from datetime import datetime, timezone

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.ai_engine import assist_onsite_issue
from app.llm import UNCONFIGURED, configured
from app.models import OnsiteIssue, SitePage, User
from app.onsite_fetch import OriginError, normalize_origin
from app.onsite_loop import (
    TEMPLATE_LIMIT_REASON,
    WEEKLY_RECHECK_FAIL,
    WEEKLY_RECHECK_OPENED,
    WEEKLY_RECHECK_PASS,
    clear_weekly_pin,
    dropped_restore_id,
    is_template_limited,
    save_weekly_pin,
    weekly_all_passed,
    weekly_pin_state,
    weekly_recheck_kind,
)
from app.risk import RISKS, SEVERITIES, default_severity, needs_confirm, require_confirm, severity_to_risk
from app.schemas import (
    AiAssistOut,
    AiStepIn,
    AnalyzeOut,
    ConfirmReadyIn,
    OnsiteDraftIn,
    OnsiteIssueCreate,
    OnsiteIssueOut,
    OnsiteStatusIn,
    WeeklyOnsiteOut,
    WeeklyRecheckVerdictIn,
)

import app.routers.onsite as _onsite_pkg

from . import router
from .common import (
    _ai_batch_limit,
    _ai_issue_candidates,
    _analyze_one,
    _issue_needs_ai,
    _issue_out,
    _owned_issue,
    _owned_page,
    _require_origin,
    _site_origin,
    _tenant,
    decorate_weekly_issues,
    load_weekly_onsite_issues,
    refresh_weekly_pin_after_drop,
)
from .constants import CATEGORIES
from .crawl import _fetch_one_registered, _reconcile_site_patterns


def _out(db: Session, user: User, row: OnsiteIssue, page: SitePage | None = None) -> OnsiteIssueOut:
    return _issue_out(row, page, _site_origin(db, user.tenant_id))


def _ai_after_analyze(db: Session, user: User, pages: list[SitePage], *, limit: int = 3) -> tuple[str, int, int]:
    issues = [i for i in _ai_issue_candidates(db, user) if _issue_needs_ai(i)]
    if not configured():
        limit = len(issues)
    by_id = {p.id: p for p in pages}
    processed = 0
    for issue in issues[:limit]:
        page = by_id.get(issue.page_id) or db.get(SitePage, issue.page_id)
        if page is None:
            continue
        _onsite_pkg.assist_onsite_issue(db, issue, page, step="analyze")
        processed += 1
    remaining = max(len(issues) - processed, 0)
    return (UNCONFIGURED if not configured() else "ok", processed, remaining)


