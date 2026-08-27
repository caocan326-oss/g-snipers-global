from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: str = ""
    password: str = ""


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
    inquiries_month: int = 0
    inquiries_month_unlinked: int = 0
    fact_pack_ready: bool = False
    fact_pack_status: str = ""
    geo_prompts: int
    geo_untested: int
    geo_recorded: int
    geo_assets_draft: int
    geo_tickets_open: int
    geo_evidence_results: int = 0
    geo_latest_sampled: int = 0
    geo_latest_mentioned: int = 0
    geo_watch_due: int = 0
    this_week_onsite: int = 0
    this_week_open: int = 0
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
    trend: str = ""
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


class SeoRankDistributionOut(BaseModel):
    top_10: int = 0
    top_30: int = 0
    top_50: int = 0
    beyond_50: int = 0
    unranked: int = 0
    total: int = 0


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
    keyword_rank_distribution: SeoRankDistributionOut = SeoRankDistributionOut()
    serp_rank_distribution: SeoRankDistributionOut = SeoRankDistributionOut()
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
    weekly_onsite: list[WorkbenchItem] = []
    weekly_pinned: bool = False
    weekly_can_restore: bool = False
    geo_questions: list[WorkbenchItem] = []
    geo_trust_sources: list[WorkbenchItem] = []
    geo_competitors: list[WorkbenchItem] = []
    geo_trust_note: str = ""


class CustomerBriefSection(BaseModel):
    key: str
    title: str
    body: str = ""
    items: list[str] = []


class CustomerBriefOut(BaseModel):
    title: str
    headline: str
    markdown: str
    generated_at: datetime
    untested: list[str] = []
    this_week: list[str] = []
    paste_text: str = ""
    sections: list[CustomerBriefSection] = []
    english_title: str = ""
    english_headline: str = ""
    english_markdown: str = ""
    english_paste: str = ""


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
    tenant_name: str | None = None
    markets: list[ProjectTargetMarketIn] = Field(default_factory=list)
    keywords: list[ProjectTargetKeywordIn] = Field(default_factory=list)
    competitors: list[ProjectTargetCompetitorIn] = Field(default_factory=list)
    confirm_site_switch: bool = False


class ProjectTargetsOut(BaseModel):
    tenant_name: str = ""
    site_origin: str = ""
    markets: list[MarketDetailOut] = Field(default_factory=list)
    target_market_count: int = 0
    keyword_count: int = 0
    competitor_count: int = 0
    primary_market_id: str | None = None
    readiness: str = "incomplete"
    note: str = ""


class SiteArchiveOut(BaseModel):
    id: str
    site_origin: str
    archived_at: datetime | None = None
    restored_at: datetime | None = None
    note: str = ""
    counts: dict[str, int] = {}
    readable_counts: dict[str, int] = {}


class SiteArchiveDeleteIn(BaseModel):
    confirm: str = ""


class SiteArchiveRestoreOut(BaseModel):
    restored: bool
    site_origin: str
    archived_current: bool = False
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
    related_prompt_id: str | None = None
    notes: str | None = None


class InquiryPatch(BaseModel):
    quality: str | None = None
    related_prompt_id: str | None = None
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
    recorded_from: str = ""
    source_note: str = ""


class GeoPromptTrendPoint(BaseModel):
    at: str = ""
    mentioned: bool = False
    owned: bool = False
    note: str = ""
    others: list[str] = []


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
    sample_verdict: str = ""
    recorded_from: str = ""
    recorded_from_label: str = "已记原句"
    source_note: str = ""
    sample_compare_note: str = ""
    sample_trend: list[GeoPromptTrendPoint] = []
    trend_note: str = ""
    cited_others: list[str] = []
    competitor_note: str = ""
    page_draft: str = ""
    faq_draft: str = ""
    llms_txt: str = ""
    cite_stage: str = "draft"
    cite_stage_label: str = ""
    cite_published_url: str = ""
    cite_paste: str = ""
    watch_due: bool = False
    watch_note: str = ""
    last_sampled_at: datetime | None = None
    next_watch_at: datetime | None = None


