const TOKEN_KEY = "gsnipers_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export async function api<T>(path: string, init: RequestInit & { timeoutMs?: number } = {}): Promise<T> {
  const { timeoutMs, ...rest } = init;
  const headers = new Headers(rest.headers);
  if (!headers.has("Content-Type") && rest.body) {
    headers.set("Content-Type", "application/json");
  }
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const controller = timeoutMs ? new AbortController() : undefined;
  const timer = timeoutMs ? window.setTimeout(() => controller?.abort(), timeoutMs) : undefined;
  try {
    const res = await fetch(path, { ...rest, headers, signal: controller?.signal ?? rest.signal });
    if (res.status === 401 && typeof window !== "undefined") {
      clearToken();
      if (!path.includes("/api/auth/login")) {
        window.location.href = "/login";
      }
    }
    if (!res.ok) {
      let detail = res.statusText;
      try {
        const data = await res.json();
        detail = data.detail || JSON.stringify(data);
      } catch {
        /* ignore */
      }
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
    if (res.status === 204) return undefined as T;
    return res.json() as Promise<T>;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("请求超时，请稍后重试。测速和排名检查不会在后台偷偷完成。");
    }
    throw error;
  } finally {
    if (timer) window.clearTimeout(timer);
  }
}

export function siteOriginHost(raw: string): string {
  const text = raw.trim();
  if (!text) return "";
  try {
    return new URL(text.includes("://") ? text : `https://${text}`).hostname.toLowerCase();
  } catch {
    return "";
  }
}

export function looksLikeSiteOrigin(raw: string): boolean {
  const host = siteOriginHost(raw);
  if (!host) return false;
  if (host === "localhost" || host === "127.0.0.1") return true;
  const labels = host.split(".");
  return labels.length >= 2 && /^[a-z]{2,24}$/i.test(labels[labels.length - 1] || "");
}

export function confirmSiteSwitch(currentOrigin: string, nextOrigin: string): boolean {
  return window.confirm(
    `更换官网会归档当前工作台，页面上的检查、AI 搜索和清单都会换成新站点。\n\n当前：${currentOrigin || "未设置"}\n新官网：${nextOrigin}\n\n若这个新官网以前查过，会恢复那份历史，不会再造空站。确定更换？`,
  );
}

export type User = {
  id: string;
  email: string;
  name: string;
  role: string;
  tenant_id: string;
  tenant_name: string;
  site_origin?: string;
};

export type DashboardSummary = {
  tenant_name: string;
  markets_count: number;
  priority_markets: number;
  seo_in_progress: number;
  seo_pending_review: number;
  seo_ready: number;
  open_work_orders: number;
  inquiries_total: number;
  qualified_inquiries: number;
  geo_prompts: number;
  geo_untested: number;
  geo_recorded: number;
  geo_assets_draft: number;
  geo_tickets_open: number;
  geo_evidence_results?: number;
  geo_latest_sampled?: number;
  geo_latest_mentioned?: number;
  onsite_pages: number;
  onsite_open_low: number;
  onsite_open_high: number;
  onsite_open_critical: number;
  offsite_gaps: number;
  offsite_outreach_open: number;
  links_unverified: number;
  distribution_jobs: number;
  llm_status: string;
};

export type WorkbenchItem = {
  id: string;
  title: string;
  subtitle: string;
  href: string;
  status: string;
  tone: "default" | "green" | "amber" | "blue" | "red" | "brand";
  meta: string;
  action_label: string;
};

export type WorkbenchChain = {
  key: string;
  title: string;
  href: string;
  primary: number;
  secondary: string;
  health: string;
  tone: "default" | "green" | "amber" | "blue" | "red" | "brand";
  action_label: string;
};

export type WorkbenchSeoBucket = {
  key: string;
  clicks: number;
  impressions: number;
  ctr: number | null;
  position: number | null;
};

export type SeoRankDistribution = {
  top_10: number;
  top_30: number;
  top_50: number;
  beyond_50: number;
  unranked: number;
  total: number;
};

