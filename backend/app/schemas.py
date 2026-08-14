from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    role: str
    tenant_id: str
    tenant_name: str
    site_origin: str = ""


class DashboardSummary(BaseModel):
    tenant_name: str
    markets_count: int
    priority_markets: int
    seo_in_progress: int
    seo_pending_review: int
    seo_ready: int
    open_work_orders: int
    inquiries_total: int
    qualified_inquiries: int
    geo_prompts: int
    geo_untested: int
    geo_recorded: int
    geo_assets_draft: int
    geo_tickets_open: int
    onsite_pages: int
    onsite_open_low: int
    onsite_open_high: int
    onsite_open_critical: int = 0
    llm_status: str = "未配置"
    offsite_gaps: int
    offsite_outreach_open: int
    links_unverified: int
    distribution_jobs: int


class MarketCreate(BaseModel):
    name: str
    region: str
    country_code: str = Field(min_length=2, max_length=8)
    primary_locale: str
    status: str = "watching"
    opportunity_score: int = Field(default=50, ge=0, le=100)
    notes: str | None = None


class MarketUpdate(BaseModel):
    name: str | None = None
    region: str | None = None
    country_code: str | None = None
    primary_locale: str | None = None
    status: str | None = None
    opportunity_score: int | None = Field(default=None, ge=0, le=100)
    notes: str | None = None


class MarketOut(BaseModel):
    id: str
    name: str
    region: str
    country_code: str
    primary_locale: str
    status: str
    opportunity_score: int
    notes: str | None
    competitor_count: int = 0
    demand_count: int = 0
    seo_count: int = 0
    created_at: datetime | None = None


class CompetitorCreate(BaseModel):
    name: str
    website: str | None = None
    positioning: str | None = None
    notes: str | None = None


class CompetitorOut(BaseModel):
    id: str
    market_id: str
    name: str
    website: str | None
    positioning: str | None
    notes: str | None
    created_at: datetime | None = None


class DemandSignalCreate(BaseModel):
    theme: str
    locale: str
    intensity: int = Field(default=3, ge=1, le=5)
    intent: str = "informational"
    source: str = "manual"
    notes: str | None = None


class DemandSignalOut(BaseModel):
    id: str
    market_id: str
    theme: str
    locale: str
    intensity: int
    intent: str
    source: str
    notes: str | None
    created_at: datetime | None = None


class InsightBriefIn(BaseModel):
    summary: str = ""
    opportunities: str = ""
    risks: str = ""
    recommended_actions: str = ""


class InsightBriefOut(InsightBriefIn):
    id: str
    market_id: str
    updated_at: datetime | None = None


class MarketDetailOut(MarketOut):
    competitors: list[CompetitorOut] = []
    demand_signals: list[DemandSignalOut] = []
    brief: InsightBriefOut | None = None


class SeoPageCreate(BaseModel):
    title: str
    target_keyword: str
    locale: str
    market_id: str | None = None
    demand_signal_id: str | None = None
    notes: str | None = None


class SeoPageUpdate(BaseModel):
    title: str | None = None
    target_keyword: str | None = None
    locale: str | None = None
    market_id: str | None = None
    outline: str | None = None
    draft_body: str | None = None
    meta_title: str | None = None
    meta_description: str | None = None
    notes: str | None = None
    status: str | None = None


class SeoPageOut(BaseModel):
    id: str
    title: str
    target_keyword: str
    locale: str
    status: str
    market_id: str | None
    demand_signal_id: str | None
    outline: str
    draft_body: str
    meta_title: str
    meta_description: str
    notes: str | None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ConfirmReadyIn(BaseModel):
    confirmed: bool = False
    note: str | None = None


class WorkOrderCreate(BaseModel):
    title: str
    type: str = "other"
    acceptance_criteria: str | None = None
    notes: str | None = None
    seo_page_id: str | None = None
    market_id: str | None = None


class WorkOrderUpdate(BaseModel):
    title: str | None = None
    type: str | None = None
    status: str | None = None
    acceptance_criteria: str | None = None
    notes: str | None = None
    seo_page_id: str | None = None
    market_id: str | None = None
    assignee_id: str | None = None


class WorkOrderOut(BaseModel):
    id: str
    title: str
    type: str
    status: str
    assignee_id: str | None
    seo_page_id: str | None
    market_id: str | None
    acceptance_criteria: str | None
    notes: str | None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class WorkOrderStatusIn(BaseModel):
    status: str


