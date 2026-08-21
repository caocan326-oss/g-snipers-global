"""Deterministic next-step for the onsite chain, plus an optional LLM one-liner.

The step machine never invents ranks, GSC counts, or citations.
LLM only rephrases known counts; if the key is missing we keep the template.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.llm import OK, UNCONFIGURED, complete, configured
from app.models import OnsiteIssue, SitePage, Tenant, User

STEPS: tuple[tuple[str, str], ...] = (
    ("setup", "登记网站"),
    ("collect", "查看网页"),
    ("diagnose", "给出改法"),
    ("confirm", "确认改法"),
    ("retest", "改后复查"),
)

CLOSED = {"verified", "wont_fix"}


@dataclass(frozen=True)
class GuideAction:
    key: str
    label: str
    filter_key: str = ""


@dataclass
class GuideState:
    current: str
    action: GuideAction
    origin: str
    pages: int
    fetched: int
    needs_draft: int
    ready_to_execute: int
    waiting_retest: int
    open_high: int
    complete: bool


def _counts(db: Session, tenant_id: str) -> tuple[str, int, int, int, int, int, int]:
    tenant = db.get(Tenant, tenant_id)
    origin = ((tenant.site_origin if tenant else "") or "").strip()
    pages = db.query(SitePage).filter(SitePage.tenant_id == tenant_id).all()
    issues = db.query(OnsiteIssue).filter(OnsiteIssue.tenant_id == tenant_id).all()
    fetched = sum(1 for page in pages if page.crawl_status == "ok" or page.fetched_at)
    needs_draft = sum(
        1 for issue in issues if issue.status == "open" and not (issue.proposed_change or "").strip()
    )
    ready = sum(1 for issue in issues if issue.status == "drafted")
    waiting = sum(1 for issue in issues if issue.status in {"draft_applied", "confirmed"})
    open_high = sum(
        1
        for issue in issues
        if issue.severity in {"critical", "high"} and issue.status not in CLOSED
    )
    return origin, len(pages), fetched, needs_draft, ready, waiting, open_high


def compute_state(db: Session, user: User) -> GuideState:
    origin, pages, fetched, needs_draft, ready, waiting, open_high = _counts(db, user.tenant_id)
    if not origin:
        return GuideState(
            "setup",
            GuideAction("save_origin", "保存网站地址"),
            origin,
            pages,
            fetched,
            needs_draft,
            ready,
            waiting,
            open_high,
            False,
        )
    if fetched == 0:
        return GuideState(
            "collect",
            GuideAction("fetch_site", "查看当前网页"),
            origin,
            pages,
            fetched,
            needs_draft,
            ready,
            waiting,
            open_high,
            False,
        )
    if needs_draft > 0:
        return GuideState(
            "diagnose",
            GuideAction("generate_drafts", "写出改法"),
            origin,
            pages,
            fetched,
            needs_draft,
            ready,
            waiting,
            open_high,
            False,
        )
    if ready > 0:
        return GuideState(
            "confirm",
            GuideAction("review_drafts", "查看待确认的改法", filter_key="ready_to_execute"),
            origin,
            pages,
            fetched,
            needs_draft,
            ready,
            waiting,
            open_high,
            False,
        )
    if waiting > 0:
        return GuideState(
            "retest",
            GuideAction("retest_queue", "复查已修改的页面", filter_key="waiting_retest"),
            origin,
            pages,
            fetched,
            needs_draft,
            ready,
            waiting,
            open_high,
            False,
        )
    return GuideState(
        "retest",
        GuideAction("export_report", "下载客户说明"),
        origin,
        pages,
        fetched,
        needs_draft,
        ready,
        waiting,
        open_high,
        True,
    )


def step_states(current: str, *, complete: bool) -> list[dict[str, str]]:
    seen_current = False
    rows: list[dict[str, str]] = []
    for key, label in STEPS:
        if complete:
            status = "done"
        elif key == current:
            status = "current"
            seen_current = True
        elif not seen_current:
            status = "done"
        else:
            status = "upcoming"
        rows.append({"key": key, "label": label, "status": status})
    return rows


def fallback_narrative(state: GuideState) -> str:
    origin = state.origin or "尚未登记"
    if state.current == "setup":
        return "还没有登记客户官网。先保存网址，才能打开页面查看。未查看的内容不会写成已有结论。"
    if state.current == "collect":
        return f"当前网站是 {origin}。下一步只读取现有页面，不会修改线上内容。"
    if state.current == "diagnose":
        high = "其中有优先处理项。" if state.open_high else ""
        return f"已查看 {state.fetched} 个页面，还有 {state.needs_draft} 条未写改法。{high}点主按钮会把剩下的改法写完，不会再查一遍，所以问题数不会因此变多。"
    if state.current == "confirm":
        return f"已有 {state.ready_to_execute} 条改法待确认。系统不会直接改客户网站，确认后才能复查。"
    if state.complete:
        return f"本轮网站检查已完成，共查看 {state.fetched} 个页面。可以下载客户说明；未检查的项目会如实标注。"
    return f"有 {state.waiting_retest} 条已确认修改。下一步重新打开页面核对，一致后才算完成。"


def narrate(state: GuideState) -> tuple[str, str]:
    template = fallback_narrative(state)
    if not configured():
        return template, UNCONFIGURED
    result = complete(
        system=(
            "你在写给企业市场负责人看的一句中文说明，不超过50字。语气清楚、克制，不要口语（不要老板、你点头、瞎说），也不要行话（不要取证、复测、Canonical、GSC、HTML）。"
            "说明已查看什么、下一步点哪个按钮。未查看的不要写成已有结论。不要自称ChatGPT。不要说已经改了客户网站。"
        ),
        user=(
            f"步骤:{state.current} 官网:{state.origin or '未登记'} "
            f"已抓:{state.fetched}/{state.pages} 待改稿:{state.needs_draft} "
            f"待确认:{state.ready_to_execute} 待复测:{state.waiting_retest} "
            f"高风险未关:{state.open_high} 主按钮:{state.action.label} 已完成:{state.complete}"
        ),
    )
    text = (result.text or "").strip().replace("\n", "")
    if result.status == OK and text:
        return text[:80], result.status
    return template, result.status


def guide_payload(db: Session, user: User, *, voice: bool) -> dict:
    state = compute_state(db, user)
    narrative, ai_status = narrate(state) if voice else (fallback_narrative(state), "template")
    if not voice and configured():
        ai_status = "pending"
    elif not voice:
        ai_status = UNCONFIGURED
    return {
        "current": state.current,
        "complete": state.complete,
        "action_key": state.action.key,
        "action_label": state.action.label,
        "filter_key": state.action.filter_key,
        "narrative": narrative,
        "ai_status": ai_status,
        "origin": state.origin,
        "pages": state.pages,
        "fetched": state.fetched,
        "needs_draft": state.needs_draft,
        "ready_to_execute": state.ready_to_execute,
        "waiting_retest": state.waiting_retest,
        "open_high": state.open_high,
        "steps": step_states(state.current, complete=state.complete),
    }