export type WorkbenchSeoPerformance = {
  days: number;
  data_status: string;
  total_clicks: number;
  total_impressions: number;
  avg_ctr: number | null;
  avg_position: number | null;
  indexed_pages: number;
  index_pending_pages: number;
  backlink_domains: number;
  unverified_backlinks: number;
  authority_status: string;
  pagespeed_status: string;
  latest_speed_score: number | null;
  serp_status: string;
  serp_runs: number;
  serp_own_visible_runs: number;
  serp_competitor_visible_runs: number;
  serp_avg_own_position: number | null;
  keyword_rank_distribution: SeoRankDistribution;
  serp_rank_distribution: SeoRankDistribution;
  top_countries: WorkbenchSeoBucket[];
  top_keywords: WorkbenchSeoBucket[];
  top_pages: WorkbenchSeoBucket[];
};

export type Workbench = {
  summary: DashboardSummary;
  site_origin: string;
  diagnostic_status: string;
  seo_performance: WorkbenchSeoPerformance;
  next_actions: WorkbenchItem[];
  seo_items: WorkbenchItem[];
  geo_items: WorkbenchItem[];
  recent_signals: WorkbenchItem[];
  chains: WorkbenchChain[];
  deferred_modules: WorkbenchItem[];
};

export type CustomerBriefSection = {
  key: string;
  title: string;
  body: string;
  items: string[];
};

export type CustomerBrief = {
  title: string;
  headline: string;
  markdown: string;
  generated_at: string;
  untested: string[];
  this_week: string[];
  sections: CustomerBriefSection[];
};

export type AiStatus = {
  configured: boolean;
  status: string;
  env_var: string;
  base_url: string;
  model: string;
  note: string;
};

export type AiAssist = {
  status: string;
  step: string;
  applied_draft: boolean;
  diagnosis: string;
  draft: string;
  review: string;
  review_verdict: string;
  evidence: string;
  detail: string;
  processed?: number;
  remaining?: number;
  limit?: number;
};

export type SeoPerformanceBucket = {
  key: string;
  clicks: number;
  impressions: number;
  ctr: number | null;
  position: number | null;
};

export type PageSpeedAudit = {
  id: string;
  url: string;
  strategy: string;
  status: string;
  performance_score: number | null;
  seo_score: number | null;
  accessibility_score: number | null;
  best_practices_score: number | null;
  lcp_ms: number | null;
  inp_ms: number | null;
  cls: number | null;
  detail: string;
  audited_at: string | null;
};

export type SeoPerformanceSummary = {
  gsc_status: string;
  bing_status: string;
  pagespeed_status: string;
  total_clicks: number;
  total_impressions: number;
  avg_ctr: number | null;
  avg_position: number | null;
  keyword_rank_distribution: SeoRankDistribution;
  by_country: SeoPerformanceBucket[];
  by_query: SeoPerformanceBucket[];
  by_page: SeoPerformanceBucket[];
  speed_latest: PageSpeedAudit[];
  imports: {
    id: string;
    source: string;
    filename: string;
    rows_imported: number;
    note: string;
    imported_at: string | null;
  }[];
  serp: SerpSummary | null;
};

export type SerpResult = {
  position: number;
  title: string;
  url: string;
  domain: string;
  snippet: string;
  result_type: string;
  ownership: string;
};

export type SerpRun = {
  id: string;
  provider: string;
  keyword: string;
  country: string;
  locale: string;
  device: string;
  status: string;
  own_domain: string;
  own_best_position: number | null;
  competitor_best_position: number | null;
  result_count: number;
  third_party_count: number;
  error: string;
  created_at: string | null;
  results: SerpResult[];
};

export type SerpSummary = {
  configured: boolean;
  status: string;
  total_runs: number;
  own_visible_runs: number;
  competitor_visible_runs: number;
  avg_own_position: number | null;
  rank_distribution: SeoRankDistribution;
  latest_runs: SerpRun[];
  top_third_party_domains: { domain: string; count: number }[];
};

export type SerpRunBatch = {
  status: string;
  configured: boolean;
  ran: number;
  failed: number;
  note: string;
  runs: SerpRun[];
};

export type GscStatus = {
  configured: boolean;
  connected: boolean;
  relay_configured?: boolean;
  status: string;
  site_url: string;
  last_sync_at: string | null;
  last_error: string;
  redirect_uri: string;
  note: string;
};

export type GscAuthUrl = {
  configured: boolean;
  auth_url: string;
  redirect_uri: string;
  note: string;
};