class InquiryCreate(BaseModel):
    source: str
    contact: str
    quality: str = "unreviewed"
    related_seo_page_id: str | None = None
    related_work_order_id: str | None = None
    related_market_id: str | None = None
    notes: str | None = None


class GeoObservationOut(BaseModel):
    id: str
    prompt_id: str
    engine: str
    engine_label: str = ""
    region: str = ""
    status: str
    notes: str | None
    observed_at: datetime | None = None


class GeoObservationUpdate(BaseModel):
    status: str
    notes: str | None = None


class GeoPromptCreate(BaseModel):
    prompt_text: str
    locale: str
    market_id: str | None = None
    seo_page_id: str | None = None
    demand_signal_id: str | None = None


class GeoPromptOut(BaseModel):
    id: str
    prompt_text: str
    locale: str
    market_id: str | None
    seo_page_id: str | None
    demand_signal_id: str | None
    diagnosis: str = "untested"
    diagnosis_label: str = "未测"
    observations: list[GeoObservationOut] = []
    created_at: datetime | None = None
    cite_rate: str = "未测"
    absorption_rate: str = "未测"
    ai_status: str = "untested"
    evidence: str = ""


class GeoDiagnosisIn(BaseModel):
    diagnosis: str


class GeoTicketCreate(BaseModel):
    prompt_id: str
    title: str
    diagnosis: str = "untested"
    rationale: str = ""
    acceptance_criteria: str = ""


class GeoTicketOut(BaseModel):
    id: str
    prompt_id: str
    title: str
    diagnosis: str
    diagnosis_label: str = "未测"
    rationale: str
    acceptance_criteria: str
    status: str
    verified_note: str | None
    ai_status: str = "untested"
    ai_review: str = ""
    evidence: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None


class GeoTicketVerifyIn(BaseModel):
    confirmed: bool = False
    note: str | None = None


class GeoAssetOut(BaseModel):
    id: str
    kind: str
    title: str
    body: str
    status: str
    ai_status: str = "untested"
    updated_at: datetime | None = None


class GeoAssetUpdate(BaseModel):
    body: str


class GeoChecklistItemOut(BaseModel):
    id: str
    seo_page_id: str
    item_key: str
    label: str
    status: str
    notes: str | None


class GeoChecklistItemUpdate(BaseModel):
    status: str
    notes: str | None = None


class GeoSummary(BaseModel):
    prompts: int
    untested: int
    recorded: int
    checklist_untested: int
    assets_draft: int
    tickets_open: int = 0
    cite_rate: str = "未测"


class InquiryOut(BaseModel):
    id: str
    source: str
    contact: str
    quality: str
    related_seo_page_id: str | None
    related_work_order_id: str | None
    related_market_id: str | None
    notes: str | None
    created_at: datetime | None = None


class SitePageCreate(BaseModel):
    path: str
    locale: str
    title: str
    market_id: str | None = None
    seo_page_id: str | None = None
    meta_title: str = ""
    meta_description: str = ""
    meta_keywords: str = ""
    headings: str = ""
    internal_links: str = ""
    structured_data: str = ""
    canonical: str = ""
    notes: str | None = None


class SitePageUpdate(BaseModel):
    title: str | None = None
    meta_title: str | None = None
    meta_description: str | None = None
    meta_keywords: str | None = None
    headings: str | None = None
    internal_links: str | None = None
    structured_data: str | None = None
    canonical: str | None = None
    notes: str | None = None


class OnsiteIssueOut(BaseModel):
    id: str
    page_id: str
    page_path: str = ""
    page_title: str = ""
    category: str
    title: str
    detail: str
    proposed_change: str
    severity: str = "low"
    risk: str
    status: str
    metric_status: str
    ai_status: str = "untested"
    ai_diagnosis: str = ""
    ai_review: str = ""
    ai_review_verdict: str = "untested"
    evidence: str = ""


class OnsiteIssueCreate(BaseModel):
    category: str
    title: str
    detail: str = ""
    proposed_change: str = ""
    severity: str | None = None
    risk: str | None = None


class OnsiteDraftIn(BaseModel):
    proposed_change: str


class OnsiteBoardOut(BaseModel):
    pages: int
    analyzed_pages: int
    counts: dict[str, int]
    groups: dict[str, list[OnsiteIssueOut]]