class GeoDiagnosisIn(BaseModel):
    diagnosis: str


class GeoCiteStageIn(BaseModel):
    stage: str
    published_url: str = ""


class GeoTicketCreate(BaseModel):
    prompt_id: str
    title: str
    diagnosis: str = "untested"
    rationale: str = ""
    acceptance_criteria: str = ""
    priority: str = "P2"
    owner_hint: str = ""
    recommended_action: str = ""
    retest_method: str = ""


class GeoTicketOut(BaseModel):
    id: str
    prompt_id: str
    title: str
    diagnosis: str
    diagnosis_label: str = "未测"
    rationale: str
    acceptance_criteria: str
    priority: str = "P2"
    owner_hint: str = ""
    recommended_action: str = ""
    customer_note: str = ""
    customer_paste: str = ""
    page_label: str = ""
    page_url: str = ""
    channel: str = ""
    channel_key: str = ""
    compose_url: str = ""
    offsite_draft: str = ""
    offsite_url: str = ""
    retest_method: str = ""
    retest_result: str = ""
    sample_note: str = ""
    handoff: str = "drafted"
    handoff_label: str = ""
    result_url: str = ""
    blocked_reason: str = ""
    status: str
    verified_note: str | None
    ai_status: str = "untested"
    ai_review: str = ""
    evidence: str = ""
    last_checked_at: datetime | None = None
    closed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class GeoTicketVerifyIn(BaseModel):
    confirmed: bool = False
    note: str | None = None


class GeoTicketHandoffIn(BaseModel):
    handoff: str
    note: str | None = None
    result_url: str = ""


class GeoTicketOffsiteIn(BaseModel):
    post_url: str = ""


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


class GeoTrustSource(BaseModel):
    host: str
    kind: str
    kind_label: str
    hits: int
    prompt_count: int = 0
    sample_url: str = ""
    sample_prompt: str = ""


class GeoTrustCompetitor(BaseModel):
    name: str
    hits: int
    prompt_count: int = 0
    registered: bool = False
    sample_prompt: str = ""


class GeoTrustRound(BaseModel):
    label: str
    at: str = ""
    mentioned: bool = False
    owned: bool = False
    hosts: list[str] = []
    owned_hosts: list[str] = []
    other_hosts: list[str] = []
    competitors: list[str] = []
    sampled: int = 0
    mentioned_count: int = 0


class GeoTrustPrompt(BaseModel):
    prompt_id: str
    prompt_text: str
    latest: GeoTrustRound | None = None
    previous: GeoTrustRound | None = None
    compare: str = ""


class GeoTrustMap(BaseModel):
    sources: list[GeoTrustSource] = []
    competitors: list[GeoTrustCompetitor] = []
    owned_hits: int = 0
    other_hits: int = 0
    marketplace_hits: int = 0
    competitor_site_hits: int = 0
    note: str = ""
    empty: bool = True
    prompts: list[GeoTrustPrompt] = []
    rounds: list[GeoTrustRound] = []
    compare_note: str = ""


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
    latest_run_at: datetime | None = None
    latest_sampled: int = 0
    latest_mentioned: int = 0
    latest_owned: int = 0
    latest_third_party: int = 0
    previous_sampled: int = 0
    previous_mentioned: int = 0
    previous_owned: int = 0
    compare_note: str = ""
    latest_mention_split: str = ""
    watch_due: int = 0
    watch_count: int = 0
    watch_interval_days: int = 7
    trust_map: GeoTrustMap = Field(default_factory=GeoTrustMap)


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


class GeoGroundedBatchOut(BaseModel):
    providers: list[str]
    results_count: int
    failed: list[str] = []
    note: str
    runs: list["GeoSampleRunOut"] = []


class GeoWatchItemOut(BaseModel):
    prompt_id: str
    prompt_text: str
    due: bool
    last_sampled_at: datetime | None = None
    next_watch_at: datetime | None = None
    note: str = ""


