from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, selectinload

from app.auth import get_current_user
from app.database import get_db
from app.models import BacklinkGap, GeoTicket, OnsiteIssue, SitePage, User
from app.routers.onsite.common import _category_label, _page_short, _plain_title
from app.schemas import ExecutionBoardOut, ExecutionItemOut

router = APIRouter(prefix="/api/execution", tags=["execution"])

SEO_CLOSED = {"done", "resolved", "verified", "wont_fix", "closed"}
GEO_CLOSED = {"done", "closed", "ignored"}
OFFSITE_CLOSED = {"won", "closed", "ignored", "skipped"}


def _priority_rank(priority: str) -> int:
    return {"P0": 0, "P1": 1, "P2": 2, "P3": 3}.get(priority or "P2", 4)


def _status_rank(status: str) -> int:
    return {"blocked": 0, "needs_retest": 1, "reopened": 1, "confirmed": 2, "in_progress": 2, "open": 3}.get(status, 4)


@router.get("/items", response_model=ExecutionBoardOut)
def list_execution_items(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ExecutionBoardOut:
    items: list[ExecutionItemOut] = []

    seo_rows = (
        db.query(OnsiteIssue)
        .options(selectinload(OnsiteIssue.page))
        .filter(OnsiteIssue.tenant_id == user.tenant_id, ~OnsiteIssue.status.in_(SEO_CLOSED))
        .all()
    )
    for issue in seo_rows:
        page: SitePage | None = issue.page
        priority = issue.priority or {"critical": "P0", "high": "P1", "low": "P2"}.get(issue.severity or "low", "P2")
        items.append(
            ExecutionItemOut(
                id=issue.id,
                source_module="seo",
                title=_plain_title(issue.title),
                subtitle=f"{_page_short(page)} · {_category_label(issue.category)}",
                href=f"/onsite/{issue.page_id}",
                status=issue.status,
                priority=priority,
                owner_hint=issue.owner_hint or "内容运营 / 客户经理",
                acceptance_criteria=issue.acceptance_criteria or "处理后重新抓取页面，确认该问题不再出现。",
                evidence=issue.evidence or issue.detail or "",
                recommended_action=issue.recommended_action or issue.proposed_change or "",
                retest_method=issue.retest_method or "重新抓取页面并比对观察层。",
                retest_result=issue.retest_result or "",
                result_url=issue.result_url or "",
                blocked_reason=issue.blocked_reason or "",
                updated_at=issue.last_checked_at or issue.closed_at or issue.created_at,
            )
        )

    geo_rows = db.query(GeoTicket).filter(GeoTicket.tenant_id == user.tenant_id, ~GeoTicket.status.in_(GEO_CLOSED)).all()
    for ticket in geo_rows:
        items.append(
            ExecutionItemOut(
                id=ticket.id,
                source_module="geo",
                title=ticket.title,
                subtitle=ticket.rationale or ticket.diagnosis,
                href="/geo",
                status=ticket.status,
                priority=ticket.priority or "P2",
                owner_hint=ticket.owner_hint or "内容运营 / 客户经理",
                acceptance_criteria=ticket.acceptance_criteria or "完成 GEO 资产或站外可信源补齐，并复测买家问题。",
                evidence=ticket.evidence or "",
                recommended_action=ticket.recommended_action or "补齐实体说明、第三方可信源或官网可引用内容。",
                retest_method=ticket.retest_method or "重新运行 GEO 采样，检查提及和引用。",
                retest_result=ticket.retest_result or ticket.verified_note or "",
                blocked_reason=ticket.blocked_reason or "",
                updated_at=ticket.last_checked_at or ticket.updated_at or ticket.created_at,
            )
        )

    offsite_rows = db.query(BacklinkGap).filter(BacklinkGap.tenant_id == user.tenant_id, ~BacklinkGap.status.in_(OFFSITE_CLOSED)).all()
    for gap in offsite_rows:
        items.append(
            ExecutionItemOut(
                id=gap.id,
                source_module="offsite",
                title=gap.title or gap.referring_domain,
                subtitle=f"{gap.referring_domain} · {gap.issue_type}",
                href="/offsite",
                status=gap.status,
                priority=gap.priority or "P2",
                owner_hint=gap.owner_hint or "站外执行",
                acceptance_criteria=gap.acceptance_criteria or "记录 result_url，并完成 Placement 核验。",
                evidence=gap.evidence or gap.notes or "",
                recommended_action=gap.recommended_action or "判断该平台是否值得提交、认领或监控。",
                retest_method=gap.retest_method or "复查 result_url 是否可访问、是否提及客户、是否链接到目标页。",
                retest_result=gap.retest_result or "",
                result_url=gap.result_url or gap.link_url or "",
                blocked_reason=gap.blocked_reason or "",
                updated_at=gap.last_checked_at or gap.closed_at or gap.created_at,
            )
        )

    items.sort(key=lambda item: (_priority_rank(item.priority), _status_rank(item.status), item.source_module, item.title))
    return ExecutionBoardOut(
        total_open=len(items),
        blocked=sum(1 for item in items if item.status == "blocked" or item.blocked_reason),
        needs_retest=sum(1 for item in items if item.status in {"needs_retest", "reopened", "confirmed"}),
        items=items,
    )
