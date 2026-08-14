from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.geo_helpers import ENGINES
from app.models import (
    BacklinkGap,
    Competitor,
    DemandSignal,
    GeoObservation,
    GeoPrompt,
    GeoTicket,
    InsightBrief,
    Market,
    OnsiteIssue,
    SeoPage,
    SitePage,
    User,
)
from app.schemas import (
    ChainFeedOut,
    CompetitorCreate,
    CompetitorOut,
    DemandSignalCreate,
    DemandSignalOut,
    InsightBriefIn,
    InsightBriefOut,
    MarketCreate,
    MarketDetailOut,
    MarketOut,
    MarketUpdate,
    SeoPageOut,
)

router = APIRouter(prefix="/api", tags=["insights"])

MARKET_STATUSES = {"watching", "priority", "paused"}


def _owned_market(db: Session, user: User, market_id: str) -> Market:
    market = db.get(Market, market_id)
    if market is None or market.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="市场不存在")
    return market


def _market_out(db: Session, market: Market) -> MarketOut:
    competitors = (
        db.query(func.count(Competitor.id)).filter(Competitor.market_id == market.id).scalar() or 0
    )
    demand = (
        db.query(func.count(DemandSignal.id)).filter(DemandSignal.market_id == market.id).scalar() or 0
    )
    seo = db.query(func.count(SeoPage.id)).filter(SeoPage.market_id == market.id).scalar() or 0
    return MarketOut(
        id=market.id,
        name=market.name,
        region=market.region,
        country_code=market.country_code,
        primary_locale=market.primary_locale,
        status=market.status,
        opportunity_score=market.opportunity_score,
        notes=market.notes,
        competitor_count=competitors,
        demand_count=demand,
        seo_count=seo,
        created_at=market.created_at,
    )


@router.get("/markets", response_model=list[MarketOut])
def list_markets(
    status: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MarketOut]:
    q = db.query(Market).filter(Market.tenant_id == user.tenant_id)
    if status:
        q = q.filter(Market.status == status)
    markets = q.order_by(Market.status.asc(), Market.name.asc()).all()
    return [_market_out(db, m) for m in markets]