class GeoWatchListOut(BaseModel):
    interval_days: int = 7
    watching: int = 0
    due: int = 0
    items: list[GeoWatchItemOut] = []
    note: str = ""


class GeoWatchRunDueOut(BaseModel):
    due: int = 0
    ran: int = 0
    prompt_ids: list[str] = []
    providers: list[str] = []
    results_count: int = 0
    failed: list[str] = []
    note: str = ""
    runs: list["GeoSampleRunOut"] = []


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


class GeoSampleResultVerifyIn(BaseModel):
    confirmed: bool = False
    checked_url: str = ""
    passed: bool = True
    note: str | None = None


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
    marketplace_citations: list[str] = []
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
    related_prompt_id: str | None = None
    related_prompt_text: str = ""
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
    page_url: str = ""
    category: str
    title: str
    detail: str
    proposed_change: str
    severity: str = "low"
    risk: str
    priority: str = "P2"
    status: str
    metric_status: str
    ai_status: str = "untested"
    ai_diagnosis: str = ""
    ai_review: str = ""
    ai_review_verdict: str = "untested"
    evidence: str = ""
    impact: str = ""
    acceptance_criteria: str = ""
    recommended_action: str = ""
    review_required: bool = False
    retest_method: str = ""
    retest_result: str = ""
    result_url: str = ""
    blocked_reason: str = ""
    owner_hint: str = ""
    customer_note: str = ""
    customer_paste: str = ""
    sent_to_customer: bool = False
    last_checked_at: datetime | None = None
    closed_at: datetime | None = None


class OnsiteIssueCreate(BaseModel):
    category: str
    title: str
    detail: str = ""
    proposed_change: str = ""
    severity: str | None = None
    risk: str | None = None
    priority: str = "P2"
    owner_hint: str = ""
    acceptance_criteria: str = ""
    recommended_action: str = ""
    retest_method: str = ""


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
    this_week: list[OnsiteIssueOut] = []
    weekly_pinned: bool = False
    can_restore: bool = False


class WeeklyOnsiteOut(BaseModel):
    this_week: list[OnsiteIssueOut] = []
    weekly_pinned: bool = False
    can_restore: bool = False
    note: str = ""


class OnsiteGuideStepOut(BaseModel):
    key: str
    label: str
    status: str


class OnsiteGuideOut(BaseModel):
    current: str
    complete: bool = False
    action_key: str
    action_label: str
    filter_key: str = ""
    narrative: str
    ai_status: str
    origin: str = ""
    pages: int = 0
    fetched: int = 0
    needs_draft: int = 0
    ready_to_execute: int = 0
    waiting_retest: int = 0
    open_high: int = 0
    steps: list[OnsiteGuideStepOut]


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
    confirm_site_switch: bool = False


class SiteSettingsOut(BaseModel):
    site_origin: str
    note: str = "只抓已登记页。主机名必须与 origin 一致，不猜 www。"


class IntegrationSettingsIn(BaseModel):
    gsc_oauth_client_id: str | None = None
    gsc_oauth_client_secret: str | None = None
    gsc_oauth_redirect_uri: str | None = None
    pagespeed_api_key: str | None = None
    ce17_user: str | None = None
    ce17_api_pwd: str | None = None
    brightdata_dataset_api_key: str | None = None
    brightdata_serp_zone: str | None = None
    brightdata_serp_dataset_id: str | None = None
    brightdata_serp_endpoint: str | None = None
    clear_keys: list[str] = []


class IntegrationFieldOut(BaseModel):
    key: str
    label: str
    configured: bool
    masked_value: str = ""
    source: str = "none"


class IntegrationSettingsOut(BaseModel):
    fields: list[IntegrationFieldOut]
    gsc_configured: bool
    pagespeed_configured: bool
    google_relay_configured: bool = False
    ce17_configured: bool = False
    brightdata_serp_configured: bool
    note: str = "密钥只在后端保存；前端只显示是否已配置和掩码。"


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
    limit: int = Field(default=50, ge=1, le=50)


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
    rank_distribution: SeoRankDistributionOut = SeoRankDistributionOut()
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
    keyword_rank_distribution: SeoRankDistributionOut = SeoRankDistributionOut()
    by_country: list[SeoPerformanceBucketOut] = []
    by_query: list[SeoPerformanceBucketOut] = []
    by_page: list[SeoPerformanceBucketOut] = []
    speed_latest: list[PageSpeedAuditOut] = []
    imports: list[SeoPerformanceImportOut] = []
    serp: SerpSummaryOut | None = None