export type GscSyncResult = {
  status: string;
  rows_imported: number;
  date_start: string;
  date_end: string;
  note: string;
  last_error: string;
};

export type DataSyncRun = {
  id: string;
  source: string;
  mode: string;
  status: string;
  rows_imported: number;
  submitted: number;
  note: string;
  started_at: string | null;
  finished_at: string | null;
};

export type DataSyncStatus = {
  runs: DataSyncRun[];
};

export type DataSyncRunDueResult = {
  status: string;
  ran: number;
  skipped: number;
  runs: DataSyncRun[];
  note: string;
};

export type IntegrationField = {
  key: string;
  label: string;
  configured: boolean;
  masked_value: string;
  source: string;
};

export type IntegrationSettings = {
  fields: IntegrationField[];
  gsc_configured: boolean;
  pagespeed_configured: boolean;
  google_relay_configured?: boolean;
  ce17_configured?: boolean;
  brightdata_serp_configured: boolean;
  note: string;
};

export type BingStatus = {
  configured: boolean;
  status: string;
  note: string;
};

export type IndexNowStatus = {
  configured: boolean;
  host: string;
  key_location: string;
  last_submitted_at: string | null;
  last_status: string;
  note: string;
};

export type IndexNowSubmitResult = {
  status: string;
  submitted: number;
  http_status: number | null;
  note: string;
};

export type Market = {
  id: string;
  name: string;
  region: string;
  country_code: string;
  primary_locale: string;
  status: string;
  opportunity_score: number;
  notes: string | null;
  competitor_count: number;
  demand_count: number;
  seo_count: number;
};

export type Competitor = {
  id: string;
  market_id: string;
  name: string;
  website: string | null;
  positioning: string | null;
  notes: string | null;
};

export type DemandSignal = {
  id: string;
  market_id: string;
  theme: string;
  locale: string;
  intensity: number;
  intent: string;
  source: string;
  notes: string | null;
};

export type InsightBrief = {
  id: string;
  market_id: string;
  summary: string;
  opportunities: string;
  risks: string;
  recommended_actions: string;
};

export type MarketDetail = Market & {
  competitors: Competitor[];
  demand_signals: DemandSignal[];
  brief: InsightBrief | null;
};

export type ProjectTargets = {
  site_origin: string;
  markets: MarketDetail[];
  target_market_count: number;
  keyword_count: number;
  competitor_count: number;
  primary_market_id: string | null;
  readiness: string;
  note: string;
};

export type SiteArchive = {
  id: string;
  site_origin: string;
  archived_at: string | null;
  restored_at: string | null;
  note: string;
  counts: Record<string, number>;
  readable_counts: Record<string, number>;
};

export type SiteArchiveRestore = {
  restored: boolean;
  site_origin: string;
  archived_current: boolean;
  note: string;
};

export type ChainFeed = {
  chain: string;
  created_id: string;
  title: string;
  redirect_path: string;
};

export type SeoPage = {
  id: string;
  title: string;
  target_keyword: string;
  locale: string;
  status: string;
  market_id: string | null;
  demand_signal_id: string | null;
  outline: string;
  draft_body: string;
  meta_title: string;
  meta_description: string;
  notes: string | null;
};

export type WorkOrder = {
  id: string;
  title: string;
  type: string;
  status: string;
  assignee_id: string | null;
  seo_page_id: string | null;
  market_id: string | null;
  acceptance_criteria: string | null;
  notes: string | null;
};

export type Inquiry = {
  id: string;
  source: string;
  contact: string;
  quality: string;
  related_seo_page_id: string | null;
  related_work_order_id: string | null;
  related_market_id: string | null;
  notes: string | null;
  created_at: string | null;
};

export type GeoObservation = {
  id: string;
  prompt_id: string;
  engine: string;
  engine_label?: string;
  region?: string;
  surface?: string;
  sample_type?: string;
  status: string;
  evidence_tier?: string;
  evidence_label?: string;
  response_excerpt?: string;
  citation_urls?: string;
  brand_mentions?: string;
  competitor_mentions?: string;
  interpretation_note?: string;
  notes: string | null;
  observed_at: string | null;
};

