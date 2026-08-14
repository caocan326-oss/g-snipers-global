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
