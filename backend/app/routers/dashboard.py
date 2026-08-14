from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import (
    BacklinkGap,
    DistributionJob,
    GeoAsset,
    GeoObservation,
    GeoPrompt,
    Inquiry,
    Market,
    OnsiteIssue,
    OutreachItem,
    SeoPage,
    SitePage,
    Tenant,
    User,
    WorkOrder,
)
from app.schemas import DashboardSummary

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> DashboardSummary:
    tid = user.tenant_id
    tenant = db.get(Tenant, tid)
    markets = db.query(func.count(Market.id)).filter(Market.tenant_id == tid).scalar() or 0
    priority = (
        db.query(func.count(Market.id)).filter(Market.tenant_id == tid, Market.status == "priority").scalar() or 0
    )
    seo_in_progress = (
        db.query(func.count(SeoPage.id))
        .filter(SeoPage.tenant_id == tid, SeoPage.status.in_(["outline", "draft", "meta"]))
        .scalar()
        or 0
    )
    seo_review = (
        db.query(func.count(SeoPage.id)).filter(SeoPage.tenant_id == tid, SeoPage.status == "review").scalar() or 0
    )
    seo_ready = (
        db.query(func.count(SeoPage.id)).filter(SeoPage.tenant_id == tid, SeoPage.status == "ready").scalar() or 0
    )
    open_wo = (
        db.query(func.count(WorkOrder.id))
        .filter(WorkOrder.tenant_id == tid, WorkOrder.status.in_(["open", "claimed", "in_progress", "blocked"]))
        .scalar()
        or 0
    )
    inquiries = db.query(func.count(Inquiry.id)).filter(Inquiry.tenant_id == tid).scalar() or 0
    qualified = (
        db.query(func.count(Inquiry.id)).filter(Inquiry.tenant_id == tid, Inquiry.quality == "qualified").scalar()
        or 0
    )
    geo_prompts = db.query(func.count(GeoPrompt.id)).filter(GeoPrompt.tenant_id == tid).scalar() or 0
    geo_untested = (
        db.query(func.count(GeoObservation.id))
        .filter(GeoObservation.tenant_id == tid, GeoObservation.status == "untested")
        .scalar()
        or 0
    )
    geo_recorded = (
        db.query(func.count(GeoObservation.id))
        .filter(GeoObservation.tenant_id == tid, GeoObservation.status != "untested")
        .scalar()
        or 0
    )
    geo_assets_draft = (
        db.query(func.count(GeoAsset.id)).filter(GeoAsset.tenant_id == tid, GeoAsset.status == "draft").scalar() or 0
    )
    onsite_pages = db.query(func.count(SitePage.id)).filter(SitePage.tenant_id == tid).scalar() or 0
    onsite_open_low = (
        db.query(func.count(OnsiteIssue.id))
        .filter(OnsiteIssue.tenant_id == tid, OnsiteIssue.risk == "low", OnsiteIssue.status == "open")
        .scalar()
        or 0
    )
    onsite_open_high = (
        db.query(func.count(OnsiteIssue.id))
        .filter(OnsiteIssue.tenant_id == tid, OnsiteIssue.risk == "high", OnsiteIssue.status == "open")
        .scalar()
        or 0
    )
    offsite_gaps = db.query(func.count(BacklinkGap.id)).filter(BacklinkGap.tenant_id == tid).scalar() or 0
    offsite_outreach_open = (
        db.query(func.count(OutreachItem.id))
        .filter(OutreachItem.tenant_id == tid, OutreachItem.status.in_(["todo", "sent_manual"]))
        .scalar()
        or 0
    )
    distribution_jobs = db.query(func.count(DistributionJob.id)).filter(DistributionJob.tenant_id == tid).scalar() or 0
    return DashboardSummary(
        tenant_name=tenant.name if tenant else "",
        markets_count=markets,
        priority_markets=priority,
        seo_in_progress=seo_in_progress,
        seo_pending_review=seo_review,
        seo_ready=seo_ready,
        open_work_orders=open_wo,
        inquiries_total=inquiries,
        qualified_inquiries=qualified,
        geo_prompts=geo_prompts,
        geo_untested=geo_untested,
        geo_recorded=geo_recorded,
        geo_assets_draft=geo_assets_draft,
        onsite_pages=onsite_pages,
        onsite_open_low=onsite_open_low,
        onsite_open_high=onsite_open_high,
        offsite_gaps=offsite_gaps,
        offsite_outreach_open=offsite_outreach_open,
        distribution_jobs=distribution_jobs,
    )