export type GeoPrompt = {
  id: string;
  prompt_text: string;
  locale: string;
  market_id: string | null;
  seo_page_id: string | null;
  demand_signal_id?: string | null;
  prompt_pack_id?: string;
  prompt_key?: string;
  prompt_type?: string;
  diagnosis: string;
  diagnosis_label: string;
  observations: GeoObservation[];
  cite_rate?: string;
  mention_rate?: string;
  verified_citation_rate?: string;
  competitor_rate?: string;
  absorption_rate?: string;
  ai_status?: string;
  evidence?: string;
};

export type GeoSummary = {
  prompts: number;
  untested: number;
  recorded: number;
  checklist_untested: number;
  assets_draft: number;
  tickets_open: number;
  mention_rate: string;
  cite_rate: string;
  verified_citation_rate: string;
  competitor_rate: string;
  absorption_rate: string;
  competitor_mentions: number;
  sample_runs?: number;
  evidence_results?: number;
  latest_run_id?: string | null;
  latest_run_at?: string | null;
  latest_sampled?: number;
  latest_mentioned?: number;
  latest_owned?: number;
  latest_third_party?: number;
  previous_sampled?: number;
  previous_mentioned?: number;
  previous_owned?: number;
  compare_note?: string;
};

export type GeoReport = {
  title: string;
  markdown: string;
  generated_at: string;
};

export type GeoReportTable = {
  filename: string;
  csv: string;
  generated_at: string;
};

export type GeoSampleResult = {
  id: string;
  run_id: string;
  prompt_id: string;
  observation_id: string | null;
  evidence_id: string;
  trial_index: number;
  prompt_type?: string;
  engine: string;
  engine_label?: string;
  model: string;
  web_grounded: string;
  surface: string;
  prompt_text_hash: string;
  answer_text_hash: string;
  answer_excerpt: string;
  mentioned: boolean;
  citations: string[];
  owned_citations: string[];
  third_party_citations: string[];
  brand_hits: string;
  competitor_hits: string;
  verification_status: string;
  verification_note: string;
  sampled_at: string | null;
};

export type GeoSampleRun = {
  id: string;
  protocol_version: string;
  prompt_set_id: string;
  config_hash: string;
  domain: string;
  brand_names: string[];
  engines: string[];
  trials_per_prompt: number;
  region_hint: string;
  language: string;
  status: string;
  note: string;
  started_at: string | null;
  finished_at: string | null;
  results_count: number;
  mention_rate: string;
  cite_rate: string;
  verified_citation_rate: string;
  results: GeoSampleResult[];
  aggregate?: Record<string, unknown>;
};

export type GeoProviderStatus = {
  key: string;
  label: string;
  configured: boolean;
  web_grounded: boolean;
  env_var: string;
  role: string;
  status: string;
  note: string;
};

export type GeoProviderStatusList = {
  providers: GeoProviderStatus[];
  note: string;
};

export type GeoGroundedBatch = {
  providers: string[];
  results_count: number;
  failed: string[];
  note: string;
  runs: GeoSampleRun[];
};

export type GeoTicketDraft = {
  created: number;
  skipped: number;
  note: string;
  tickets: GeoTicket[];
};

export type GeoTicket = {
  id: string;
  prompt_id: string;
  title: string;
  diagnosis: string;
  diagnosis_label: string;
  rationale: string;
  acceptance_criteria: string;
  priority: string;
  owner_hint: string;
  recommended_action: string;
  retest_method: string;
  retest_result: string;
  blocked_reason: string;
  status: string;
  verified_note: string | null;
  ai_status?: string;
  ai_review?: string;
  evidence?: string;
  last_checked_at?: string | null;
  closed_at?: string | null;
};

export type GeoAsset = {
  id: string;
  kind: string;
  title: string;
  body: string;
  status: string;
  updated_at?: string | null;
};

export type SitePage = {
  id: string;
  path: string;
  locale: string;
  title: string;
  meta_title: string;
  meta_description: string;
  meta_keywords: string;
  headings: string;
  internal_links: string;
  structured_data: string;
  canonical?: string;
  index_status: string;
  crawl_status: string;
  fetched_at?: string | null;
  final_url?: string;
  http_status?: number | null;
  content_type?: string;
  ttfb_ms?: number | null;
  redirect_count?: number;
  html_bytes?: number;
  body_hash?: string;
  needs_js?: boolean;
  fetch_mode?: string;
  render_status?: string;
  render_final_url?: string;
  render_word_count?: number;
  html_lang?: string;
  hreflang?: string;
  viewport?: string;
  json_ld_types?: string;
  crawl_error?: string;
  discovery_source?: string;
  is_in_sitemap?: string;
  meta_robots?: string;
  x_robots_tag?: string;
  word_count?: number;
  image_count?: number;
  images_missing_alt?: number;
  external_link_count?: number;
  page_type?: string;
  url_depth?: number;
  priority_hint?: string;
  notes: string | null;
  open_issue_count: number;
  analyzed_at?: string | null;
};

