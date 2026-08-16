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


class WorkbenchItem(BaseModel):
    id: str
    title: str
    subtitle: str = ""
    href: str
    status: str = ""
    tone: str = "default"
    meta: str = ""
    action_label: str = "查看"


class WorkbenchChain(BaseModel):
    key: str
    title: str
    href: str
    primary: int
    secondary: str
    health: str
    tone: str = "default"
    action_label: str


class WorkbenchSeoBucket(BaseModel):
    key: str
    clicks: int = 0
    impressions: int = 0
    ctr: float | None = None
    position: float | None = None


class WorkbenchSeoPerformance(BaseModel):
    days: int = 28
    data_status: str = "未导入"
    total_clicks: int = 0
    total_impressions: int = 0
    avg_ctr: float | None = None
    avg_position: float | None = None
    indexed_pages: int = 0
    index_pending_pages: int = 0
    backlink_domains: int = 0
    unverified_backlinks: int = 0
    authority_status: str = "未接入"
    pagespeed_status: str = "未测速"
    latest_speed_score: int | None = None
    serp_status: str = "未配置"
    serp_runs: int = 0
    serp_own_visible_runs: int = 0
    serp_competitor_visible_runs: int = 0
    serp_avg_own_position: float | None = None
    top_countries: list[WorkbenchSeoBucket] = []
    top_keywords: list[WorkbenchSeoBucket] = []
    top_pages: list[WorkbenchSeoBucket] = []


class WorkbenchOut(BaseModel):
    summary: DashboardSummary
    site_origin: str = ""
    diagnostic_status: str
    seo_performance: WorkbenchSeoPerformance = WorkbenchSeoPerformance()
    next_actions: list[WorkbenchItem] = []
    seo_items: list[WorkbenchItem] = []
    geo_items: list[WorkbenchItem] = []
    recent_signals: list[WorkbenchItem] = []
    chains: list[WorkbenchChain] = []
    deferred_modules: list[WorkbenchItem] = []


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


class ProjectTargetMarketIn(BaseModel):
    name: str
    region: str = ""
    country_code: str = Field(min_length=2, max_length=8)
    primary_locale: str = "en-US"
    status: str = "priority"
    opportunity_score: int = Field(default=70, ge=0, le=100)


class ProjectTargetKeywordIn(BaseModel):
    theme: str
    locale: str = "en-US"
    market_id: str | None = None
    market_name: str | None = None
    country_code: str | None = None
    intent: str = "commercial"
    intensity: int = Field(default=4, ge=1, le=5)


class ProjectTargetCompetitorIn(BaseModel):
    name: str
    website: str | None = None
    market_id: str | None = None
    market_name: str | None = None
    country_code: str | None = None
    positioning: str | None = None


class ProjectTargetsIn(BaseModel):
    site_origin: str | None = None
    markets: list[ProjectTargetMarketIn] = Field(default_factory=list)
    keywords: list[ProjectTargetKeywordIn] = Field(default_factory=list)
    competitors: list[ProjectTargetCompetitorIn] = Field(default_factory=list)


class ProjectTargetsOut(BaseModel):
    site_origin: str = ""
    markets: list[MarketDetailOut] = Field(default_factory=list)
    target_market_count: int = 0
    keyword_count: int = 0
    competitor_count: int = 0
    primary_market_id: str | None = None
    readiness: str = "incomplete"
    note: str = ""


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
    surface: str = "manual_ai_answer"
    sample_type: str = "manual"
    status: str
    evidence_tier: str = "none"
    evidence_label: str = "未测"
    response_excerpt: str = ""
    citation_urls: str = ""
    brand_mentions: str = ""
    competitor_mentions: str = ""
    interpretation_note: str = ""
    notes: str | None
    observed_at: datetime | None = None


class GeoObservationUpdate(BaseModel):
    status: str
    surface: str | None = None
    sample_type: str | None = None
    response_excerpt: str | None = None
    citation_urls: str | None = None
    brand_mentions: str | None = None
    competitor_mentions: str | None = None
    interpretation_note: str | None = None
    notes: str | None = None


class GeoPromptCreate(BaseModel):
    prompt_text: str
    locale: str
    market_id: str | None = None
    seo_page_id: str | None = None
    demand_signal_id: str | None = None
    prompt_pack_id: str = "custom"
    prompt_key: str = ""
    prompt_type: str = "custom"


class GeoPromptOut(BaseModel):
    id: str
    prompt_text: str
    locale: str
    market_id: str | None
    seo_page_id: str | None
    demand_signal_id: str | None
    prompt_pack_id: str = "custom"
    prompt_key: str = ""
    prompt_type: str = "custom"
    diagnosis: str = "untested"
    diagnosis_label: str = "未测"
    observations: list[GeoObservationOut] = []
    created_at: datetime | None = None
    mention_rate: str = "未测"
    cite_rate: str = "未测"
    verified_citation_rate: str = "未测"
    competitor_rate: str = "未测"
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
    mention_rate: str = "未测"
    cite_rate: str = "未测"
    verified_citation_rate: str = "未测"
    competitor_rate: str = "未测"
    absorption_rate: str = "未测"
    competitor_mentions: int = 0
    sample_runs: int = 0
    evidence_results: int = 0
    latest_run_id: str | None = None