class GscStatusOut(BaseModel):
    configured: bool
    connected: bool
    relay_configured: bool = False
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
    title: str = ""
    issue_type: str = "competitor_gap"
    source: str = "manual"
    source_platform_id: str = ""
    competitor_name: str
    referring_domain: str
    competitor_url: str | None = None
    link_url: str | None = None
    kind: str = "competitor"
    market_id: str | None = None
    priority: str = "P2"
    our_presence: str = "none"
    owner_hint: str = ""
    acceptance_criteria: str = ""
    recommended_action: str = ""
    retest_method: str = ""
    retest_result: str = ""
    result_url: str = ""
    blocked_reason: str = ""
    notes: str | None = None


class BacklinkGapUpdate(BaseModel):
    status: str | None = None
    verify_status: str | None = None
    notes: str | None = None
    link_url: str | None = None
    kind: str | None = None
    title: str | None = None
    issue_type: str | None = None
    source: str | None = None
    source_platform_id: str | None = None
    priority: str | None = None
    owner_hint: str | None = None
    acceptance_criteria: str | None = None
    recommended_action: str | None = None
    retest_method: str | None = None
    retest_result: str | None = None
    result_url: str | None = None
    blocked_reason: str | None = None


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
    title: str = ""
    issue_type: str = "competitor_gap"
    source: str = "manual"
    source_platform_id: str = ""
    competitor_name: str
    referring_domain: str
    competitor_url: str | None
    link_url: str | None = None
    kind: str = "competitor"
    priority: str = "P2"
    verify_status: str = "unverified"
    market_id: str | None
    our_presence: str
    domain_metric: str
    status: str
    owner_hint: str = ""
    acceptance_criteria: str = ""
    recommended_action: str = ""
    retest_method: str = ""
    retest_result: str = ""
    result_url: str = ""
    blocked_reason: str = ""
    notes: str | None
    ai_status: str = "untested"
    ai_review: str = ""
    evidence: str = ""
    last_checked_at: datetime | None = None
    closed_at: datetime | None = None
    outreach: list[OutreachOut] = []


class OffsiteOpportunityGenerateOut(BaseModel):
    created: int
    skipped: int
    from_geo: int = 0
    from_seo: int = 0
    from_onsite: int = 0
    note: str
    gaps: list[BacklinkGapOut] = []


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
    gap_id: str | None = None
    platform_id: str | None = None
    account_id: str | None = None
    content_asset_id: str | None = None
    task_type: str = "profile_create"
    payload_summary: str = ""
    owner_hint: str = ""
    result_url: str = ""
    blocked_reason: str = ""


class DistributionJobOut(BaseModel):
    id: str
    gap_id: str | None = None
    platform_id: str | None = None
    account_id: str | None = None
    content_asset_id: str | None = None
    title: str
    target_url: str
    provider_key: str
    task_type: str = "profile_create"
    payload_summary: str
    owner_hint: str = ""
    status: str
    result_url: str = ""
    verify_status: str = "pending"
    blocked_reason: str = ""
    last_result: str
    last_detail: str | None
    due_at: datetime | None = None
    last_checked_at: datetime | None = None


class DistributionJobUpdate(BaseModel):
    status: str | None = None
    platform_id: str | None = None
    account_id: str | None = None
    content_asset_id: str | None = None
    owner_hint: str | None = None
    result_url: str | None = None
    verify_status: str | None = None
    blocked_reason: str | None = None
    payload_summary: str | None = None


class DistributionSubmitResultIn(BaseModel):
    result_url: str
    evidence: str = ""
    verify_status: str = "pending"


