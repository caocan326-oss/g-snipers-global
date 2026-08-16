import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def new_id() -> str:
    return str(uuid.uuid4())


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(120))
    site_origin: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    users: Mapped[list["User"]] = relationship(back_populates="tenant")


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(String(40), default="account_manager")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tenant: Mapped[Tenant] = relationship(back_populates="users")


class Market(Base):
    __tablename__ = "markets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    region: Mapped[str] = mapped_column(String(40), nullable=False)
    country_code: Mapped[str] = mapped_column(String(8), nullable=False)
    primary_locale: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="watching")
    opportunity_score: Mapped[int] = mapped_column(Integer, default=50)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    competitors: Mapped[list["Competitor"]] = relationship(back_populates="market", cascade="all, delete-orphan")
    demand_signals: Mapped[list["DemandSignal"]] = relationship(
        back_populates="market", cascade="all, delete-orphan"
    )
    brief: Mapped["InsightBrief | None"] = relationship(back_populates="market", uselist=False)


class Competitor(Base):
    __tablename__ = "competitors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    market_id: Mapped[str] = mapped_column(ForeignKey("markets.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    website: Mapped[str | None] = mapped_column(String(500))
    positioning: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    market: Mapped[Market] = relationship(back_populates="competitors")


class DemandSignal(Base):
    __tablename__ = "demand_signals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    market_id: Mapped[str] = mapped_column(ForeignKey("markets.id"), nullable=False, index=True)
    theme: Mapped[str] = mapped_column(String(300), nullable=False)
    locale: Mapped[str] = mapped_column(String(16), nullable=False)
    intensity: Mapped[int] = mapped_column(Integer, default=3)
    intent: Mapped[str] = mapped_column(String(40), default="informational")
    source: Mapped[str] = mapped_column(String(40), default="manual")
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    market: Mapped[Market] = relationship(back_populates="demand_signals")