@router.post("/markets", response_model=MarketOut, status_code=201)
def create_market(
    body: MarketCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MarketOut:
    if body.status not in MARKET_STATUSES:
        raise HTTPException(status_code=400, detail="无效的市场状态")
    market = Market(tenant_id=user.tenant_id, **body.model_dump())
    db.add(market)
    db.commit()
    db.refresh(market)
    return _market_out(db, market)


@router.get("/markets/{market_id}", response_model=MarketDetailOut)
def get_market(
    market_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MarketDetailOut:
    market = _owned_market(db, user, market_id)
    base = _market_out(db, market)
    brief = None
    if market.brief:
        brief = InsightBriefOut(
            id=market.brief.id,
            market_id=market.id,
            summary=market.brief.summary,
            opportunities=market.brief.opportunities,
            risks=market.brief.risks,
            recommended_actions=market.brief.recommended_actions,
            updated_at=market.brief.updated_at,
        )
    return MarketDetailOut(
        **base.model_dump(),
        competitors=[CompetitorOut.model_validate(c, from_attributes=True) for c in market.competitors],
        demand_signals=[DemandSignalOut.model_validate(d, from_attributes=True) for d in market.demand_signals],
        brief=brief,
    )


@router.patch("/markets/{market_id}", response_model=MarketOut)
def update_market(
    market_id: str,
    body: MarketUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MarketOut:
    market = _owned_market(db, user, market_id)
    data = body.model_dump(exclude_unset=True)
    if "status" in data and data["status"] not in MARKET_STATUSES:
        raise HTTPException(status_code=400, detail="无效的市场状态")
    for key, value in data.items():
        setattr(market, key, value)
    db.commit()
    db.refresh(market)
    return _market_out(db, market)


@router.post("/markets/{market_id}/competitors", response_model=CompetitorOut, status_code=201)
def add_competitor(
    market_id: str,
    body: CompetitorCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Competitor:
    market = _owned_market(db, user, market_id)
    row = Competitor(tenant_id=user.tenant_id, market_id=market.id, **body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/competitors/{competitor_id}", status_code=204)
def delete_competitor(
    competitor_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    row = db.get(Competitor, competitor_id)
    if row is None or row.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="竞品不存在")
    db.delete(row)
    db.commit()


@router.post("/markets/{market_id}/demand-signals", response_model=DemandSignalOut, status_code=201)
def add_demand_signal(
    market_id: str,
    body: DemandSignalCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DemandSignal:
    market = _owned_market(db, user, market_id)
    row = DemandSignal(tenant_id=user.tenant_id, market_id=market.id, **body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/demand-signals/{signal_id}", status_code=204)
def delete_demand_signal(
    signal_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    row = db.get(DemandSignal, signal_id)
    if row is None or row.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="需求信号不存在")
    db.delete(row)
    db.commit()


@router.put("/markets/{market_id}/brief", response_model=InsightBriefOut)
def upsert_brief(
    market_id: str,
    body: InsightBriefIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InsightBrief:
    market = _owned_market(db, user, market_id)
    brief = db.query(InsightBrief).filter(InsightBrief.market_id == market.id).first()
    if brief is None:
        brief = InsightBrief(tenant_id=user.tenant_id, market_id=market.id)
        db.add(brief)
    brief.summary = body.summary
    brief.opportunities = body.opportunities
    brief.risks = body.risks
    brief.recommended_actions = body.recommended_actions
    brief.updated_by = user.id
    db.commit()
    db.refresh(brief)
    return brief


@router.post("/demand-signals/{signal_id}/create-seo-page", response_model=SeoPageOut, status_code=201)
def create_seo_from_signal(
    signal_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SeoPage:
    signal = db.get(DemandSignal, signal_id)
    if signal is None or signal.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="需求信号不存在")
    page = SeoPage(
        tenant_id=user.tenant_id,
        market_id=signal.market_id,
        demand_signal_id=signal.id,
        title=signal.theme,
        target_keyword=signal.theme,
        locale=signal.locale,
        status="idea",
        created_by=user.id,
    )
    db.add(page)
    db.commit()
    db.refresh(page)
    return page


def _owned_signal(db: Session, user: User, signal_id: str) -> DemandSignal:
    signal = db.get(DemandSignal, signal_id)
    if signal is None or signal.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="需求信号不存在")
    return signal


@router.post("/demand-signals/{signal_id}/open-onsite", response_model=ChainFeedOut, status_code=201)
def open_onsite_from_signal(
    signal_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChainFeedOut:
    signal = _owned_signal(db, user, signal_id)
    slug = signal.theme.lower().replace(" ", "-")[:48]
    path = f"/{signal.locale.lower()}/{slug}"
    page = (
        db.query(SitePage)
        .filter(SitePage.tenant_id == user.tenant_id, SitePage.path == path)
        .first()
    )
    if page is None:
        page = SitePage(
            tenant_id=user.tenant_id,
            market_id=signal.market_id,
            path=path,
            locale=signal.locale,
            title=signal.theme,
            index_status="untested",
            crawl_status="untested",
            notes="由洞察信号开出的站内任务。收录/抓取未接 GSC，保持未测。",
        )
        db.add(page)
        db.flush()
    issue = OnsiteIssue(
        tenant_id=user.tenant_id,
        page_id=page.id,
        category="tdk",
        title=f"从信号开站内改页：{signal.theme}",
        detail="洞察投喂。先出 TDK / 标题 / 内链草稿，高风险改线上须确认。",
        proposed_change=f"围绕「{signal.theme}」补 Title / Description（工作区草稿，不改线上）。",
        risk="low",
        status="open",
        metric_status="untested",
    )
    db.add(issue)
    db.commit()
    return ChainFeedOut(
        chain="onsite",
        created_id=page.id,
        title=issue.title,
        redirect_path=f"/onsite/{page.id}",
    )


@router.post("/demand-signals/{signal_id}/open-geo-ticket", response_model=ChainFeedOut, status_code=201)
def open_geo_from_signal(
    signal_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChainFeedOut:
    signal = _owned_signal(db, user, signal_id)
    prompt = GeoPrompt(
        tenant_id=user.tenant_id,
        market_id=signal.market_id,
        demand_signal_id=signal.id,
        prompt_text=signal.theme,
        locale=signal.locale,
        diagnosis="untested",
    )
    db.add(prompt)
    db.flush()
    for engine in ENGINES:
        db.add(
            GeoObservation(
                tenant_id=user.tenant_id,
                prompt_id=prompt.id,
                engine=engine,
                status="untested",
            )
        )
    ticket = GeoTicket(
        tenant_id=user.tenant_id,
        prompt_id=prompt.id,
        title=f"采样验收：{signal.theme}",
        diagnosis="untested",
        rationale="洞察信号转入 GEO。先人工采样中西引擎，未测不得写成已引用。引用 ≠ 吸收。",
        acceptance_criteria="8 个引擎槽位完成一轮人工记录或明确保持未测；不得发明 brand.com 引用率；验收须客户经理确认。",
        status="open",
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ChainFeedOut(
        chain="geo",
        created_id=ticket.id,
        title=ticket.title,
        redirect_path="/geo",
    )


@router.post("/demand-signals/{signal_id}/open-link-followup", response_model=ChainFeedOut, status_code=201)
def open_link_from_signal(
    signal_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChainFeedOut:
    signal = _owned_signal(db, user, signal_id)
    gap = BacklinkGap(
        tenant_id=user.tenant_id,
        market_id=signal.market_id,
        competitor_name="待核验",
        referring_domain="待登记",
        kind="inbound",
        verify_status="unverified",
        our_presence="untested",
        domain_metric="untested",
        status="identified",
        notes=f"从信号「{signal.theme}」开外链跟进。逐条核验，禁止一键群发。",
    )
    db.add(gap)
    db.commit()
    db.refresh(gap)
    return ChainFeedOut(
        chain="offsite",
        created_id=gap.id,
        title=f"外链跟进：{signal.theme}",
        redirect_path="/offsite",
    )