class ContentBriefOut(BaseModel):
    id: str
    title: str
    target_keyword: str
    locale: str
    status: str
    serp_features: str = "未测"
    note: str = "无 SERP / GSC 源，不编造精选摘要或 People Also Ask。"


class CrawlOrSeedOut(BaseModel):
    seeded: int
    pages: int
    note: str


class SiteOriginIn(BaseModel):
    site_origin: str


class SiteSettingsOut(BaseModel):
    site_origin: str
    note: str = "只抓已登记页。主机名必须与 origin 一致，不猜 www。"


class FetchPageResultOut(BaseModel):
    page_id: str | None = None
    path: str
    url: str
    crawl_status: str
    http_status: int | None = None
    final_url: str = ""
    needs_js: bool = False
    error: str = ""
    verified: int = 0
    created: int = 0


class FetchRegisteredOut(BaseModel):
    origin: str
    fetched: int
    failed: int
    verified: int
    created: int
    pages: int
    note: str
    results: list[FetchPageResultOut] = []
    ai_status: str = "未配置"


class AnalyzeOut(BaseModel):
    created: int
    skipped: int
    verified: int = 0
    pages: int
    note: str = "分析只读观察层，不改改稿，也不应用到线上。"
    ai_status: str = "未配置"


class AiStatusOut(BaseModel):
    configured: bool
    status: str
    env_var: str
    base_url: str
    model: str
    note: str


class AiAssistOut(BaseModel):
    status: str
    step: str
    applied_draft: bool = False
    diagnosis: str = ""
    draft: str = ""
    review: str = ""
    review_verdict: str = "未测"
    evidence: str = ""
    detail: str = ""


class AiStepIn(BaseModel):
    step: str = "all"


class SitePageOut(BaseModel):
    id: str
    path: str
    locale: str
    title: str
    market_id: str | None
    seo_page_id: str | None
    meta_title: str
    meta_description: str
    meta_keywords: str
    headings: str
    internal_links: str
    structured_data: str
    canonical: str = ""
    index_status: str
    crawl_status: str
    fetched_at: datetime | None = None
    final_url: str = ""
    http_status: int | None = None
    needs_js: bool = False
    html_lang: str = ""
    hreflang: str = ""
    viewport: str = ""
    json_ld_types: str = ""
    crawl_error: str = ""
    notes: str | None
    open_issue_count: int = 0
    analyzed_at: datetime | None = None


class SitePageDetailOut(SitePageOut):
    issues: list[OnsiteIssueOut] = []


class BacklinkGapCreate(BaseModel):
    competitor_name: str
    referring_domain: str
    competitor_url: str | None = None
    link_url: str | None = None
    kind: str = "competitor"
    market_id: str | None = None
    our_presence: str = "none"
    notes: str | None = None


class BacklinkGapUpdate(BaseModel):
    status: str | None = None
    verify_status: str | None = None
    notes: str | None = None
    link_url: str | None = None
    kind: str | None = None


class OutreachOut(BaseModel):
    id: str
    gap_id: str
    contact: str
    channel: str
    status: str
    notes: str | None


class OutreachCreate(BaseModel):
    contact: str
    channel: str = "email"
    notes: str | None = None


class BacklinkGapOut(BaseModel):
    id: str
    competitor_name: str
    referring_domain: str
    competitor_url: str | None
    link_url: str | None = None
    kind: str = "competitor"
    verify_status: str = "unverified"
    market_id: str | None
    our_presence: str
    domain_metric: str
    status: str
    notes: str | None
    ai_status: str = "untested"
    ai_review: str = ""
    evidence: str = ""
    outreach: list[OutreachOut] = []


class LinkCheckerOut(BaseModel):
    counts: dict[str, int]
    domain_metric: str = "未测"
    note: str = "这是断链式核验清单，不是 Ahrefs / Semrush 外链指数。"
    links: list[BacklinkGapOut] = []


class ChainFeedOut(BaseModel):
    chain: str
    created_id: str
    title: str
    redirect_path: str


class DistributionJobCreate(BaseModel):
    title: str
    target_url: str
    provider_key: str
    payload_summary: str = ""


class DistributionJobOut(BaseModel):
    id: str
    title: str
    target_url: str
    provider_key: str
    payload_summary: str
    status: str
    last_result: str
    last_detail: str | None


class ProviderOut(BaseModel):
    key: str
    label: str
    configured: bool
    status: str
    env_var: str


class SendResultOut(BaseModel):
    sent: bool
    provider_status: str
    detail: str
    job: DistributionJobOut