export type FetchRegistered = {
  origin: string;
  fetched: number;
  failed: number;
  verified: number;
  created: number;
  pages: number;
  note: string;
  ai_status: string;
  results: {
    page_id: string | null;
    path: string;
    url: string;
    crawl_status: string;
    http_status: number | null;
    final_url: string;
    needs_js: boolean;
    fetch_mode: string;
    render_status: string;
    error: string;
    verified: number;
    created: number;
  }[];
};

export const crawlStatusLabel: Record<string, string> = {
  untested: "尚未查看",
  ok: "可正常访问",
  robots_disallow: "网站规则禁止",
  robots_blocked: "网站规则阻止",
  timeout: "超时",
  ssl_error: "安全证书失败",
  http_4xx: "页面不存在或打不开",
  http_5xx: "服务器错误",
  host_rejected: "网址不被接受",
  needs_js: "需浏览器才能显示",
  fetch_error: "查看失败",
  error: "查看失败",
};

export type OnsiteIssue = {
  id: string;
  page_id: string;
  page_path?: string;
  page_title?: string;
  category: string;
  title: string;
  detail: string;
  proposed_change: string;
  severity: string;
  risk: string;
  priority?: string;
  status: string;
  metric_status: string;
  ai_status?: string;
  ai_diagnosis?: string;
  ai_review?: string;
  ai_review_verdict?: string;
  evidence?: string;
  impact?: string;
  acceptance_criteria?: string;
  recommended_action?: string;
  review_required?: boolean;
  retest_method?: string;
  retest_result?: string;
  result_url?: string;
  blocked_reason?: string;
  owner_hint?: string;
  last_checked_at?: string | null;
  closed_at?: string | null;
};

export type OnsiteBoard = {
  pages: number;
  analyzed_pages: number;
  counts: { critical: number; high: number; low: number };
  status_counts: Record<string, number>;
  workflow_counts: Record<string, number>;
  groups: { critical: OnsiteIssue[]; high: OnsiteIssue[]; low: OnsiteIssue[] };
};

export type OnsiteGuide = {
  current: string;
  complete: boolean;
  action_key: string;
  action_label: string;
  filter_key: string;
  narrative: string;
  ai_status: string;
  origin: string;
  pages: number;
  fetched: number;
  needs_draft: number;
  ready_to_execute: number;
  waiting_retest: number;
  open_high: number;
  steps: { key: string; label: string; status: string }[];
};

export type CrawlSession = {
  id: string;
  origin: string;
  mode: string;
  max_urls: number;
  max_depth: number;
  status: string;
  discovered: number;
  fetched: number;
  failed: number;
  created: number;
  verified: number;
  robots_blocked: number;
  needs_js: number;
  note: string;
  started_at: string | null;
  finished_at: string | null;
};

export type SeoReport = {
  title: string;
  markdown: string;
  generated_at: string;
};

export type SeoReportTable = {
  filename: string;
  csv: string;
  generated_at: string;
};

export type ContentBrief = {
  id: string;
  title: string;
  target_keyword: string;
  locale: string;
  status: string;
  serp_features: string;
  note: string;
};

export type SitePageDetail = SitePage & { issues: OnsiteIssue[] };

export type OutreachItem = {
  id: string;
  gap_id: string;
  contact: string;
  channel: string;
  status: string;
  notes: string | null;
};

export type BacklinkGap = {
  id: string;
  title: string;
  issue_type: string;
  source: string;
  source_platform_id: string;
  competitor_name: string;
  referring_domain: string;
  competitor_url: string | null;
  link_url: string | null;
  kind: string;
  priority: string;
  verify_status: string;
  our_presence: string;
  domain_metric: string;
  status: string;
  owner_hint: string;
  acceptance_criteria: string;
  recommended_action: string;
  retest_method: string;
  retest_result: string;
  result_url: string;
  blocked_reason: string;
  notes: string | null;
  ai_status?: string;
  ai_review?: string;
  evidence?: string;
  last_checked_at: string | null;
  closed_at: string | null;
  outreach: OutreachItem[];
};