class GeoSeedOut(BaseModel):
    created: int
    skipped: int
    prompts: int
    note: str


class GeoReportOut(BaseModel):
    title: str
    markdown: str
    generated_at: datetime


class GeoReportTableOut(BaseModel):
    filename: str
    csv: str
    generated_at: datetime


class GeoSampleRunCreate(BaseModel):
    note: str = ""
    prompt_set_id: str = "manual-panel"
    region_hint: str = ""
    language: str = ""


class GeoAutoSampleIn(BaseModel):
    prompt_ids: list[str] = []
    engine: str = "llm"
    provider: str = "deepseek"
    model: str = ""
    trials: int = Field(default=1, ge=1, le=3)
    limit: int = Field(default=8, ge=1, le=30)
    region_hint: str = ""
    web_grounded: str = "false"


class GeoProviderStatusOut(BaseModel):
    key: str
    label: str
    configured: bool
    web_grounded: bool
    env_var: str
    role: str
    status: str
    note: str = ""


class GeoProviderStatusListOut(BaseModel):
    providers: list[GeoProviderStatusOut] = []
    note: str = "DeepSeek/LLM 可用于分析；联网 AI 搜索 provider 只有返回 citation/source 时才计入真实引用。"


class GeoSampleResultOut(BaseModel):
    id: str
    run_id: str
    prompt_id: str
    observation_id: str | None = None
    evidence_id: str
    trial_index: int
    prompt_type: str = "custom"
    engine: str
    engine_label: str = ""
    model: str
    web_grounded: str
    surface: str
    prompt_text_hash: str
    answer_text_hash: str
    answer_excerpt: str = ""
    mentioned: bool
    citations: list[str] = []
    owned_citations: list[str] = []
    third_party_citations: list[str] = []
    brand_hits: str = ""
    competitor_hits: str = ""
    verification_status: str
    verification_note: str = ""
    sampled_at: datetime | None = None


class GeoSampleRunOut(BaseModel):
    id: str
    protocol_version: str
    prompt_set_id: str
    config_hash: str
    domain: str
    brand_names: list[str] = []
    engines: list[str] = []
    trials_per_prompt: int
    region_hint: str = ""
    language: str = ""
    status: str
    note: str = ""
    started_at: datetime | None = None
    finished_at: datetime | None = None
    results_count: int = 0
    mention_rate: str = "未测"
    cite_rate: str = "未测"
    verified_citation_rate: str = "未测"
    results: list[GeoSampleResultOut] = []
    aggregate: dict = {}


class GeoTicketDraftOut(BaseModel):
    created: int
    skipped: int
    note: str
    tickets: list[GeoTicketOut] = []


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
    impact: str = ""
    recommended_action: str = ""
    review_required: bool = False
    retest_method: str = ""
    owner_hint: str = ""


class OnsiteIssueCreate(BaseModel):
    category: str
    title: str
    detail: str = ""
    proposed_change: str = ""
    severity: str | None = None
    risk: str | None = None


class OnsiteDraftIn(BaseModel):
    proposed_change: str


class OnsiteStatusIn(BaseModel):
    confirmed: bool = False
    note: str | None = None


class OnsiteBoardOut(BaseModel):
    pages: int
    analyzed_pages: int
    counts: dict[str, int]
    status_counts: dict[str, int] = {}
    workflow_counts: dict[str, int] = {}
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
    fetch_mode: str = "http"
    render_status: str = "not_needed"
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


class CrawlSiteIn(BaseModel):
    max_urls: int = Field(default=50, ge=1, le=300)
    max_depth: int = Field(default=2, ge=0, le=5)


class CrawlSessionOut(BaseModel):
    id: str
    origin: str
    mode: str
    max_urls: int
    max_depth: int
    status: str
    discovered: int
    fetched: int
    failed: int
    created: int
    verified: int
    robots_blocked: int
    needs_js: int
    note: str
    started_at: datetime | None = None
    finished_at: datetime | None = None


class SeoReportOut(BaseModel):
    title: str
    markdown: str
    generated_at: datetime


class SeoReportTableOut(BaseModel):
    filename: str
    csv: str
    generated_at: datetime


class SeoPerformanceImportIn(BaseModel):
    source: str = Field(default="gsc_csv", pattern="^(gsc_csv|bing_csv)$")
    filename: str = ""
    csv_text: str = Field(min_length=1)


class SeoPerformanceImportOut(BaseModel):
    id: str
    source: str
    filename: str
    rows_imported: int
    note: str
    imported_at: datetime | None = None


class SeoPerformanceBucketOut(BaseModel):
    key: str
    clicks: int
    impressions: int
    ctr: float | None = None
    position: float | None = None


class SerpRunIn(BaseModel):
    keywords: list[str] = []
    country: str = "US"
    locale: str = "en-US"
    device: str = Field(default="desktop", pattern="^(desktop|mobile)$")
    limit: int = Field(default=10, ge=1, le=20)