class DistributionGuideOut(BaseModel):
    job_id: str
    platform_name: str = ""
    submission_mode: str = ""
    task_type: str = ""
    materials: list[str] = []
    checklist: list[str] = []
    risk_notes: list[str] = []
    placement_checks: list[str] = []


class PlacementCheckOut(BaseModel):
    job_id: str
    result_url: str
    target_url: str = ""
    http_status: int | None = None
    is_live: bool = False
    brand_mentioned: bool = False
    target_link_found: bool = False
    link_attr: str = "unknown"
    note: str


class ExecutionItemOut(BaseModel):
    id: str
    source_module: str
    title: str
    subtitle: str = ""
    href: str
    status: str
    priority: str = "P2"
    owner_hint: str = ""
    acceptance_criteria: str = ""
    evidence: str = ""
    recommended_action: str = ""
    customer_note: str = ""
    customer_paste: str = ""
    retest_method: str = ""
    retest_result: str = ""
    sample_note: str = ""
    handoff: str = ""
    handoff_label: str = ""
    result_url: str = ""
    blocked_reason: str = ""
    updated_at: datetime | None = None


class ExecutionBoardOut(BaseModel):
    total_open: int
    blocked: int
    needs_retest: int
    items: list[ExecutionItemOut] = []


class SourcePlatformCreate(BaseModel):
    platform_key: str
    name: str
    domain: str = ""
    source_type: str = "directory"
    regions: str = ""
    industry_tags: str = ""
    base_url: str = ""
    listing_model: str = "directory_profile"
    submission_mode: str = "manual_login"
    has_official_api: bool = False
    risk_level: str = "medium"
    status: str = "active"
    notes: str = ""


class SourcePlatformOut(SourcePlatformCreate):
    id: str
    accounts_count: int = 0
    connectors_count: int = 0
    compose_url: str = ""
    docs_url: str = ""
    api_endpoint: str = ""
    api_auth_mode: str = ""
    profile_url: str = ""
    profile_http_status: int | None = None
    profile_is_live: bool = False
    profile_site_found: bool = False
    profile_checked_at: datetime | None = None
    profile_note: str = ""
    profile_missing_page: bool = False


class CheckProfileIn(BaseModel):
    profile_url: str = ""


class ProfileCheckOut(BaseModel):
    platform_id: str
    profile_url: str
    http_status: int | None = None
    is_live: bool = False
    site_found: bool = False
    brand_mentioned: bool = False
    missing_channel_page: bool = False
    note: str
    sent: bool = False


class OfficialApiOut(BaseModel):
    platform_key: str
    label: str
    compose_url: str
    docs_url: str
    api_endpoint: str
    http_method: str
    auth_mode: str
    env_hint: str
    note: str


class OfficialApiSeedOut(BaseModel):
    created: int
    updated: int
    apis: list[OfficialApiOut] = []


class OfficialPayloadOut(BaseModel):
    sent: bool = False
    platform_key: str
    label: str
    compose_url: str
    docs_url: str
    api_endpoint: str
    http_method: str
    auth_mode: str
    env_hint: str
    note: str
    customer_body: dict = {}


class OffsiteCustomerPasteOut(BaseModel):
    asset_id: str
    channel: str
    compose_url: str = ""
    paste: str


class MarkOwnApiIn(BaseModel):
    model_config = {"extra": "forbid"}
    confirmed: bool


class SourcePlatformSeedOut(BaseModel):
    created: int
    skipped: int
    platforms: list[SourcePlatformOut] = []


class FactPackCreate(BaseModel):
    name: str = "Default Fact Pack"
    legal_name: str = ""
    brand_names: str = ""
    website: str = ""
    product_categories_en: str = ""
    certifications: str = ""
    key_specs: str = ""
    banned_claims: str = ""
    contact_public: str = ""
    approved_boilerplate_en: str = ""
    status: str = "draft"


class FactPackUpdate(BaseModel):
    name: str | None = None
    legal_name: str | None = None
    brand_names: str | None = None
    website: str | None = None
    product_categories_en: str | None = None
    certifications: str | None = None
    key_specs: str | None = None
    banned_claims: str | None = None
    contact_public: str | None = None
    approved_boilerplate_en: str | None = None
    status: str | None = None


