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

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type") && init.body) {
    headers.set("Content-Type", "application/json");
  }
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(path, { ...init, headers });
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
  status: string;
  notes: string | null;
  observed_at: string | null;
};

export type GeoPrompt = {
  id: string;
  prompt_text: string;
  locale: string;
  market_id: string | null;
  seo_page_id: string | null;
  diagnosis: string;
  diagnosis_label: string;
  observations: GeoObservation[];
  cite_rate?: string;
  absorption_rate?: string;
  ai_status?: string;
  evidence?: string;
};

export type GeoTicket = {
  id: string;
  prompt_id: string;
  title: string;
  diagnosis: string;
  diagnosis_label: string;
  rationale: string;
  acceptance_criteria: string;
  status: string;
  verified_note: string | null;
  ai_status?: string;
  ai_review?: string;
  evidence?: string;
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
  needs_js?: boolean;
  html_lang?: string;
  hreflang?: string;
  viewport?: string;
  json_ld_types?: string;
  crawl_error?: string;
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
    error: string;
    verified: number;
    created: number;
  }[];
};

export const crawlStatusLabel: Record<string, string> = {
  untested: "未抓取",
  ok: "已抓取",
  robots_disallow: "robots 禁止",
  timeout: "超时",
  ssl_error: "SSL 失败",
  http_4xx: "HTTP 4xx",
  http_5xx: "HTTP 5xx",
  host_rejected: "主机名拒绝",
  needs_js: "需要 JS",
  error: "抓取失败",
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
  status: string;
  metric_status: string;
  ai_status?: string;
  ai_diagnosis?: string;
  ai_review?: string;
  ai_review_verdict?: string;
  evidence?: string;
};

export type OnsiteBoard = {
  pages: number;
  analyzed_pages: number;
  counts: { critical: number; high: number; low: number };
  groups: { critical: OnsiteIssue[]; high: OnsiteIssue[]; low: OnsiteIssue[] };
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
  competitor_name: string;
  referring_domain: string;
  competitor_url: string | null;
  link_url: string | null;
  kind: string;
  verify_status: string;
  our_presence: string;
  domain_metric: string;
  status: string;
  notes: string | null;
  ai_status?: string;
  ai_review?: string;
  evidence?: string;
  outreach: OutreachItem[];
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
  title: string;
  target_url: string;
  provider_key: string;
  payload_summary: string;
  status: string;
  last_result: string;
  last_detail: string | null;
};

export type GeoChecklistItem = {
  id: string;
  seo_page_id: string;
  item_key: string;
  label: string;
  status: string;
  notes: string | null;
};