class SerpResultOut(BaseModel):
    position: int
    title: str
    url: str
    domain: str
    snippet: str = ""
    result_type: str = "organic"
    ownership: str = "third_party"


class SerpRunOut(BaseModel):
    id: str
    provider: str
    keyword: str
    country: str
    locale: str
    device: str
    status: str
    own_domain: str = ""
    own_best_position: int | None = None
    competitor_best_position: int | None = None
    result_count: int = 0
    third_party_count: int = 0
    error: str = ""
    created_at: datetime | None = None
    results: list[SerpResultOut] = []


class SerpRunBatchOut(BaseModel):
    status: str
    configured: bool
    ran: int = 0
    failed: int = 0
    note: str = ""
    runs: list[SerpRunOut] = []


class SerpSummaryOut(BaseModel):
    configured: bool
    status: str
    total_runs: int = 0
    own_visible_runs: int = 0
    competitor_visible_runs: int = 0
    avg_own_position: float | None = None
    latest_runs: list[SerpRunOut] = []
    top_third_party_domains: list[dict[str, int | str]] = []


class PageSpeedRunIn(BaseModel):
    urls: list[str] = []
    strategies: list[str] = ["mobile", "desktop"]
    limit: int = Field(default=3, ge=1, le=10)


class PageSpeedAuditOut(BaseModel):
    id: str
    url: str
    strategy: str
    status: str
    performance_score: int | None = None
    seo_score: int | None = None
    accessibility_score: int | None = None
    best_practices_score: int | None = None
    lcp_ms: int | None = None
    inp_ms: int | None = None
    cls: float | None = None
    detail: str = ""
    audited_at: datetime | None = None


class SeoPerformanceSummaryOut(BaseModel):
    gsc_status: str
    bing_status: str
    pagespeed_status: str
    total_clicks: int
    total_impressions: int
    avg_ctr: float | None = None
    avg_position: float | None = None
    by_country: list[SeoPerformanceBucketOut] = []
    by_query: list[SeoPerformanceBucketOut] = []
    by_page: list[SeoPerformanceBucketOut] = []
    speed_latest: list[PageSpeedAuditOut] = []
    imports: list[SeoPerformanceImportOut] = []
    serp: SerpSummaryOut | None = None


class GscStatusOut(BaseModel):
    configured: bool
    connected: bool
    status: str
    site_url: str = ""
    last_sync_at: datetime | None = None
    last_error: str = ""
    redirect_uri: str = ""
    note: str = ""


class GscAuthUrlOut(BaseModel):
    configured: bool
    auth_url: str = ""
    redirect_uri: str = ""
    note: str = ""


class GscConnectIn(BaseModel):
    code: str = Field(min_length=1)
    site_url: str = ""


class GscSyncIn(BaseModel):
    days: int = Field(default=28, ge=1, le=180)
    row_limit: int = Field(default=25000, ge=100, le=25000)


class GscSyncOut(BaseModel):
    status: str
    rows_imported: int = 0
    date_start: str = ""
    date_end: str = ""
    note: str = ""
    last_error: str = ""


class DataSyncRunOut(BaseModel):
    id: str
    source: str
    mode: str
    status: str
    rows_imported: int = 0
    submitted: int = 0
    note: str = ""
    started_at: datetime | None = None
    finished_at: datetime | None = None


class DataSyncStatusOut(BaseModel):
    runs: list[DataSyncRunOut] = []


class DataSyncRunDueIn(BaseModel):
    force: bool = False
    sources: list[str] = Field(default_factory=lambda: ["gsc"])


class DataSyncRunDueOut(BaseModel):
    status: str
    ran: int = 0
    skipped: int = 0
    runs: list[DataSyncRunOut] = []
    note: str = ""


class BingStatusOut(BaseModel):
    configured: bool
    status: str
    note: str


class IndexNowStatusOut(BaseModel):
    configured: bool
    host: str = ""
    key_location: str = ""
    last_submitted_at: datetime | None = None
    last_status: str = ""
    note: str = ""


class IndexNowSubmitIn(BaseModel):
    urls: list[str] = []
    paths: list[str] = []


class IndexNowSubmitOut(BaseModel):
    status: str
    submitted: int = 0
    http_status: int | None = None
    note: str = ""


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
    processed: int = 0
    remaining: int = 0
    limit: int = 0


class AiStepIn(BaseModel):
    step: str = "all"
    limit: int | None = None


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
    content_type: str = ""
    ttfb_ms: int | None = None
    redirect_count: int = 0
    html_bytes: int = 0
    body_hash: str = ""
    needs_js: bool = False
    fetch_mode: str = "http"
    render_status: str = "not_needed"
    render_final_url: str = ""
    render_word_count: int = 0
    html_lang: str = ""
    hreflang: str = ""
    viewport: str = ""
    json_ld_types: str = ""
    crawl_error: str = ""
    discovery_source: str = "manual"
    is_in_sitemap: str = "untested"
    meta_robots: str = ""
    x_robots_tag: str = ""
    word_count: int = 0
    image_count: int = 0
    images_missing_alt: int = 0
    external_link_count: int = 0
    page_type: str = "other"
    url_depth: int = 0
    priority_hint: str = "P2"
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