class FactPackOut(FactPackCreate):
    id: str
    version: int = 1
    approved_by: str = ""
    approved_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class FactPackFromMaterialsIn(BaseModel):
    source_text: str
    name: str = "Default Fact Pack"


class FactPackFromMaterialsOut(BaseModel):
    fact_pack: FactPackOut
    notes: list[str] = []
    omitted: list[str] = []


class ContentAssetCreate(BaseModel):
    fact_pack_id: str | None = None
    asset_type: str = "company_blurb"
    title: str
    body_md: str = ""
    locale: str = "en"
    keywords: str = ""
    entities: str = ""


class ContentAssetUpdate(BaseModel):
    fact_pack_id: str | None = None
    asset_type: str | None = None
    title: str | None = None
    body_md: str | None = None
    locale: str | None = None
    keywords: str | None = None
    entities: str | None = None
    status: str | None = None
    human_review_note: str | None = None


class ContentAssetOut(BaseModel):
    id: str
    fact_pack_id: str | None = None
    fact_pack_name: str = ""
    asset_type: str
    title: str
    body_md: str
    locale: str
    keywords: str = ""
    entities: str = ""
    status: str
    ai_review_status: str = "untested"
    ai_review: str = ""
    human_review_note: str = ""
    approved_by: str = ""
    approved_at: datetime | None = None
    version: int = 1
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ContentAssetReviewOut(BaseModel):
    asset: ContentAssetOut
    findings: list[str] = []


class ContentAssetApproveIn(BaseModel):
    confirmed: bool
    note: str = ""


class ContentAssetGenerateIn(BaseModel):
    fact_pack_id: str
    asset_type: str = "company_blurb"
    title: str = ""
    locale: str = "en"


class PlatformAccountCreate(BaseModel):
    platform_id: str
    label: str
    login_identifier: str = ""
    auth_method: str = "manual_only"
    vault_ref: str = ""
    owner_hint: str = ""
    scope: str = "shared"
    status: str = "active"
    risk_level: str = "medium"
    regions_allowed: str = ""
    notes: str = ""


class PlatformAccountOut(PlatformAccountCreate):
    id: str
    platform_name: str = ""
    last_verified_at: datetime | None = None
    last_used_at: datetime | None = None


class PlatformConnectorCreate(BaseModel):
    platform_id: str
    provider_key: str
    auth_mode: str = "manual"
    capabilities: str = "draft_only"
    status: str = "manual_only"
    env_var: str = ""
    notes: str = ""


class PlatformConnectorOut(PlatformConnectorCreate):
    id: str
    platform_name: str = ""
    last_verified_at: datetime | None = None


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


class BackupDumpOut(BaseModel):
    filename: str
    size_bytes: int
    modified_at: str


class BackupStatusOut(BaseModel):
    schedule_enabled: bool
    local_dir: str
    keep: int
    offsite_kind: str
    offsite_configured: bool
    offsite_dir: str = ""
    offsite_scp_set: bool = False
    latest: BackupDumpOut | None = None
    dumps: list[BackupDumpOut] = []
    note: str = ""


class BackupCreateOut(BaseModel):
    filename: str
    size_bytes: int
    offsite: str
    note: str = ""


class UsageMeterOut(BaseModel):
    key: str
    label: str
    vendor: str
    hint: str
    used: int
    limit: int
    remaining: int


class UsageTodayOut(BaseModel):
    day: str
    tenant_id: str
    tenant_name: str
    meters: list[UsageMeterOut]


class UsageTenantOut(BaseModel):
    tenant_id: str
    tenant_name: str
    site_origin: str = ""
    meters: list[UsageMeterOut]


class UsageBoardOut(BaseModel):
    day: str
    tenants: list[UsageTenantOut]


class UsageQuotaPatch(BaseModel):
    tenant_id: str
    meter: str
    daily_limit: int = Field(ge=0, le=10000)
