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