class InsightBrief(Base):
    __tablename__ = "insight_briefs"
    __table_args__ = (UniqueConstraint("market_id", name="uq_insight_briefs_market"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    market_id: Mapped[str] = mapped_column(ForeignKey("markets.id"), nullable=False, index=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    opportunities: Mapped[str] = mapped_column(Text, default="")
    risks: Mapped[str] = mapped_column(Text, default="")
    recommended_actions: Mapped[str] = mapped_column(Text, default="")
    updated_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    market: Mapped[Market] = relationship(back_populates="brief")


class SeoPage(Base):
    __tablename__ = "seo_pages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    market_id: Mapped[str | None] = mapped_column(ForeignKey("markets.id"), index=True)
    demand_signal_id: Mapped[str | None] = mapped_column(ForeignKey("demand_signals.id"))
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    target_keyword: Mapped[str] = mapped_column(String(300), nullable=False)
    locale: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="idea", index=True)
    outline: Mapped[str] = mapped_column(Text, default="")
    draft_body: Mapped[str] = mapped_column(Text, default="")
    meta_title: Mapped[str] = mapped_column(String(200), default="")
    meta_description: Mapped[str] = mapped_column(String(400), default="")
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class WorkOrder(Base):
    __tablename__ = "work_orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    type: Mapped[str] = mapped_column(String(40), default="other")
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    assignee_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    seo_page_id: Mapped[str | None] = mapped_column(ForeignKey("seo_pages.id"))
    market_id: Mapped[str | None] = mapped_column(ForeignKey("markets.id"))
    acceptance_criteria: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Inquiry(Base):
    __tablename__ = "inquiries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(80), nullable=False)
    contact: Mapped[str] = mapped_column(String(300), nullable=False)
    quality: Mapped[str] = mapped_column(String(20), default="unreviewed")
    related_seo_page_id: Mapped[str | None] = mapped_column(ForeignKey("seo_pages.id"))
    related_work_order_id: Mapped[str | None] = mapped_column(ForeignKey("work_orders.id"))
    related_market_id: Mapped[str | None] = mapped_column(ForeignKey("markets.id"))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GeoPrompt(Base):
    """A question to spot-check in AI answers. Results are AM-recorded, never invented."""

    __tablename__ = "geo_prompts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    market_id: Mapped[str | None] = mapped_column(ForeignKey("markets.id"), index=True)
    seo_page_id: Mapped[str | None] = mapped_column(ForeignKey("seo_pages.id"))
    demand_signal_id: Mapped[str | None] = mapped_column(ForeignKey("demand_signals.id"))
    prompt_pack_id: Mapped[str] = mapped_column(String(120), default="custom")
    prompt_key: Mapped[str] = mapped_column(String(80), default="")
    prompt_type: Mapped[str] = mapped_column(String(40), default="custom")
    prompt_text: Mapped[str] = mapped_column(String(500), nullable=False)
    locale: Mapped[str] = mapped_column(String(16), nullable=False)
    diagnosis: Mapped[str] = mapped_column(String(40), default="untested")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ai_status: Mapped[str] = mapped_column(String(20), default="untested")
    evidence: Mapped[str] = mapped_column(Text, default="")

    observations: Mapped[list["GeoObservation"]] = relationship(
        back_populates="prompt", cascade="all, delete-orphan"
    )
    tickets: Mapped[list["GeoTicket"]] = relationship(
        back_populates="prompt", cascade="all, delete-orphan"
    )


class GeoObservation(Base):
    __tablename__ = "geo_observations"
    __table_args__ = (UniqueConstraint("prompt_id", "engine", name="uq_geo_obs_prompt_engine"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    prompt_id: Mapped[str] = mapped_column(ForeignKey("geo_prompts.id"), nullable=False, index=True)
    engine: Mapped[str] = mapped_column(String(40), nullable=False)
    surface: Mapped[str] = mapped_column(String(60), default="manual_ai_answer")
    sample_type: Mapped[str] = mapped_column(String(40), default="manual")
    status: Mapped[str] = mapped_column(String(20), default="untested")
    response_excerpt: Mapped[str] = mapped_column(Text, default="")
    citation_urls: Mapped[str] = mapped_column(Text, default="")
    brand_mentions: Mapped[str] = mapped_column(Text, default="")
    competitor_mentions: Mapped[str] = mapped_column(Text, default="")
    interpretation_note: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str | None] = mapped_column(Text)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    observed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))

    prompt: Mapped[GeoPrompt] = relationship(back_populates="observations")


class GeoSampleRun(Base):
    """A protocol-bound GEO sampling run. Results can come from manual evidence or API adapters."""

    __tablename__ = "geo_sample_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    protocol_version: Mapped[str] = mapped_column(String(80), default="geo-test-protocol-v1")
    prompt_set_id: Mapped[str] = mapped_column(String(120), default="manual-panel")
    config_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String(500), default="")
    brand_names: Mapped[str] = mapped_column(Text, default="")
    engines: Mapped[str] = mapped_column(Text, default="")
    trials_per_prompt: Mapped[int] = mapped_column(Integer, default=1)
    region_hint: Mapped[str] = mapped_column(String(80), default="")
    language: Mapped[str] = mapped_column(String(32), default="")
    operator_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(30), default="done", index=True)
    note: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    results: Mapped[list["GeoSampleResult"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class GeoSampleResult(Base):
    __tablename__ = "geo_sample_results"
    __table_args__ = (
        UniqueConstraint("run_id", "prompt_id", "engine", "trial_index", name="uq_geo_sample_trial"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("geo_sample_runs.id"), nullable=False, index=True)
    prompt_id: Mapped[str] = mapped_column(ForeignKey("geo_prompts.id"), nullable=False, index=True)
    observation_id: Mapped[str | None] = mapped_column(ForeignKey("geo_observations.id"), index=True)
    evidence_id: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    trial_index: Mapped[int] = mapped_column(Integer, default=1)
    prompt_type: Mapped[str] = mapped_column(String(40), default="custom")
    engine: Mapped[str] = mapped_column(String(40), nullable=False)
    model: Mapped[str] = mapped_column(String(120), default="manual")
    web_grounded: Mapped[str] = mapped_column(String(20), default="unknown")
    surface: Mapped[str] = mapped_column(String(60), default="manual_ai_answer")
    prompt_text_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    answer_text_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    answer_excerpt: Mapped[str] = mapped_column(Text, default="")
    mentioned: Mapped[bool] = mapped_column(Boolean, default=False)
    citations_json: Mapped[str] = mapped_column(Text, default="[]")
    owned_citations_json: Mapped[str] = mapped_column(Text, default="[]")
    third_party_citations_json: Mapped[str] = mapped_column(Text, default="[]")
    brand_hits: Mapped[str] = mapped_column(Text, default="")
    competitor_hits: Mapped[str] = mapped_column(Text, default="")
    verification_status: Mapped[str] = mapped_column(String(20), default="pending")
    verification_note: Mapped[str] = mapped_column(Text, default="")
    sampled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    run: Mapped[GeoSampleRun] = relationship(back_populates="results")
    prompt: Mapped[GeoPrompt] = relationship()
    observation: Mapped[GeoObservation | None] = relationship()


class GeoAsset(Base):
    __tablename__ = "geo_assets"
    __table_args__ = (UniqueConstraint("tenant_id", "kind", name="uq_geo_assets_tenant_kind"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="draft")
    ai_status: Mapped[str] = mapped_column(String(20), default="untested")
    updated_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class GeoChecklistItem(Base):
    __tablename__ = "geo_checklist_items"
    __table_args__ = (UniqueConstraint("seo_page_id", "item_key", name="uq_geo_check_page_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    seo_page_id: Mapped[str] = mapped_column(ForeignKey("seo_pages.id"), nullable=False, index=True)
    item_key: Mapped[str] = mapped_column(String(40), nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="untested")
    notes: Mapped[str | None] = mapped_column(Text)

    seo_page: Mapped[SeoPage] = relationship()


class GeoTicket(Base):
    """Implementation ticket with acceptance; verify or reopen after sampling."""

    __tablename__ = "geo_tickets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    prompt_id: Mapped[str] = mapped_column(ForeignKey("geo_prompts.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    diagnosis: Mapped[str] = mapped_column(String(40), default="untested")
    rationale: Mapped[str] = mapped_column(Text, default="")
    acceptance_criteria: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    verified_note: Mapped[str | None] = mapped_column(Text)
    ai_status: Mapped[str] = mapped_column(String(20), default="untested")
    ai_review: Mapped[str] = mapped_column(Text, default="")
    evidence: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    prompt: Mapped["GeoPrompt"] = relationship(back_populates="tickets")


class SitePage(Base):
    __tablename__ = "site_pages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    market_id: Mapped[str | None] = mapped_column(ForeignKey("markets.id"), index=True)
    seo_page_id: Mapped[str | None] = mapped_column(ForeignKey("seo_pages.id"))
    path: Mapped[str] = mapped_column(String(400), nullable=False)
    locale: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    meta_title: Mapped[str] = mapped_column(Text, default="")
    meta_description: Mapped[str] = mapped_column(Text, default="")
    meta_keywords: Mapped[str] = mapped_column(String(300), default="")
    headings: Mapped[str] = mapped_column(Text, default="")
    internal_links: Mapped[str] = mapped_column(Text, default="")
    structured_data: Mapped[str] = mapped_column(Text, default="")
    canonical: Mapped[str] = mapped_column(Text, default="")
    index_status: Mapped[str] = mapped_column(String(20), default="untested")
    crawl_status: Mapped[str] = mapped_column(String(32), default="untested")
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    final_url: Mapped[str] = mapped_column(String(500), default="")
    http_status: Mapped[int | None] = mapped_column(Integer)
    content_type: Mapped[str] = mapped_column(String(160), default="")
    ttfb_ms: Mapped[int | None] = mapped_column(Integer)
    redirect_count: Mapped[int] = mapped_column(Integer, default=0)
    html_bytes: Mapped[int] = mapped_column(Integer, default=0)
    body_hash: Mapped[str] = mapped_column(String(64), default="")
    needs_js: Mapped[bool] = mapped_column(Boolean, default=False)
    html_lang: Mapped[str] = mapped_column(String(32), default="")
    hreflang: Mapped[str] = mapped_column(Text, default="")
    viewport: Mapped[str] = mapped_column(String(300), default="")
    json_ld_types: Mapped[str] = mapped_column(String(400), default="")
    crawl_error: Mapped[str] = mapped_column(Text, default="")
    discovery_source: Mapped[str] = mapped_column(String(40), default="manual")
    is_in_sitemap: Mapped[str] = mapped_column(String(20), default="untested")
    meta_robots: Mapped[str] = mapped_column(String(300), default="")
    x_robots_tag: Mapped[str] = mapped_column(String(300), default="")
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    image_count: Mapped[int] = mapped_column(Integer, default=0)
    images_missing_alt: Mapped[int] = mapped_column(Integer, default=0)
    external_link_count: Mapped[int] = mapped_column(Integer, default=0)
    analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    issues: Mapped[list["OnsiteIssue"]] = relationship(back_populates="page", cascade="all, delete-orphan")


class CrawlSession(Base):
    __tablename__ = "crawl_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    origin: Mapped[str] = mapped_column(String(500), nullable=False)
    mode: Mapped[str] = mapped_column(String(40), default="site")
    max_urls: Mapped[int] = mapped_column(Integer, default=50)
    max_depth: Mapped[int] = mapped_column(Integer, default=2)
    status: Mapped[str] = mapped_column(String(30), default="running", index=True)
    discovered: Mapped[int] = mapped_column(Integer, default=0)
    fetched: Mapped[int] = mapped_column(Integer, default=0)
    failed: Mapped[int] = mapped_column(Integer, default=0)
    created: Mapped[int] = mapped_column(Integer, default=0)
    verified: Mapped[int] = mapped_column(Integer, default=0)
    robots_blocked: Mapped[int] = mapped_column(Integer, default=0)
    needs_js: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SeoPerformanceImport(Base):
    __tablename__ = "seo_performance_imports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(300), default="")
    rows_imported: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[str] = mapped_column(Text, default="")
    imported_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SeoPerformanceRow(Base):
    __tablename__ = "seo_performance_rows"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    import_id: Mapped[str | None] = mapped_column(ForeignKey("seo_performance_imports.id"), index=True)
    source: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    date: Mapped[str] = mapped_column(String(40), default="")
    country: Mapped[str] = mapped_column(String(120), default="")
    device: Mapped[str] = mapped_column(String(80), default="")
    query: Mapped[str] = mapped_column(String(500), default="", index=True)
    page_url: Mapped[str] = mapped_column(String(700), default="", index=True)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    ctr: Mapped[float | None] = mapped_column(Float)
    position: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PageSpeedAudit(Base):
    __tablename__ = "pagespeed_audits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(700), nullable=False, index=True)
    strategy: Mapped[str] = mapped_column(String(20), default="mobile")
    status: Mapped[str] = mapped_column(String(30), default="ok", index=True)
    performance_score: Mapped[int | None] = mapped_column(Integer)
    seo_score: Mapped[int | None] = mapped_column(Integer)
    accessibility_score: Mapped[int | None] = mapped_column(Integer)
    best_practices_score: Mapped[int | None] = mapped_column(Integer)
    lcp_ms: Mapped[int | None] = mapped_column(Integer)
    inp_ms: Mapped[int | None] = mapped_column(Integer)
    cls: Mapped[float | None] = mapped_column(Float)
    detail: Mapped[str] = mapped_column(Text, default="")
    audited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GscConnection(Base):
    __tablename__ = "gsc_connections"
    __table_args__ = (UniqueConstraint("tenant_id", name="uq_gsc_connections_tenant"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    site_url: Mapped[str] = mapped_column(String(700), default="")
    status: Mapped[str] = mapped_column(String(30), default="disconnected", index=True)
    access_token: Mapped[str] = mapped_column(Text, default="")
    refresh_token: Mapped[str] = mapped_column(Text, default="")
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scopes: Mapped[str] = mapped_column(Text, default="")
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str] = mapped_column(Text, default="")
    connected_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class GscSyncRun(Base):
    __tablename__ = "gsc_sync_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    connection_id: Mapped[str | None] = mapped_column(ForeignKey("gsc_connections.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="running", index=True)
    date_start: Mapped[str] = mapped_column(String(20), default="")
    date_end: Mapped[str] = mapped_column(String(20), default="")
    rows_imported: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DataSyncRun(Base):
    __tablename__ = "data_sync_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    mode: Mapped[str] = mapped_column(String(40), default="manual")
    status: Mapped[str] = mapped_column(String(30), default="running", index=True)
    rows_imported: Mapped[int] = mapped_column(Integer, default=0)
    submitted: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IndexNowSubmission(Base):
    __tablename__ = "indexnow_submissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    key_location: Mapped[str] = mapped_column(String(700), default="")
    urls: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="submitted", index=True)
    http_status: Mapped[int | None] = mapped_column(Integer)
    response_text: Mapped[str] = mapped_column(Text, default="")
    submitted_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OnsiteIssue(Base):
    """Monitor finding + execute task. High-risk never touches live without confirm."""

    __tablename__ = "onsite_issues"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    page_id: Mapped[str] = mapped_column(ForeignKey("site_pages.id"), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    detail: Mapped[str] = mapped_column(Text, default="")
    proposed_change: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[str] = mapped_column(String(10), default="low")
    risk: Mapped[str] = mapped_column(String(10), default="low")
    status: Mapped[str] = mapped_column(String(30), default="open", index=True)
    metric_status: Mapped[str] = mapped_column(String(20), default="untested")
    ai_status: Mapped[str] = mapped_column(String(20), default="untested")
    ai_diagnosis: Mapped[str] = mapped_column(Text, default="")
    ai_review: Mapped[str] = mapped_column(Text, default="")
    ai_review_verdict: Mapped[str] = mapped_column(String(20), default="untested")
    evidence: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    page: Mapped[SitePage] = relationship(back_populates="issues")


class BacklinkGap(Base):
    __tablename__ = "backlink_gaps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    market_id: Mapped[str | None] = mapped_column(ForeignKey("markets.id"))
    competitor_name: Mapped[str] = mapped_column(String(200), nullable=False)
    referring_domain: Mapped[str] = mapped_column(String(300), nullable=False)
    competitor_url: Mapped[str | None] = mapped_column(String(500))
    link_url: Mapped[str | None] = mapped_column(String(500))
    kind: Mapped[str] = mapped_column(String(20), default="competitor")
    verify_status: Mapped[str] = mapped_column(String(20), default="unverified")
    our_presence: Mapped[str] = mapped_column(String(20), default="none")
    domain_metric: Mapped[str] = mapped_column(String(20), default="untested")
    status: Mapped[str] = mapped_column(String(20), default="identified", index=True)
    notes: Mapped[str | None] = mapped_column(Text)
    ai_status: Mapped[str] = mapped_column(String(20), default="untested")
    ai_review: Mapped[str] = mapped_column(Text, default="")
    evidence: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    outreach: Mapped[list["OutreachItem"]] = relationship(back_populates="gap", cascade="all, delete-orphan")


class OutreachItem(Base):
    __tablename__ = "outreach_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    gap_id: Mapped[str] = mapped_column(ForeignKey("backlink_gaps.id"), nullable=False, index=True)
    contact: Mapped[str] = mapped_column(String(300), nullable=False)
    channel: Mapped[str] = mapped_column(String(40), default="email")
    status: Mapped[str] = mapped_column(String(20), default="todo")
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    gap: Mapped[BacklinkGap] = relationship(back_populates="outreach")


class DistributionJob(Base):
    __tablename__ = "distribution_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    target_url: Mapped[str] = mapped_column(String(500), nullable=False)
    provider_key: Mapped[str] = mapped_column(String(40), nullable=False)
    payload_summary: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)
    last_result: Mapped[str] = mapped_column(String(40), default="未发送")
    last_detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DistributionAttempt(Base):
    __tablename__ = "distribution_attempts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("distribution_jobs.id"), nullable=False, index=True)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    sent: Mapped[bool] = mapped_column(Boolean, default=False)
    result: Mapped[str] = mapped_column(String(40), default="未发送")
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PublishConfirmation(Base):
    """Human confirm gate: content is never auto-published."""

    __tablename__ = "publish_confirmations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    seo_page_id: Mapped[str] = mapped_column(ForeignKey("seo_pages.id"), nullable=False)
    confirmed_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=True)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AiRun(Base):
    """One AI engine step. Unconfigured / 未测 is stored honestly."""

    __tablename__ = "ai_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    chain: Mapped[str] = mapped_column(String(20), nullable=False)
    step: Mapped[str] = mapped_column(String(20), nullable=False)
    target_type: Mapped[str] = mapped_column(String(40), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="untested")
    output: Mapped[str] = mapped_column(Text, default="")
    evidence: Mapped[str] = mapped_column(Text, default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