@router.post("/analyze", response_model=AnalyzeOut)
def analyze_inventory(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> AnalyzeOut:
    pages = db.query(SitePage).filter(SitePage.tenant_id == user.tenant_id).all()
    created = skipped = verified = 0
    for page in pages:
        c, s, v = _analyze_one(db, user, page)
        created += c
        skipped += s
        verified += v
    site_created, site_skipped = _reconcile_site_patterns(db, user, pages)
    created += site_created
    skipped += site_skipped
    ai_status, ai_processed, ai_remaining = _onsite_pkg._ai_after_analyze(db, user, pages)
    db.commit()
    note = "分析只读当前观察，不改改稿，也不应用到线上。已满足的工单标为已验收。"
    if ai_processed:
        note += f" 已先生成 {ai_processed} 条 AI 建议。"
    if ai_remaining:
        note += f" 还有 {ai_remaining} 条可继续批量生成。"
    if ai_status == UNCONFIGURED:
        note += " LLM 未配置，诊断/改稿未编造。"
    return AnalyzeOut(
        created=created, skipped=skipped, verified=verified, pages=len(pages), note=note, ai_status=ai_status
    )


@router.post("/pages/{page_id}/analyze", response_model=AnalyzeOut)
def analyze_one_page(
    page_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalyzeOut:
    page = _owned_page(db, user, page_id)
    created, skipped, verified = _analyze_one(db, user, page)
    ai_status, ai_processed, ai_remaining = _onsite_pkg._ai_after_analyze(db, user, [page])
    db.commit()
    note = "分析只读当前观察，不改改稿，也不应用到线上。已满足的工单标为已验收。"
    if ai_processed:
        note += f" 已先生成 {ai_processed} 条 AI 建议。"
    if ai_remaining:
        note += f" 还有 {ai_remaining} 条可继续批量生成。"
    if ai_status == UNCONFIGURED:
        note += " LLM 未配置，诊断/改稿未编造。"
    return AnalyzeOut(
        created=created, skipped=skipped, verified=verified, pages=1, note=note, ai_status=ai_status
    )


@router.post("/pages/{page_id}/issues", response_model=OnsiteIssueOut, status_code=201)
def create_issue(
    page_id: str,
    body: OnsiteIssueCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OnsiteIssueOut:
    page = _owned_page(db, user, page_id)
    if body.category not in CATEGORIES:
        raise HTTPException(status_code=400, detail="无效问题类型")
    severity = body.severity or default_severity(body.category)
    if severity not in SEVERITIES:
        raise HTTPException(status_code=400, detail="无效严重级别")
    risk = body.risk or severity_to_risk(severity)
    if risk not in RISKS:
        raise HTTPException(status_code=400, detail="无效风险等级")
    row = OnsiteIssue(
        tenant_id=user.tenant_id,
        page_id=page.id,
        category=body.category,
        title=body.title,
        detail=body.detail,
        proposed_change=body.proposed_change,
        severity=severity,
        risk=risk,
        priority=body.priority,
        owner_hint=body.owner_hint,
        acceptance_criteria=body.acceptance_criteria,
        recommended_action=body.recommended_action,
        retest_method=body.retest_method,
        status="open",
        metric_status="untested",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _out(db, user, row, page)


@router.patch("/issues/{issue_id}/draft", response_model=OnsiteIssueOut)
def write_change_draft(
    issue_id: str,
    body: OnsiteDraftIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OnsiteIssueOut:
    row = _owned_issue(db, user, issue_id)
    if not body.proposed_change.strip():
        raise HTTPException(status_code=400, detail="改稿草稿不能为空")
    row.proposed_change = body.proposed_change
    if row.status == "open":
        row.status = "drafted"
    db.commit()
    db.refresh(row)
    return _out(db, user, row)


@router.post("/issues/{issue_id}/apply-draft", response_model=OnsiteIssueOut)
def apply_draft(
    issue_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OnsiteIssueOut:
    row = _owned_issue(db, user, issue_id)
    if needs_confirm(row.severity, row.risk):
        raise HTTPException(status_code=400, detail="高风险任务不能自动落草稿，请走人工确认")
    if not (row.proposed_change or "").strip():
        raise HTTPException(status_code=400, detail="请先写改稿草稿，分析与应用是两步")
    page = db.get(SitePage, row.page_id)
    if page is None or page.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="页面不存在")
    row.status = "draft_applied"
    db.commit()
    db.refresh(row)
    return _out(db, user, row, page)


@router.post("/issues/{issue_id}/confirm-apply", response_model=OnsiteIssueOut)
def confirm_apply(
    issue_id: str,
    body: ConfirmReadyIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OnsiteIssueOut:
    require_confirm(body.confirmed, action="应用到线上站点")
    row = _owned_issue(db, user, issue_id)
    if not needs_confirm(row.severity, row.risk):
        raise HTTPException(status_code=400, detail="低风险任务请用工作区落草稿，无需线上确认")
    if not (row.proposed_change or "").strip():
        raise HTTPException(status_code=400, detail="请先写改稿草稿，分析与应用是两步")
    page = db.get(SitePage, row.page_id)
    if page is None or page.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="页面不存在")
    row.status = "confirmed"
    tenant = _tenant(db, user)
    if (tenant.site_origin or "").strip():
        try:
            origin = normalize_origin(tenant.site_origin)
            _fetch_one_registered(db, user, page, origin)
        except OriginError:
            pass
    db.commit()
    db.refresh(row)
    return _out(db, user, row, page)


@router.post("/issues/{issue_id}/mark-executed", response_model=OnsiteIssueOut)
def mark_executed(
    issue_id: str,
    body: OnsiteStatusIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OnsiteIssueOut:
    require_confirm(body.confirmed, action="标记已执行")
    row = _owned_issue(db, user, issue_id)
    if not (row.proposed_change or "").strip():
        raise HTTPException(status_code=400, detail="请先保存处理方案，再标记已执行")
    page = db.get(SitePage, row.page_id)
    if page is None or page.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="页面不存在")
    row.status = "confirmed"
    note = (body.note or "").strip()
    if note:
        row.evidence = ((row.evidence or "").rstrip() + f"\n人工执行记录：{note}").strip()
    row.last_checked_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return _out(db, user, row, page)


@router.post("/issues/{issue_id}/retest", response_model=OnsiteIssueOut)
def retest_issue(
    issue_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OnsiteIssueOut:
    row = _owned_issue(db, user, issue_id)
    page = db.get(SitePage, row.page_id)
    if page is None or page.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="页面不存在")
    tenant = _tenant(db, user)
    origin = _require_origin(tenant)
    try:
        _fetch_one_registered(db, user, page, origin)
    except OriginError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.flush()
    db.refresh(row)
    row.last_checked_at = datetime.now(timezone.utc)
    row.retest_result = "已重新抓取页面并刷新诊断状态。"
    db.commit()
    db.refresh(row)
    return _out(db, user, row, page)


@router.post("/issues/{issue_id}/template-limit", response_model=OnsiteIssueOut)
def mark_template_limit(
    issue_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OnsiteIssueOut:
    row = _owned_issue(db, user, issue_id)
    page = db.get(SitePage, row.page_id)
    if page is None or page.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="页面不存在")
    if row.status in {"verified", "wont_fix"}:
        raise HTTPException(status_code=400, detail="已关闭的项不用再记受模板限制。")
    row.blocked_reason = TEMPLATE_LIMIT_REASON
    refresh_weekly_pin_after_drop(db, user.tenant_id, row.id)
    db.commit()
    db.refresh(row)
    return _out(db, user, row, page)


def _return_issue_to_week(db: Session, user: User, row: OnsiteIssue, *, sent: bool) -> None:
    if row.status == "verified":
        row.status = "open"
        row.closed_at = None
    row.blocked_reason = ""
    row.retest_result = "已放回这周三处。打开核对只记看过，不是工作台勾完。我们不代改。"
    pin = weekly_pin_state(db, user.tenant_id)
    issue_ids = [row.id, *[item for item in (pin.get("issue_ids") or []) if item != row.id]]
    sent_ids = [item for item in (pin.get("sent_ids") or []) if item != row.id]
    if sent:
        sent_ids = [row.id, *sent_ids]
    save_weekly_pin(
        db,
        user.tenant_id,
        issue_ids=issue_ids,
        sent_ids=sent_ids,
        last_dropped_id="",
        last_dropped_sent=False,
    )


def _weekly_out(db: Session, user: User, note: str = "") -> WeeklyOnsiteOut:
    rows = load_weekly_onsite_issues(db, user.tenant_id)
    pin = weekly_pin_state(db, user.tenant_id)
    return WeeklyOnsiteOut(
        this_week=decorate_weekly_issues(db, user.tenant_id, rows),
        weekly_pinned=bool(pin.get("issue_ids")),
        can_restore=bool(dropped_restore_id(db, user.tenant_id)),
        note=note,
    )


@router.post("/weekly/pin", response_model=WeeklyOnsiteOut)
def pin_weekly_onsite(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> WeeklyOnsiteOut:
    rows = load_weekly_onsite_issues(db, user.tenant_id)
    if not rows:
        raise HTTPException(status_code=400, detail="还没有这周的三处可以钉住。")
    pin = weekly_pin_state(db, user.tenant_id)
    save_weekly_pin(db, user.tenant_id, issue_ids=[row.id for row in rows], sent_ids=pin.get("sent_ids") or [])
    db.commit()
    return _weekly_out(db, user, "已钉住这三处。新抓到的紧急页不会顶掉。受模板限制仍会换下一页。")


@router.post("/weekly/unpin", response_model=WeeklyOnsiteOut)
def unpin_weekly_onsite(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> WeeklyOnsiteOut:
    clear_weekly_pin(db, user.tenant_id)
    db.commit()
    return _weekly_out(db, user, "已取消钉住。这周三处按紧急/优先重新挑。")


@router.post("/weekly/next-set", response_model=WeeklyOnsiteOut)
def rotate_weekly_onsite(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> WeeklyOnsiteOut:
    current = load_weekly_onsite_issues(db, user.tenant_id)
    if not current:
        raise HTTPException(status_code=400, detail="还没有这周三处可以换。")
    if not weekly_all_passed(current):
        raise HTTPException(status_code=400, detail="这周三处还没都过。过了再换下一组。")
    page_ids = [(row.page_id or "").strip() for row in current if (row.page_id or "").strip()]
    pin = weekly_pin_state(db, user.tenant_id)
    retired = list(dict.fromkeys([*(pin.get("retired_page_ids") or []), *page_ids]))
    save_weekly_pin(
        db,
        user.tenant_id,
        issue_ids=[],
        sent_ids=[],
        claimed_ids=[],
        awaiting_reopen_ids=[],
        retired_page_ids=retired,
    )
    db.flush()
    nxt = load_weekly_onsite_issues(db, user.tenant_id)
    if nxt:
        save_weekly_pin(
            db,
            user.tenant_id,
            issue_ids=[row.id for row in nxt],
            retired_page_ids=retired,
        )
        note = "已换下一组。按紧急/优先另挑。上一组还在问题板，不是已解决。我们不代改。"
    else:
        note = "上一组过了。紧急/优先里没有下一组。上一组还在问题板，不是已解决。我们不代改。"
    db.commit()
    return _weekly_out(db, user, note)


@router.post("/weekly/restore-dropped", response_model=WeeklyOnsiteOut)
def restore_dropped_weekly(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> WeeklyOnsiteOut:
    dropped_id = dropped_restore_id(db, user.tenant_id)
    if not dropped_id:
        raise HTTPException(status_code=400, detail="没有刚拿掉的一页可以放回。")
    row = _owned_issue(db, user, dropped_id)
    pin = weekly_pin_state(db, user.tenant_id)
    sent = dropped_id in (pin.get("sent_ids") or []) or bool(pin.get("last_dropped_sent")) or (
        row.status == "verified" and (row.retest_result or "").startswith("打开过该页。这一条现在对得上")
    )
    _return_issue_to_week(db, user, row, sent=sent)
    db.commit()
    return _weekly_out(db, user, "已放回这周三处。打开核对只记看过，不是工作台勾完。不是官网已改。我们不代改。")


@router.post("/issues/{issue_id}/sent-to-customer", response_model=WeeklyOnsiteOut)
def mark_sent_to_customer(
    issue_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WeeklyOnsiteOut:
    row = _owned_issue(db, user, issue_id)
    week = load_weekly_onsite_issues(db, user.tenant_id)
    week_ids = [item.id for item in week]
    if row.id not in week_ids:
        raise HTTPException(status_code=400, detail="只记这周这三处已经发给客户。先打开站内「这周给客户改三处」。")
    pin = weekly_pin_state(db, user.tenant_id)
    issue_ids = pin.get("issue_ids") or week_ids
    sent_ids = list(dict.fromkeys([*(pin.get("sent_ids") or []), row.id]))
    save_weekly_pin(db, user.tenant_id, issue_ids=issue_ids, sent_ids=sent_ids)
    db.commit()
    return _weekly_out(db, user, "已记下发给客户。不是官网已改，也不是我们代改。")


@router.post("/issues/{issue_id}/clear-sent-to-customer", response_model=WeeklyOnsiteOut)
def clear_sent_to_customer(
    issue_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WeeklyOnsiteOut:
    row = _owned_issue(db, user, issue_id)
    pin = weekly_pin_state(db, user.tenant_id)
    if not pin.get("issue_ids") and not pin.get("sent_ids"):
        db.commit()
        return _weekly_out(db, user, "这条还没有记成发给客户。")
    sent_ids = [item for item in (pin.get("sent_ids") or []) if item != row.id]
    save_weekly_pin(db, user.tenant_id, issue_ids=pin.get("issue_ids") or [], sent_ids=sent_ids)
    db.commit()
    return _weekly_out(db, user, "已取消「已发给客户」。")


@router.post("/issues/{issue_id}/weekly-claimed", response_model=WeeklyOnsiteOut)
def mark_weekly_claimed(
    issue_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WeeklyOnsiteOut:
    row = _owned_issue(db, user, issue_id)
    week = load_weekly_onsite_issues(db, user.tenant_id)
    week_ids = [item.id for item in week]
    if row.id not in week_ids:
        raise HTTPException(status_code=400, detail="只记这周这三处。先打开总览「这周给客户改三处」。")
    pin = weekly_pin_state(db, user.tenant_id)
    if row.id not in (pin.get("sent_ids") or []):
        raise HTTPException(status_code=400, detail="先记下已发。客户说改完了不是官网已改。")
    kind = weekly_recheck_kind(row.retest_result or "")
    if kind == "pass":
        raise HTTPException(status_code=400, detail="这一条已经核对过。不用再记客户说改完了。")
    if kind not in {"fail", "viewed"}:
        raise HTTPException(status_code=400, detail="先打开核对再记过或记不过。客户说改完了还要再打开核对。")
    issue_ids = pin.get("issue_ids") or week_ids
    claimed_ids = list(dict.fromkeys([*(pin.get("claimed_ids") or []), row.id]))
    awaiting_reopen_ids = list(dict.fromkeys([*(pin.get("awaiting_reopen_ids") or []), row.id]))
    save_weekly_pin(
        db,
        user.tenant_id,
        issue_ids=issue_ids,
        sent_ids=pin.get("sent_ids") or [],
        claimed_ids=claimed_ids,
        awaiting_reopen_ids=awaiting_reopen_ids,
    )
    db.commit()
    return _weekly_out(db, user, "已记下客户说改完了。还要打开核对。不是官网已改。我们不代改。")


@router.post("/issues/{issue_id}/clear-weekly-claimed", response_model=WeeklyOnsiteOut)
def clear_weekly_claimed(
    issue_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WeeklyOnsiteOut:
    row = _owned_issue(db, user, issue_id)
    pin = weekly_pin_state(db, user.tenant_id)
    claimed_ids = [item for item in (pin.get("claimed_ids") or []) if item != row.id]
    save_weekly_pin(
        db,
        user.tenant_id,
        issue_ids=pin.get("issue_ids") or [],
        sent_ids=pin.get("sent_ids") or [],
        claimed_ids=claimed_ids,
    )
    db.commit()
    return _weekly_out(db, user, "已取消「客户说改完了」。")


@router.post("/issues/{issue_id}/weekly-recheck", response_model=WeeklyOnsiteOut)
def weekly_recheck_issue(
    issue_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WeeklyOnsiteOut:
    row = _owned_issue(db, user, issue_id)
    week_ids = [item.id for item in load_weekly_onsite_issues(db, user.tenant_id)]
    if row.id not in week_ids:
        raise HTTPException(status_code=400, detail="只核这周这三处。先打开站内「这周给客户改三处」。")
    page = db.get(SitePage, row.page_id)
    if page is None or page.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="页面不存在")
    origin = _require_origin(_tenant(db, user))
    prior_status = row.status
    try:
        snap, _created, _verified = _fetch_one_registered(db, user, page, origin)
    except OriginError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.flush()
    db.refresh(row)
    row.last_checked_at = datetime.now(timezone.utc)
    if row.status == "verified":
        row.status = prior_status if prior_status != "verified" else "open"
        row.closed_at = None
    if not getattr(snap, "usable", False):
        row.retest_result = "打开过该页，但这次没抓全。只记看过，不是工作台勾完。还在这三处。我们不代改。"
        note = "已打开该页。这次没抓全。只记看过，不是工作台勾完。还在这三处。我们不代改。"
    else:
        row.retest_result = "打开过该页。只记看过，不是工作台勾完。还在这三处。我们不代改。"
        note = "已打开该页。只记看过，不是工作台勾完。还在这三处。我们不代改。"
    pin = weekly_pin_state(db, user.tenant_id)
    awaiting_reopen_ids = [item for item in (pin.get("awaiting_reopen_ids") or []) if item != row.id]
    save_weekly_pin(
        db,
        user.tenant_id,
        issue_ids=pin.get("issue_ids") or week_ids,
        sent_ids=pin.get("sent_ids") or [],
        claimed_ids=pin.get("claimed_ids") or [],
        awaiting_reopen_ids=awaiting_reopen_ids,
    )
    db.commit()
    return _weekly_out(db, user, note)


@router.post("/issues/{issue_id}/weekly-recheck-verdict", response_model=WeeklyOnsiteOut)
def weekly_recheck_verdict(
    issue_id: str,
    body: WeeklyRecheckVerdictIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WeeklyOnsiteOut:
    row = _owned_issue(db, user, issue_id)
    week_ids = [item.id for item in load_weekly_onsite_issues(db, user.tenant_id)]
    if row.id not in week_ids:
        raise HTTPException(status_code=400, detail="只核这周这三处。先打开站内「这周给客户改三处」。")
    pin = weekly_pin_state(db, user.tenant_id)
    if row.id in (pin.get("awaiting_reopen_ids") or []):
        raise HTTPException(status_code=400, detail="客户说改完了还要先打开核对。客户说了不算过。")
    if not (row.retest_result or "").startswith(WEEKLY_RECHECK_OPENED):
        raise HTTPException(status_code=400, detail="先打开核对这一页。只记看过还不算过。")
    if row.status == "verified":
        row.status = "open"
        row.closed_at = None
    if body.passed:
        row.retest_result = WEEKLY_RECHECK_PASS
        note = "已记下核对过。这一条现在对得上。不是我们改的。还在这三处。我们不代改。"
    else:
        row.retest_result = WEEKLY_RECHECK_FAIL
        note = "已记下核对不过。问题还在。还在这三处。我们不代改。"
    pin = weekly_pin_state(db, user.tenant_id)
    claimed_ids = [item for item in (pin.get("claimed_ids") or []) if item != row.id]
    save_weekly_pin(
        db,
        user.tenant_id,
        issue_ids=pin.get("issue_ids") or week_ids,
        sent_ids=pin.get("sent_ids") or [],
        claimed_ids=claimed_ids,
    )
    db.commit()
    return _weekly_out(db, user, note)


@router.post("/issues/{issue_id}/clear-template-limit", response_model=OnsiteIssueOut)
def clear_template_limit(
    issue_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OnsiteIssueOut:
    row = _owned_issue(db, user, issue_id)
    page = db.get(SitePage, row.page_id)
    if page is None or page.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="页面不存在")
    if is_template_limited(row):
        row.blocked_reason = ""
    db.commit()
    db.refresh(row)
    return _out(db, user, row, page)


@router.post("/issues/{issue_id}/wont-fix", response_model=OnsiteIssueOut)
def wont_fix_issue(
    issue_id: str,
    body: OnsiteStatusIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OnsiteIssueOut:
    row = _owned_issue(db, user, issue_id)
    page = db.get(SitePage, row.page_id)
    if page is None or page.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="页面不存在")
    row.status = "wont_fix"
    row.closed_at = datetime.now(timezone.utc)
    note = (body.note or "").strip()
    if note:
        row.evidence = ((row.evidence or "").rstrip() + f"\n忽略原因：{note}").strip()
    refresh_weekly_pin_after_drop(db, user.tenant_id, row.id)
    db.commit()
    db.refresh(row)
    return _out(db, user, row, page)


@router.post("/issues/{issue_id}/reopen", response_model=OnsiteIssueOut)
def reopen_issue(
    issue_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OnsiteIssueOut:
    row = _owned_issue(db, user, issue_id)
    page = db.get(SitePage, row.page_id)
    if page is None or page.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="页面不存在")
    row.status = "drafted" if (row.proposed_change or "").strip() else "open"
    row.closed_at = None
    db.commit()
    db.refresh(row)
    return _out(db, user, row, page)


@router.post("/issues/{issue_id}/ai", response_model=AiAssistOut)
def ai_issue(
    issue_id: str,
    body: AiStepIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AiAssistOut:
    row = db.get(OnsiteIssue, issue_id)
    if row is None or row.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="任务不存在")
    page = db.get(SitePage, row.page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="页面不存在")
    payload = _onsite_pkg.assist_onsite_issue(db, row, page, step=body.step)
    db.commit()
    return AiAssistOut(**payload)


@router.post("/ai", response_model=AiAssistOut)
def ai_onsite_engine(
    body: AiStepIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AiAssistOut:
    pages = db.query(SitePage).filter(SitePage.tenant_id == user.tenant_id).all()
    created = skipped = 0
    limit = _ai_batch_limit(body.limit)
    if body.step in {"analyze", "all"}:
        for page in pages:
            c, s, _v = _analyze_one(db, user, page)
            created += c
            skipped += s
        site_created, site_skipped = _reconcile_site_patterns(db, user, pages)
        created += site_created
        skipped += site_skipped
    if body.step == "analyze":
        db.commit()
        extra = f" 又查出 {created} 条。不是网站更差了，是清单更完整。" if created else ""
        return AiAssistOut(
            status="ok" if created or skipped else "skipped",
            step=body.step,
            processed=created + skipped,
            remaining=0,
            limit=limit,
            detail=f"只重新检查了一遍，没有写改法。新建 {created} 条，刷新 {skipped} 条。{extra}".strip(),
        )
    issues = [i for i in _ai_issue_candidates(db, user) if _issue_needs_ai(i)]
    if not issues:
        db.commit()
        return AiAssistOut(
            status="skipped",
            step=body.step,
            processed=0,
            remaining=0,
            limit=limit,
            detail="没有待写的改法。" if body.step == "content" else f"没有待处理问题。规则诊断新建 {created} 条，刷新 {skipped} 条。",
        )
    last: dict = {"status": UNCONFIGURED, "step": body.step, "detail": ""}
    processed = drafted = ok = errors = unconfigured = 0
    by_id = {p.id: p for p in pages}
    batch = issues[:limit]
    for issue in batch:
        page = by_id.get(issue.page_id)
        if page is None:
            continue
        last = _onsite_pkg.assist_onsite_issue(db, issue, page, step=body.step)
        processed += 1
        if last.get("status") == "ok":
            ok += 1
        elif last.get("status") == UNCONFIGURED:
            unconfigured += 1
        elif last.get("status") == "error":
            errors += 1
        if (last.get("draft") or "").strip():
            drafted += 1
    db.commit()
    remaining = max(len(issues) - processed, 0)
    if body.step == "content":
        last["detail"] = f"已写 {drafted} 条改法，还剩 {remaining} 条。这次只写改法，没有再查一遍。"
    else:
        last["detail"] = (
            f"本次已处理 {processed} 条 AI 建议；"
            f"生成草案 {drafted} 条，成功 {ok} 条，未配置 {unconfigured} 条，错误 {errors} 条；"
            f"剩余约 {remaining} 条可继续处理。"
            f"规则诊断新建 {created} 条，刷新 {skipped} 条。"
        )
        if created:
            last["detail"] += " 又查出新问题，不是网站更差了。"
    last["processed"] = processed
    last["remaining"] = remaining
    last["limit"] = limit
    return AiAssistOut(**last)