export type OffsiteOpportunityGeneration = {
  created: number;
  skipped: number;
  from_geo: number;
  from_seo: number;
  from_onsite: number;
  note: string;
  gaps: BacklinkGap[];
};

export type DistProvider = {
  key: string;
  label: string;
  configured: boolean;
  status: string;
  env_var: string;
};

export type DistJob = {
  id: string;
  gap_id: string | null;
  platform_id: string | null;
  account_id: string | null;
  content_asset_id: string | null;
  title: string;
  target_url: string;
  provider_key: string;
  task_type: string;
  payload_summary: string;
  owner_hint: string;
  status: string;
  result_url: string;
  verify_status: string;
  blocked_reason: string;
  last_result: string;
  last_detail: string | null;
  due_at: string | null;
  last_checked_at: string | null;
};

export type DistGuide = {
  job_id: string;
  platform_name: string;
  submission_mode: string;
  task_type: string;
  materials: string[];
  checklist: string[];
  risk_notes: string[];
  placement_checks: string[];
};

export type PlacementCheck = {
  job_id: string;
  result_url: string;
  target_url: string;
  http_status: number | null;
  is_live: boolean;
  brand_mentioned: boolean;
  target_link_found: boolean;
  link_attr: string;
  note: string;
};

export type ExecutionItem = {
  id: string;
  source_module: string;
  title: string;
  subtitle: string;
  href: string;
  status: string;
  priority: string;
  owner_hint: string;
  acceptance_criteria: string;
  evidence: string;
  recommended_action: string;
  retest_method: string;
  retest_result: string;
  result_url: string;
  blocked_reason: string;
  updated_at: string | null;
};

export type ExecutionBoard = {
  total_open: number;
  blocked: number;
  needs_retest: number;
  items: ExecutionItem[];
};

export type SourcePlatform = {
  id: string;
  platform_key: string;
  name: string;
  domain: string;
  source_type: string;
  regions: string;
  industry_tags: string;
  base_url: string;
  listing_model: string;
  submission_mode: string;
  has_official_api: boolean;
  risk_level: string;
  status: string;
  notes: string;
  accounts_count: number;
  connectors_count: number;
  compose_url?: string;
  docs_url?: string;
  api_endpoint?: string;
  api_auth_mode?: string;
};

export type SourcePlatformSeed = {
  created: number;
  skipped: number;
  platforms: SourcePlatform[];
};

export type FactPack = {
  id: string;
  name: string;
  legal_name: string;
  brand_names: string;
  website: string;
  product_categories_en: string;
  certifications: string;
  key_specs: string;
  banned_claims: string;
  contact_public: string;
  approved_boilerplate_en: string;
  status: string;
  version: number;
  approved_by: string;
  approved_at: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type ContentAsset = {
  id: string;
  fact_pack_id: string | null;
  fact_pack_name: string;
  asset_type: string;
  title: string;
  body_md: string;
  locale: string;
  keywords: string;
  entities: string;
  status: string;
  ai_review_status: string;
  ai_review: string;
  human_review_note: string;
  approved_by: string;
  approved_at: string | null;
  version: number;
  created_at: string | null;
  updated_at: string | null;
};

export type ContentAssetReview = {
  asset: ContentAsset;
  findings: string[];
};

export type PlatformAccount = {
  id: string;
  platform_id: string;
  platform_name: string;
  label: string;
  login_identifier: string;
  auth_method: string;
  vault_ref: string;
  owner_hint: string;
  scope: string;
  status: string;
  risk_level: string;
  regions_allowed: string;
  notes: string;
  last_verified_at: string | null;
  last_used_at: string | null;
};

export type PlatformConnector = {
  id: string;
  platform_id: string;
  platform_name: string;
  provider_key: string;
  auth_mode: string;
  capabilities: string;
  status: string;
  env_var: string;
  notes: string;
  last_verified_at: string | null;
};

export type GeoChecklistItem = {
  id: string;
  seo_page_id: string;
  item_key: string;
  label: string;
  status: string;
  notes: string | null;
};
