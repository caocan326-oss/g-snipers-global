import csv
import hashlib
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from io import StringIO
from urllib.parse import quote, urlencode, urljoin, urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.ai_engine import assist_onsite_issue
from app.llm import UNCONFIGURED, configured
from app.models import (
    CrawlSession,
    Competitor,
    DemandSignal,
    DataSyncRun,
    GscConnection,
    GscSyncRun,
    IntegrationSetting,
    IndexNowSubmission,
    Market,
    OnsiteIssue,
    PageSpeedAudit,
    SeoPage,
    SeoPerformanceImport,
    SeoPerformanceRow,
    SerpResult,
    SerpRun,
    SitePage,
    Tenant,
    User,
)
from app.onsite_analyzer import parse_internal_paths, reconcile_issues
from app.onsite_fetch import (
    OriginError,
    allowed_hosts_from_origin,
    apply_observation,
    build_fetch_url,
    fetch_many,
    fetch_site,
    fetch_url,
    load_robots,
    make_client,
    normalize_origin,
    origin_host,
    registered_targets,
)
from app.risk import RISKS, SEVERITIES, default_severity, needs_confirm, require_confirm, severity_to_risk
from app.schemas import (
    AiAssistOut,
    AiStepIn,
    AnalyzeOut,
    ConfirmReadyIn,
    ContentBriefOut,
    CrawlOrSeedOut,
    CrawlSessionOut,
    CrawlSiteIn,
    FetchPageResultOut,
    FetchRegisteredOut,
    OnsiteBoardOut,
    OnsiteDraftIn,
    OnsiteIssueCreate,
    OnsiteIssueOut,
    PageSpeedAuditOut,
    PageSpeedRunIn,
    OnsiteStatusIn,
    GscAuthUrlOut,
    GscConnectIn,
    GscStatusOut,
    GscSyncIn,
    GscSyncOut,
    BingStatusOut,
    DataSyncRunDueIn,
    DataSyncRunDueOut,
    DataSyncRunOut,
    DataSyncStatusOut,
    IntegrationFieldOut,
    IntegrationSettingsIn,
    IntegrationSettingsOut,
    IndexNowStatusOut,
    IndexNowSubmitIn,
    IndexNowSubmitOut,
    SeoReportOut,
    SeoReportTableOut,
    SeoPerformanceBucketOut,
    SeoPerformanceImportIn,
    SeoPerformanceImportOut,
    SeoPerformanceSummaryOut,
    SerpResultOut,
    SerpRunBatchOut,
    SerpRunIn,
    SerpRunOut,
    SerpSummaryOut,
    SiteOriginIn,
    SitePageCreate,
    SitePageDetailOut,
    SitePageOut,
    SitePageUpdate,
    SiteSettingsOut,
)

router = APIRouter(prefix="/api/onsite", tags=["onsite"])

CATEGORIES = {"tdk", "heading", "internal_link", "schema", "index", "crawl", "canonical", "image", "content", "b2b"}
ISSUE_STATUSES = {"open", "drafted", "draft_applied", "confirmed", "verified", "wont_fix"}
OPENISH = {"open", "drafted", "draft_applied", "confirmed"}
BOARD_ACTIONABLE = {"open", "drafted", "draft_applied", "confirmed"}
AI_BATCH_DEFAULT_LIMIT = 5
AI_BATCH_MAX_LIMIT = 10
SEVERITY_RANK = {"critical": 0, "high": 1, "low": 2}
SEVERITY_LABELS = {"critical": "紧急", "high": "重要", "low": "一般"}
CATEGORY_LABELS = {
    "tdk": "标题/描述",
    "heading": "页面标题结构",
    "internal_link": "内链入口",
    "schema": "结构化数据",
    "index": "收录确认",
    "crawl": "抓取访问",
    "canonical": "规范 URL",
    "image": "图片说明",
    "content": "内容质量",
    "b2b": "B2B 转化信息",
}
PAGE_TYPE_LABELS = {
    "home": "首页",
    "product": "产品页",
    "solution": "方案页",
    "case": "案例页",
    "article": "文章页",
    "contact": "联系页",
    "other": "其他页面",
}

INTEGRATION_FIELDS = {
    "gsc_oauth_client_id": ("Google OAuth Client ID", "gsc_oauth_client_id"),
    "gsc_oauth_client_secret": ("Google OAuth Client Secret", "gsc_oauth_client_secret"),
    "gsc_oauth_redirect_uri": ("Google OAuth Redirect URI", "gsc_oauth_redirect_uri"),
    "pagespeed_api_key": ("PageSpeed API Key", "pagespeed_api_key"),
    "brightdata_dataset_api_key": ("Bright Data Dataset API Key", "brightdata_dataset_api_key"),
    "brightdata_serp_dataset_id": ("Bright Data SERP Dataset ID", "brightdata_serp_dataset_id"),
    "brightdata_serp_endpoint": ("Bright Data SERP Endpoint", "brightdata_serp_endpoint"),
}
CRAWL_LABELS = {
    "ok": "可正常访问",
    "http_4xx": "页面不存在或访问失败",
    "http_5xx": "服务器错误",
    "robots_blocked": "robots 阻止抓取",
    "needs_js": "疑似需要浏览器渲染",
    "fetch_error": "抓取失败",
    "untested": "未抓取",
}

PERFORMANCE_SOURCE_LABELS = {"gsc_csv": "Google Search Console CSV", "bing_csv": "Bing Webmaster CSV"}
PAGESPEED_ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
GSC_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GSC_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GSC_SEARCH_ANALYTICS_ENDPOINT = "https://searchconsole.googleapis.com/webmasters/v3/sites/{site_url}/searchAnalytics/query"
GSC_SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"
INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow"
BRIGHTDATA_SERP_INPUT_URL = "https://www.google.com/"

CSV_ALIASES = {
    "query": {"query", "queries", "查询", "搜索查询", "关键词", "关键字"},
    "page_url": {"page", "pages", "url", "landing page", "网页", "页面", "着陆页", "链接"},
    "country": {"country", "countries", "国家/地区", "国家", "地区", "region"},
    "device": {"device", "设备", "终端"},
    "date": {"date", "日期", "day"},
    "clicks": {"clicks", "点击次数", "点击", "click"},
    "impressions": {"impressions", "展示次数", "曝光", "曝光量", "展现"},
    "ctr": {"ctr", "点击率"},
    "position": {"position", "avg. position", "average position", "平均排名", "排名"},
}

CATEGORY_GUIDANCE = {
    "tdk": {
        "impact": "影响搜索结果标题/摘要表达和买家点击判断。",
        "action": "检查页面主题、目标市场和品牌表达，补齐或改写 Title / Description。",
        "retest": "回抓页面后比对 title、description 与处理方案是否一致。",
        "owner": "内容运营 / 客户经理",
    },
    "heading": {
        "impact": "影响页面主题识别、内容层级和用户阅读路径。",
        "action": "补齐 H1 或调整冲突标题，让页面主题和正文结构一致。",
        "retest": "回抓页面后检查 H1 与 headings 是否已更新。",
        "owner": "内容运营 / 网站编辑",
    },
    "internal_link": {
        "impact": "影响核心页面发现、页面权重传递和买家继续浏览路径。",
        "action": "在相关页面加入可抓取的真实 href 内链，并使用清晰锚文本。",
        "retest": "回抓页面后检查目标 URL 是否出现在内链列表。",
        "owner": "内容运营 / 网站编辑",
    },
    "schema": {
        "impact": "影响搜索引擎和 AI 系统理解公司、产品、文章或面包屑信息。",
        "action": "生成 JSON-LD 草案，人工核实公司、产品、认证、价格等事实后上线。",
        "retest": "回抓页面后检查 JSON-LD 类型和语法；关键页再人工用 Rich Results Test 复核。",
        "owner": "技术执行 / 客户网站负责人",
    },
    "index": {
        "impact": "影响是否能确认 Google/Bing 真实索引状态；无授权时只能保持未测。",
        "action": "接入 GSC/Bing 后复核真实索引状态；未授权前不要编造已收录或未收录。",
        "retest": "授权平台数据后复查 URL Inspection 或搜索平台状态。",
        "owner": "客户经理 / 客户授权人",
    },
    "crawl": {
        "impact": "影响系统能否读取页面事实，抓取失败时不能继续判断内容质量。",
        "action": "排查 HTTP 状态、robots、跳转、TLS、超时或 JS 空壳问题。",
        "retest": "修复后重新抓取页面，确认状态码、最终 URL 和正文可读取。",
        "owner": "技术执行 / 客户网站负责人",
    },
    "canonical": {
        "impact": "影响搜索引擎判断规范 URL，错误 canonical 可能让核心页被合并到错误页面。",
        "action": "确认页面规范版本，修正 canonical 指向；高风险项必须人工确认。",
        "retest": "回抓页面后检查 canonical 是否指向预期 URL。",
        "owner": "技术执行 / 客户网站负责人",
    },
    "image": {
        "impact": "影响图片内容理解、图片搜索和无障碍体验。",
        "action": "为关键产品图、认证图、应用图补充准确 alt，无法确认图片内容时人工核对。",
        "retest": "回抓页面后检查图片数量和缺失 alt 数是否下降。",
        "owner": "内容运营 / 网站编辑",
    },
    "content": {
        "impact": "影响买家理解产品价值，也影响搜索和 AI 系统抽取可引用内容。",
        "action": "补充产品参数、应用场景、FAQ、案例、认证或询盘入口，业务事实必须人工确认。",
        "retest": "回抓页面后检查正文可抽取字数、标题结构和关键内容是否已补齐。",
        "owner": "内容运营 / 客户经理",
    },
    "b2b": {
        "impact": "影响海外 B2B 买家判断供应商能力、产品适配度和是否发起询盘。",
        "action": "补齐产品参数、应用行业、认证、案例、MOQ/交期/质保等需确认信息，并强化询盘入口。",
        "retest": "回抓页面后检查正文、内链、CTA 和结构化信息是否覆盖关键 B2B 决策字段。",
        "owner": "客户经理 / 内容运营",
    },
}

B2B_PATH_HINTS = ("product", "products", "solution", "solutions", "application", "applications", "case", "cases", "industry", "industries")


def _url_depth(path: str) -> int:
    return len([part for part in (path or "/").split("/") if part])


def _page_type(page: SitePage) -> str:
    text = f"{page.path} {page.title} {page.meta_title}".lower()
    if (page.path or "/").strip() in {"", "/"}:
        return "home"
    if any(token in text for token in ("product", "products", "sku", "model")):
        return "product"
    if any(token in text for token in ("solution", "application", "industry")):
        return "solution"
    if any(token in text for token in ("case", "project")):
        return "case"
    if any(token in text for token in ("blog", "article", "news")):
        return "article"
    if any(token in text for token in ("contact", "inquiry", "quote")):
        return "contact"
    return "other"


def _priority_hint(page: SitePage) -> str:
    page_type = _page_type(page)
    if page_type in {"home", "product", "solution"}:
        return "P1"
    if page.is_in_sitemap == "yes" or page_type in {"case", "contact"}:
        return "P2"
    return "P3"


def _ai_batch_limit(limit: int | None) -> int:
    if limit is None:
        return AI_BATCH_DEFAULT_LIMIT
    return max(1, min(limit, AI_BATCH_MAX_LIMIT))


def _issue_needs_ai(issue: OnsiteIssue) -> bool:
    return not (issue.proposed_change or "").strip()


def _issue_priority_key(issue: OnsiteIssue) -> tuple[int, int, str]:
    has_draft = 1 if (issue.proposed_change or "").strip() else 0
    created = (issue.created_at or datetime.now(timezone.utc)).isoformat()
    return (has_draft, SEVERITY_RANK.get(issue.severity or "low", 3), created)


def _ai_issue_candidates(db: Session, user: User) -> list[OnsiteIssue]:
    rows = (
        db.query(OnsiteIssue)
        .filter(OnsiteIssue.tenant_id == user.tenant_id, OnsiteIssue.status.in_(["open", "drafted"]))
        .all()
    )
    rows.sort(key=_issue_priority_key)
    return rows


def _issue_out(row: OnsiteIssue, page: SitePage | None = None) -> OnsiteIssueOut:
    p = page or row.page
    guidance = CATEGORY_GUIDANCE.get(
        row.category,
        {
            "impact": "影响页面可被搜索引擎和 AI 系统稳定理解。",
            "action": "结合诊断证据补充处理方案，人工确认后执行。",
            "retest": "执行后重新抓取页面并比对观察层。",
            "owner": "客户经理 / 执行人",
        },
    )
    review_required = needs_confirm(row.severity or "low", row.risk)
    return OnsiteIssueOut(
        id=row.id,
        page_id=row.page_id,
        page_path=p.path if p else "",
        page_title=p.title if p else "",
        category=row.category,
        title=row.title,
        detail=row.detail,
        proposed_change=row.proposed_change,
        severity=row.severity or "low",
        risk=row.risk,
        status=row.status,
        metric_status=row.metric_status,
        ai_status=row.ai_status or "untested",
        ai_diagnosis=row.ai_diagnosis or "",
        ai_review=row.ai_review or "",
        ai_review_verdict=row.ai_review_verdict or "untested",
        evidence=row.evidence or "",
        impact=guidance["impact"],
        recommended_action=guidance["action"],
        review_required=review_required,
        retest_method=guidance["retest"],
        owner_hint=guidance["owner"] if review_required else "内容运营 / 客户经理",
    )


def _owned_issue(db: Session, user: User, issue_id: str) -> OnsiteIssue:
    row = db.get(OnsiteIssue, issue_id)
    if row is None or row.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="任务不存在")
    return row


def _page_out(db: Session, page: SitePage) -> SitePageOut:
    open_count = (
        db.query(func.count(OnsiteIssue.id))
        .filter(OnsiteIssue.page_id == page.id, OnsiteIssue.status.in_(list(OPENISH)))
        .scalar()
        or 0
    )
    return SitePageOut(
        id=page.id,
        path=page.path,
        locale=page.locale,
        title=page.title,
        market_id=page.market_id,
        seo_page_id=page.seo_page_id,
        meta_title=page.meta_title,
        meta_description=page.meta_description,
        meta_keywords=page.meta_keywords,
        headings=page.headings,
        internal_links=page.internal_links,
        structured_data=page.structured_data,
        canonical=page.canonical or "",
        index_status=page.index_status,
        crawl_status=page.crawl_status,
        fetched_at=page.fetched_at,
        final_url=page.final_url or "",
        http_status=page.http_status,
        content_type=page.content_type or "",
        ttfb_ms=page.ttfb_ms,
        redirect_count=page.redirect_count or 0,
        html_bytes=page.html_bytes or 0,
        body_hash=page.body_hash or "",
        needs_js=bool(page.needs_js),
        fetch_mode=page.fetch_mode or "http",
        render_status=page.render_status or "not_needed",
        render_final_url=page.render_final_url or "",
        render_word_count=page.render_word_count or 0,
        html_lang=page.html_lang or "",
        hreflang=page.hreflang or "",
        viewport=page.viewport or "",
        json_ld_types=page.json_ld_types or "",
        crawl_error=page.crawl_error or "",
        discovery_source=page.discovery_source or "manual",
        is_in_sitemap=page.is_in_sitemap or "untested",
        meta_robots=page.meta_robots or "",
        x_robots_tag=page.x_robots_tag or "",
        word_count=page.word_count or 0,
        image_count=page.image_count or 0,
        images_missing_alt=page.images_missing_alt or 0,
        external_link_count=page.external_link_count or 0,
        page_type=_page_type(page),
        url_depth=_url_depth(page.path),
        priority_hint=_priority_hint(page),
        notes=page.notes,
        open_issue_count=open_count,
        analyzed_at=page.analyzed_at,
    )


def _owned_page(db: Session, user: User, page_id: str) -> SitePage:
    page = db.get(SitePage, page_id)
    if page is None or page.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="页面不存在")
    return page


@router.get("/pages", response_model=list[SitePageOut])
def list_pages(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[SitePageOut]:
    pages = db.query(SitePage).filter(SitePage.tenant_id == user.tenant_id).order_by(SitePage.path).all()
    return [_page_out(db, p) for p in pages]


@router.post("/pages", response_model=SitePageOut, status_code=201)
def create_page(
    body: SitePageCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SitePageOut:
    page = SitePage(
        tenant_id=user.tenant_id,
        index_status="untested",
        crawl_status="untested",
        **body.model_dump(),
    )
    db.add(page)
    db.commit()
    db.refresh(page)
    return _page_out(db, page)


@router.get("/pages/{page_id}", response_model=SitePageDetailOut)
def get_page(
    page_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SitePageDetailOut:
    page = (
        db.query(SitePage)
        .options(selectinload(SitePage.issues))
        .filter(SitePage.id == page_id, SitePage.tenant_id == user.tenant_id)
        .first()
    )
    if page is None:
        raise HTTPException(status_code=404, detail="页面不存在")
    base = _page_out(db, page)
    return SitePageDetailOut(
        **base.model_dump(),
        issues=[_issue_out(i, page) for i in page.issues],
    )


@router.patch("/pages/{page_id}", response_model=SitePageOut)
def update_page(
    page_id: str,
    body: SitePageUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SitePageOut:
    page = _owned_page(db, user, page_id)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(page, key, value)
    db.commit()
    db.refresh(page)
    return _page_out(db, page)


@router.get("/board", response_model=OnsiteBoardOut)
def issue_board(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> OnsiteBoardOut:
    pages = db.query(SitePage).filter(SitePage.tenant_id == user.tenant_id).all()
    analyzed = sum(1 for p in pages if p.analyzed_at)
    rows = (
        db.query(OnsiteIssue)
        .options(selectinload(OnsiteIssue.page))
        .filter(OnsiteIssue.tenant_id == user.tenant_id, OnsiteIssue.status.in_(list(BOARD_ACTIONABLE)))
        .all()
    )
    groups: dict[str, list[OnsiteIssueOut]] = {"critical": [], "high": [], "low": []}
    status_counts = {status: 0 for status in ISSUE_STATUSES}
    workflow_counts = {
        "needs_draft": 0,
        "needs_review": 0,
        "ready_to_execute": 0,
        "waiting_retest": 0,
        "verified": 0,
        "wont_fix": 0,
    }
    all_status_rows = db.query(OnsiteIssue).filter(OnsiteIssue.tenant_id == user.tenant_id).all()
    for row in all_status_rows:
        status_counts[row.status] = status_counts.get(row.status, 0) + 1
        if row.status == "open" and not (row.proposed_change or "").strip():
            workflow_counts["needs_draft"] += 1
        if row.status == "drafted":
            workflow_counts["ready_to_execute"] += 1
            if needs_confirm(row.severity or "low", row.risk):
                workflow_counts["needs_review"] += 1
        if row.status in {"draft_applied", "confirmed"}:
            workflow_counts["waiting_retest"] += 1
        if row.status == "verified":
            workflow_counts["verified"] += 1
        if row.status == "wont_fix":
            workflow_counts["wont_fix"] += 1
    for row in rows:
        sev = row.severity if row.severity in groups else "low"
        groups[sev].append(_issue_out(row))
    return OnsiteBoardOut(
        pages=len(pages),
        analyzed_pages=analyzed,
        counts={k: len(v) for k, v in groups.items()},
        status_counts=status_counts,
        workflow_counts=workflow_counts,
        groups=groups,
    )


def _crawl_session_out(row: CrawlSession) -> CrawlSessionOut:
    return CrawlSessionOut(
        id=row.id,
        origin=row.origin,
        mode=row.mode,
        max_urls=row.max_urls,
        max_depth=row.max_depth,
        status=row.status,
        discovered=row.discovered,
        fetched=row.fetched,
        failed=row.failed,
        created=row.created,
        verified=row.verified,
        robots_blocked=row.robots_blocked,
        needs_js=row.needs_js,
        note=row.note,
        started_at=row.started_at,
        finished_at=row.finished_at,
    )


@router.get("/briefs", response_model=list[ContentBriefOut])
def content_briefs(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[ContentBriefOut]:
    pages = db.query(SeoPage).filter(SeoPage.tenant_id == user.tenant_id).order_by(SeoPage.updated_at.desc()).all()
    return [
        ContentBriefOut(
            id=p.id,
            title=p.title,
            target_keyword=p.target_keyword,
            locale=p.locale,
            status=p.status,
            serp_features="未测",
        )
        for p in pages
    ]


def _status_name(status: str) -> str:
    return {
        "open": "待方案",
        "drafted": "待人审/执行",
        "draft_applied": "待复测",
        "confirmed": "已执行待复测",
        "verified": "已解决",
        "wont_fix": "已忽略",
    }.get(status, status)


def _active_issue(issue: OnsiteIssue) -> bool:
    return issue.status not in {"verified", "wont_fix"}


def _severity_label(severity: str) -> str:
    return SEVERITY_LABELS.get(severity, severity or "一般")


def _category_label(category: str) -> str:
    return CATEGORY_LABELS.get(category, category or "其他")


def _page_label(page: SitePage | None) -> str:
    if page is None:
        return "页面未找到"
    label = page.title or page.meta_title or page.path
    return f"{label}（{page.path}）"


def _crawl_label(status: str | None) -> str:
    return CRAWL_LABELS.get(status or "untested", status or "未抓取")


def _sitemap_label(value: str | None) -> str:
    return {"yes": "在 sitemap 中", "no": "不在 sitemap 中", "untested": "未确认"}.get(value or "untested", value or "未确认")


def _issue_impact(issue: OnsiteIssue) -> str:
    return CATEGORY_GUIDANCE.get(issue.category, CATEGORY_GUIDANCE["content"])["impact"]


def _issue_action(issue: OnsiteIssue) -> str:
    if (issue.proposed_change or "").strip():
        return issue.proposed_change or ""
    return CATEGORY_GUIDANCE.get(issue.category, CATEGORY_GUIDANCE["content"])["action"]


def _issue_owner(issue: OnsiteIssue) -> str:
    return CATEGORY_GUIDANCE.get(issue.category, CATEGORY_GUIDANCE["content"])["owner"]


def _issue_retest(issue: OnsiteIssue) -> str:
    return CATEGORY_GUIDANCE.get(issue.category, CATEGORY_GUIDANCE["content"])["retest"]


def _issue_sort_key(issue: OnsiteIssue) -> tuple[int, int, str]:
    status_rank = {"open": 0, "drafted": 1, "confirmed": 2, "draft_applied": 3, "verified": 4, "wont_fix": 5}
    created = (issue.created_at or datetime.now(timezone.utc)).isoformat()
    return (SEVERITY_RANK.get(issue.severity or "low", 3), status_rank.get(issue.status, 9), created)


def _issue_group_rows(issues: list[OnsiteIssue]) -> list[tuple[tuple[str, str, str], int]]:
    counter: Counter[tuple[str, str, str]] = Counter()
    for issue in issues:
        if _active_issue(issue):
            counter[(issue.severity or "low", issue.category or "content", issue.title or "未命名问题")] += 1
    return sorted(counter.items(), key=lambda row: (SEVERITY_RANK.get(row[0][0], 3), -row[1], row[0][2]))


def _diagnosis_targets(db: Session, user: User) -> dict[str, list]:
    markets = (
        db.query(Market)
        .filter(Market.tenant_id == user.tenant_id)
        .order_by(Market.opportunity_score.desc(), Market.created_at.desc())
        .all()
    )
    status_rank = {"priority": 0, "watching": 1, "paused": 2}
    markets.sort(key=lambda m: (status_rank.get(m.status, 9), -(m.opportunity_score or 0), m.name))
    seo_pages = (
        db.query(SeoPage)
        .filter(SeoPage.tenant_id == user.tenant_id)
        .order_by(SeoPage.updated_at.desc())
        .all()
    )
    signals = (
        db.query(DemandSignal)
        .filter(DemandSignal.tenant_id == user.tenant_id)
        .order_by(DemandSignal.intensity.desc(), DemandSignal.created_at.desc())
        .all()
    )
    market_by_id = {m.id: m for m in markets}
    keyword_rows: list[tuple[str, str, str, str]] = []
    seen: set[tuple[str, str]] = set()
    for page in seo_pages:
        key = (page.target_keyword.strip().lower(), page.locale)
        if not page.target_keyword.strip() or key in seen:
            continue
        market = market_by_id.get(page.market_id or "")
        keyword_rows.append((page.target_keyword, page.locale, market.name if market else "未绑定市场", page.status))
        seen.add(key)
    for signal in signals:
        key = (signal.theme.strip().lower(), signal.locale)
        if not signal.theme.strip() or key in seen:
            continue
        market = market_by_id.get(signal.market_id)
        keyword_rows.append((signal.theme, signal.locale, market.name if market else "未绑定市场", f"需求强度 {signal.intensity}"))
        seen.add(key)
    target_markets = [m for m in markets if m.status == "priority"] or markets
    return {
        "markets": target_markets[:8],
        "keywords": keyword_rows[:20],
        "seo_pages": seo_pages,
        "market_by_id": market_by_id,
    }


def _issue_target_market(issue: OnsiteIssue, page: SitePage | None, market_by_id: dict[str, Market]) -> str:
    market_id = page.market_id if page else None
    market = market_by_id.get(market_id or "")
    return f"{market.name}（{market.country_code}）" if market else "未绑定目标国家"


def _issue_target_keyword(issue: OnsiteIssue, page: SitePage | None, seo_by_id: dict[str, SeoPage]) -> str:
    seo = seo_by_id.get((page.seo_page_id if page else "") or "")
    return seo.target_keyword if seo else "未绑定目标关键词"


def _csv_value(row: dict[str, str], field: str) -> str:
    aliases = CSV_ALIASES[field]
    for key, value in row.items():
        normalized = key.strip().lower().lstrip("\ufeff")
        if normalized in aliases:
            return (value or "").strip()
    return ""


def _parse_int(value: str) -> int:
    cleaned = value.replace(",", "").strip()
    if not cleaned:
        return 0
    try:
        return int(float(cleaned))
    except ValueError:
        return 0


def _parse_float(value: str) -> float | None:
    cleaned = value.replace(",", "").replace("%", "").strip()
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _weighted_position(rows: list[SeoPerformanceRow]) -> float | None:
    weighted = 0.0
    total = 0
    for row in rows:
        if row.position is None:
            continue
        weight = row.impressions or 1
        weighted += row.position * weight
        total += weight
    return round(weighted / total, 2) if total else None


def _performance_bucket(key: str, rows: list[SeoPerformanceRow]) -> SeoPerformanceBucketOut:
    clicks = sum(r.clicks for r in rows)
    impressions = sum(r.impressions for r in rows)
    ctr = round(clicks / impressions * 100, 2) if impressions else None
    return SeoPerformanceBucketOut(
        key=key or "未标注",
        clicks=clicks,
        impressions=impressions,
        ctr=ctr,
        position=_weighted_position(rows),
    )


def _top_buckets(rows: list[SeoPerformanceRow], attr: str, limit: int = 8) -> list[SeoPerformanceBucketOut]:
    grouped: dict[str, list[SeoPerformanceRow]] = defaultdict(list)
    for row in rows:
        grouped[getattr(row, attr) or "未标注"].append(row)
    buckets = [_performance_bucket(key, values) for key, values in grouped.items()]
    return sorted(buckets, key=lambda item: (item.impressions, item.clicks), reverse=True)[:limit]


def _latest_speed_audits(db: Session, tenant_id: str, limit: int = 8) -> list[PageSpeedAudit]:
    return (
        db.query(PageSpeedAudit)
        .filter(PageSpeedAudit.tenant_id == tenant_id)
        .order_by(PageSpeedAudit.audited_at.desc())
        .limit(limit)
        .all()
    )


def _performance_summary(db: Session, user: User) -> SeoPerformanceSummaryOut:
    rows = db.query(SeoPerformanceRow).filter(SeoPerformanceRow.tenant_id == user.tenant_id).all()
    imports = (
        db.query(SeoPerformanceImport)
        .filter(SeoPerformanceImport.tenant_id == user.tenant_id)
        .order_by(SeoPerformanceImport.imported_at.desc())
        .limit(10)
        .all()
    )
    speed = _latest_speed_audits(db, user.tenant_id)
    gsc_rows = [row for row in rows if row.source in {"gsc_csv", "gsc_api"}]
    bing_rows = [row for row in rows if row.source == "bing_csv"]
    total_clicks = sum(row.clicks for row in rows)
    total_impressions = sum(row.impressions for row in rows)
    return SeoPerformanceSummaryOut(
        gsc_status="已导入" if gsc_rows else "未导入",
        bing_status="已导入" if bing_rows else "未导入",
        pagespeed_status="已测速" if speed else "未测速",
        total_clicks=total_clicks,
        total_impressions=total_impressions,
        avg_ctr=round(total_clicks / total_impressions * 100, 2) if total_impressions else None,
        avg_position=_weighted_position(rows),
        by_country=_top_buckets(rows, "country"),
        by_query=_top_buckets(rows, "query"),
        by_page=_top_buckets(rows, "page_url"),
        speed_latest=[PageSpeedAuditOut(**audit.__dict__) for audit in speed],
        imports=[SeoPerformanceImportOut(**item.__dict__) for item in imports],
        serp=_serp_summary(db, user),
    )


def _serp_configured(db: Session, tenant_id: str) -> bool:
    return bool(
        _integration_value(db, tenant_id, "brightdata_dataset_api_key")
        and _integration_value(db, tenant_id, "brightdata_serp_dataset_id")
    )


def _domain(url: str) -> str:
    host = (urlparse(url if "://" in url else f"https://{url}").hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def _same_or_subdomain(domain: str, root: str) -> bool:
    d = _domain(domain)
    r = _domain(root)
    return bool(d and r and (d == r or d.endswith("." + r)))


def _competitor_domains(db: Session, tenant_id: str) -> set[str]:
    rows = db.query(Competitor).filter(Competitor.tenant_id == tenant_id).all()
    domains = {_domain(row.website or "") for row in rows if row.website}
    return {item for item in domains if item}


def _ownership(url: str, own_domain: str, competitors: set[str]) -> str:
    domain = _domain(url)
    if own_domain and _same_or_subdomain(domain, own_domain):
        return "owned"
    if any(_same_or_subdomain(domain, comp) for comp in competitors):
        return "competitor"
    return "third_party"


def _extract_organic_results(data: object, limit: int) -> list[dict[str, str | int]]:
    rows: list[dict[str, str | int]] = []

    def candidates_from(node: object) -> list[object]:
        if isinstance(node, list):
            return node
        if not isinstance(node, dict):
            return []
        candidates = (
            node.get("organic")
            or node.get("organic_results")
            or node.get("organic_results_100")
            or node.get("results")
            or node.get("items")
            or []
        )
        if isinstance(candidates, dict):
            candidates = candidates.get("items") or candidates.get("results") or []
        return candidates if isinstance(candidates, list) else []

    top_level = data if isinstance(data, list) else [data]
    candidates: list[object] = []
    for item in top_level:
        if isinstance(item, dict):
            candidates.extend(candidates_from(item))
            if isinstance(item.get("result"), (dict, list)):
                candidates.extend(candidates_from(item.get("result")))
            if isinstance(item.get("data"), (dict, list)):
                candidates.extend(candidates_from(item.get("data")))
        else:
            candidates.extend(candidates_from(item))

    if not isinstance(candidates, list):
        return rows
    for idx, item in enumerate(candidates, start=1):
        if not isinstance(item, dict):
            continue
        url = str(item.get("link") or item.get("url") or item.get("href") or item.get("displayed_link") or "").strip()
        if not url:
            continue
        position_raw = item.get("position") or item.get("rank") or idx
        try:
            position = int(position_raw)
        except (TypeError, ValueError):
            position = idx
        rows.append(
            {
                "position": position,
                "title": str(item.get("title") or "").strip(),
                "url": url,
                "snippet": str(item.get("snippet") or item.get("description") or item.get("text") or "").strip(),
                "result_type": str(item.get("type") or "organic").strip() or "organic",
            }
        )
        if len(rows) >= limit:
            break
    return rows


def _fetch_brightdata_serp(
    db: Session,
    tenant_id: str,
    keyword: str,
    *,
    country: str,
    locale: str,
    device: str,
    limit: int,
) -> list[dict[str, str | int]]:
    language = locale.split("-", 1)[0].lower() if locale else ""
    payload = {
        "input": [
            {
                "url": BRIGHTDATA_SERP_INPUT_URL,
                "keyword": keyword,
                "language": language,
                "uule": "",
                "brd_mobile": "1" if device == "mobile" else "",
                "tbs": "",
                "tbm": "",
                "nfpr": "",
                "index": "",
            }
        ],
        "limit_per_input": limit,
    }
    params = {
        "dataset_id": _integration_value(db, tenant_id, "brightdata_serp_dataset_id"),
        "notify": "false",
        "include_errors": "true",
    }
    headers = {
        "Authorization": f"Bearer {_integration_value(db, tenant_id, 'brightdata_dataset_api_key')}",
        "Content-Type": "application/json",
    }
    endpoint = _integration_value(db, tenant_id, "brightdata_serp_endpoint") or "https://api.brightdata.com/datasets/v3/scrape"
    with httpx.Client(timeout=90, headers=headers) as client:
        response = client.post(endpoint, params=params, json=payload)
        response.raise_for_status()
        data = response.json()
    return _extract_organic_results(data, limit)


def _serp_run_out(run: SerpRun, results: list[SerpResult] | None = None) -> SerpRunOut:
    return SerpRunOut(
        id=run.id,
        provider=run.provider,
        keyword=run.keyword,
        country=run.country,
        locale=run.locale,
        device=run.device,
        status=run.status,
        own_domain=run.own_domain,
        own_best_position=run.own_best_position,
        competitor_best_position=run.competitor_best_position,
        result_count=run.result_count,
        third_party_count=run.third_party_count,
        error=run.error,
        created_at=run.created_at,
        results=[SerpResultOut(**item.__dict__) for item in (results or [])],
    )


def _serp_summary(db: Session, user: User) -> SerpSummaryOut:
    runs = (
        db.query(SerpRun)
        .filter(SerpRun.tenant_id == user.tenant_id)
        .order_by(SerpRun.created_at.desc())
        .limit(20)
        .all()
    )
    latest = runs[:6]
    ok_runs = [row for row in runs if row.status == "ok"]
    own_positions = [row.own_best_position for row in ok_runs if row.own_best_position is not None]
    third_party_rows = (
        db.query(SerpResult.domain, func.count(SerpResult.id))
        .filter(SerpResult.tenant_id == user.tenant_id, SerpResult.ownership == "third_party")
        .group_by(SerpResult.domain)
        .order_by(func.count(SerpResult.id).desc())
        .limit(8)
        .all()
    )
    return SerpSummaryOut(
        configured=_serp_configured(db, user.tenant_id),
        status="已配置" if _serp_configured(db, user.tenant_id) else "未配置",
        total_runs=len(runs),
        own_visible_runs=sum(1 for row in ok_runs if row.own_best_position is not None),
        competitor_visible_runs=sum(1 for row in ok_runs if row.competitor_best_position is not None),
        avg_own_position=round(sum(own_positions) / len(own_positions), 2) if own_positions else None,
        latest_runs=[_serp_run_out(row) for row in latest],
        top_third_party_domains=[{"domain": domain or "未知域名", "count": int(count)} for domain, count in third_party_rows],
    )


def _target_serp_keywords(db: Session, user: User, requested: list[str], limit: int) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in requested:
        text = raw.strip()
        if text and text.lower() not in seen:
            seen.add(text.lower())
            out.append(text)
    if not out:
        signals = (
            db.query(DemandSignal)
            .filter(DemandSignal.tenant_id == user.tenant_id)
            .order_by(DemandSignal.intensity.desc(), DemandSignal.created_at.desc())
            .limit(limit)
            .all()
        )
        for row in signals:
            text = (row.theme or "").strip()
            if text and text.lower() not in seen:
                seen.add(text.lower())
                out.append(text)
    if not out:
        seo_pages = (
            db.query(SeoPage)
            .filter(SeoPage.tenant_id == user.tenant_id)
            .order_by(SeoPage.updated_at.desc())
            .limit(limit)
            .all()
        )
        for row in seo_pages:
            text = (row.target_keyword or "").strip()
            if text and text.lower() not in seen:
                seen.add(text.lower())
                out.append(text)
    return out[:limit]


def _run_one_serp(db: Session, user: User, keyword: str, *, country: str, locale: str, device: str, limit: int) -> SerpRun:
    tenant = _tenant(db, user)
    own_domain = _domain(tenant.site_origin or "")
    competitors = _competitor_domains(db, user.tenant_id)
    config_hash = hashlib.sha256(f"brightdata|{keyword}|{country}|{locale}|{device}|{limit}|{own_domain}|{','.join(sorted(competitors))}".encode()).hexdigest()
    run = SerpRun(
        tenant_id=user.tenant_id,
        provider="brightdata",
        keyword=keyword,
        country=country,
        locale=locale,
        device=device,
        status="running",
        own_domain=own_domain,
        config_hash=config_hash,
        created_by=user.id,
    )
    db.add(run)
    db.flush()
    try:
        rows = _fetch_brightdata_serp(db, user.tenant_id, keyword, country=country, locale=locale, device=device, limit=limit)
        own_positions: list[int] = []
        competitor_positions: list[int] = []
        third_party_count = 0
        for item in rows:
            url = str(item["url"])
            ownership = _ownership(url, own_domain, competitors)
            position = int(item["position"])
            if ownership == "owned":
                own_positions.append(position)
            elif ownership == "competitor":
                competitor_positions.append(position)
            else:
                third_party_count += 1
            db.add(
                SerpResult(
                    tenant_id=user.tenant_id,
                    run_id=run.id,
                    position=position,
                    title=str(item["title"])[:500],
                    url=url[:1000],
                    domain=_domain(url)[:255],
                    snippet=str(item["snippet"]),
                    result_type=str(item["result_type"])[:40],
                    ownership=ownership,
                )
            )
        run.status = "ok"
        run.result_count = len(rows)
        run.third_party_count = third_party_count
        run.own_best_position = min(own_positions) if own_positions else None
        run.competitor_best_position = min(competitor_positions) if competitor_positions else None
    except Exception as exc:
        run.status = "error"
        run.error = f"Bright Data SERP 查询失败：{exc}"[:1000]
    return run


def _page_performance(rows: list[SeoPerformanceRow], page: SitePage | None) -> SeoPerformanceBucketOut | None:
    if not page:
        return None
    path = page.path or "/"
    matched = []
    for row in rows:
        parsed = urlparse(row.page_url)
        candidate_path = parsed.path if parsed.scheme else row.page_url
        if candidate_path == path or row.page_url.endswith(path):
            matched.append(row)
    return _performance_bucket(path, matched) if matched else None


def _score_text(score: int | None) -> str:
    return str(score) if score is not None else "未得分"


def _pagespeed_targets(tenant: Tenant, pages: list[SitePage], requested: list[str], limit: int) -> list[str]:
    origin = normalize_origin(tenant.site_origin or "")
    seen: set[str] = set()
    urls: list[str] = []
    for raw in requested:
        candidate = raw.strip()
        if not candidate:
            continue
        url = candidate if urlparse(candidate).scheme else urljoin(origin, candidate)
        if url not in seen:
            urls.append(url)
            seen.add(url)
    if not urls:
        for path in ["/"] + [page.path for page in pages]:
            url = urljoin(origin, path)
            if url not in seen:
                urls.append(url)
                seen.add(url)
            if len(urls) >= limit:
                break
    return urls[:limit]


def _extract_pagespeed_score(category: dict) -> int | None:
    score = category.get("score")
    if score is None:
        return None
    try:
        return int(round(float(score) * 100))
    except (TypeError, ValueError):
        return None


def _audit_numeric(audits: dict, key: str) -> int | None:
    value = (audits.get(key) or {}).get("numericValue")
    if value is None:
        return None
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def _run_pagespeed(db: Session, tenant_id: str, url: str, strategy: str) -> dict:
    params = {"url": url, "strategy": strategy, "category": ["performance", "seo", "accessibility", "best-practices"]}
    pagespeed_key = _integration_value(db, tenant_id, "pagespeed_api_key")
    if pagespeed_key:
        params["key"] = pagespeed_key
    with httpx.Client(timeout=45) as client:
        response = client.get(PAGESPEED_ENDPOINT, params=params)
        response.raise_for_status()
        data = response.json()
    lighthouse = data.get("lighthouseResult") or {}
    categories = lighthouse.get("categories") or {}
    audits = lighthouse.get("audits") or {}
    return {
        "performance_score": _extract_pagespeed_score(categories.get("performance") or {}),
        "seo_score": _extract_pagespeed_score(categories.get("seo") or {}),
        "accessibility_score": _extract_pagespeed_score(categories.get("accessibility") or {}),
        "best_practices_score": _extract_pagespeed_score(categories.get("best-practices") or {}),
        "lcp_ms": _audit_numeric(audits, "largest-contentful-paint"),
        "inp_ms": _audit_numeric(audits, "interaction-to-next-paint") or _audit_numeric(audits, "max-potential-fid"),
        "cls": _parse_float(str((audits.get("cumulative-layout-shift") or {}).get("numericValue", ""))),
        "detail": "PageSpeed Insights 在线测速完成。",
    }


def _gsc_redirect_uri(db: Session, tenant_id: str) -> str:
    return _integration_value(db, tenant_id, "gsc_oauth_redirect_uri") or f"{settings.frontend_origin.rstrip('/')}/onsite"


def _gsc_configured(db: Session, tenant_id: str) -> bool:
    return bool(
        _integration_value(db, tenant_id, "gsc_oauth_client_id")
        and _integration_value(db, tenant_id, "gsc_oauth_client_secret")
    )


def _gsc_connection(db: Session, tenant_id: str) -> GscConnection | None:
    return db.query(GscConnection).filter(GscConnection.tenant_id == tenant_id).first()


def _gsc_status(db: Session, user: User) -> GscStatusOut:
    conn = _gsc_connection(db, user.tenant_id)
    configured = _gsc_configured(db, user.tenant_id)
    connected = bool(conn and conn.status == "connected" and conn.refresh_token)
    note = "已连接，可同步 Google Search Console 数据。" if connected else "需要客户授权 Google Search Console。"
    if not configured:
        note = "服务器未配置 GSC OAuth Client ID / Secret。"
    return GscStatusOut(
        configured=configured,
        connected=connected,
        status=conn.status if conn else "disconnected",
        site_url=conn.site_url if conn else "",
        last_sync_at=conn.last_sync_at if conn else None,
        last_error=conn.last_error if conn else "",
        redirect_uri=_gsc_redirect_uri(db, user.tenant_id),
        note=note,
    )


def _gsc_site_url(tenant: Tenant, raw: str) -> str:
    text = (raw or "").strip() or tenant.site_origin or ""
    if not text:
        raise HTTPException(status_code=400, detail="请先设置客户官网或填写 GSC property URL。")
    if text.startswith("sc-domain:"):
        return text
    origin = normalize_origin(text)
    return origin.rstrip("/") + "/"


def _exchange_gsc_code(db: Session, user: User, code: str) -> dict:
    with httpx.Client(timeout=30) as client:
        response = client.post(
            GSC_TOKEN_ENDPOINT,
            data={
                "code": code,
                "client_id": _integration_value(db, user.tenant_id, "gsc_oauth_client_id"),
                "client_secret": _integration_value(db, user.tenant_id, "gsc_oauth_client_secret"),
                "redirect_uri": _gsc_redirect_uri(db, user.tenant_id),
                "grant_type": "authorization_code",
            },
        )
        if response.status_code >= 400:
            raise HTTPException(status_code=400, detail=f"GSC 授权失败：{response.text[:500]}")
        return response.json()


def _refresh_gsc_token(db: Session, conn: GscConnection) -> str:
    if conn.access_token and conn.token_expires_at and conn.token_expires_at > datetime.now(timezone.utc) + timedelta(minutes=5):
        return conn.access_token
    if not conn.refresh_token:
        raise HTTPException(status_code=400, detail="GSC refresh token 缺失，请重新授权。")
    with httpx.Client(timeout=30) as client:
        response = client.post(
            GSC_TOKEN_ENDPOINT,
            data={
                "client_id": _integration_value(db, conn.tenant_id, "gsc_oauth_client_id"),
                "client_secret": _integration_value(db, conn.tenant_id, "gsc_oauth_client_secret"),
                "refresh_token": conn.refresh_token,
                "grant_type": "refresh_token",
            },
        )
        if response.status_code >= 400:
            conn.status = "error"
            conn.last_error = response.text[:1000]
            raise HTTPException(status_code=400, detail=f"GSC token 刷新失败：{response.text[:500]}")
        data = response.json()
    conn.access_token = data.get("access_token", "")
    expires_in = int(data.get("expires_in") or 3600)
    conn.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    conn.status = "connected"
    conn.last_error = ""
    return conn.access_token


def _gsc_date_range(days: int) -> tuple[str, str]:
    end = datetime.now(timezone.utc).date() - timedelta(days=2)
    start = end - timedelta(days=days - 1)
    return start.isoformat(), end.isoformat()


def _finish_data_sync(
    db: Session,
    user: User,
    *,
    source: str,
    mode: str,
    status: str,
    rows_imported: int = 0,
    submitted: int = 0,
    note: str = "",
) -> DataSyncRun:
    row = DataSyncRun(
        tenant_id=user.tenant_id,
        source=source,
        mode=mode,
        status=status,
        rows_imported=rows_imported,
        submitted=submitted,
        note=note,
        finished_at=datetime.now(timezone.utc),
    )
    db.add(row)
    return row


def _integration_rows(db: Session | None, tenant_id: str) -> dict[str, IntegrationSetting]:
    if db is None:
        return {}
    rows = db.query(IntegrationSetting).filter(IntegrationSetting.tenant_id == tenant_id).all()
    return {row.key: row for row in rows}


def _integration_value(db: Session | None, tenant_id: str, key: str) -> str:
    if key not in INTEGRATION_FIELDS:
        return ""
    row = _integration_rows(db, tenant_id).get(key)
    if row and row.value.strip():
        return row.value.strip()
    fallback = getattr(settings, INTEGRATION_FIELDS[key][1], "")
    return (fallback or "").strip()


def _integration_source(db: Session | None, tenant_id: str, key: str) -> str:
    row = _integration_rows(db, tenant_id).get(key)
    if row and row.value.strip():
        return "database"
    if (getattr(settings, INTEGRATION_FIELDS[key][1], "") or "").strip():
        return "env"
    return "none"


def _mask_secret(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    if len(text) <= 8:
        return "*" * len(text)
    return f"{text[:4]}...{text[-4:]}"


def _integration_settings_out(db: Session, tenant_id: str) -> IntegrationSettingsOut:
    fields = [
        IntegrationFieldOut(
            key=key,
            label=label,
            configured=bool(_integration_value(db, tenant_id, key)),
            masked_value=_mask_secret(_integration_value(db, tenant_id, key)),
            source=_integration_source(db, tenant_id, key),
        )
        for key, (label, _setting_attr) in INTEGRATION_FIELDS.items()
    ]
    return IntegrationSettingsOut(
        fields=fields,
        gsc_configured=bool(
            _integration_value(db, tenant_id, "gsc_oauth_client_id")
            and _integration_value(db, tenant_id, "gsc_oauth_client_secret")
        ),
        pagespeed_configured=bool(_integration_value(db, tenant_id, "pagespeed_api_key")),
        brightdata_serp_configured=bool(
            _integration_value(db, tenant_id, "brightdata_dataset_api_key")
            and _integration_value(db, tenant_id, "brightdata_serp_dataset_id")
        ),
    )


def _gsc_sync_due(conn: GscConnection) -> bool:
    if not conn.last_sync_at:
        return True
    last_sync = conn.last_sync_at
    if last_sync.tzinfo is None:
        last_sync = last_sync.replace(tzinfo=timezone.utc)
    interval = max(1, settings.gsc_auto_sync_min_interval_hours)
    return last_sync <= datetime.now(timezone.utc) - timedelta(hours=interval)


def _sync_gsc_rows(db: Session, user: User, conn: GscConnection, body: GscSyncIn, *, mode: str = "manual") -> GscSyncOut:
    token = _refresh_gsc_token(db, conn)
    date_start, date_end = _gsc_date_range(body.days)
    run = GscSyncRun(
        tenant_id=user.tenant_id,
        connection_id=conn.id,
        status="running",
        date_start=date_start,
        date_end=date_end,
        note="GSC Search Analytics 同步中。",
    )
    db.add(run)
    db.flush()
    url = GSC_SEARCH_ANALYTICS_ENDPOINT.format(site_url=quote(conn.site_url, safe=""))
    payload = {
        "startDate": date_start,
        "endDate": date_end,
        "dimensions": ["date", "query", "page", "country", "device"],
        "rowLimit": body.row_limit,
    }
    try:
        with httpx.Client(timeout=60) as client:
            response = client.post(url, headers={"Authorization": f"Bearer {token}"}, json=payload)
        if response.status_code >= 400:
            raise HTTPException(status_code=400, detail=f"GSC 同步失败：{response.text[:500]}")
        data = response.json()
        imported = SeoPerformanceImport(
            tenant_id=user.tenant_id,
            source="gsc_api",
            filename=f"GSC API {date_start}~{date_end}",
            imported_by=user.id,
            note=f"Google Search Console API 自动同步，property={conn.site_url}",
        )
        db.add(imported)
        db.flush()
        count = 0
        for row in data.get("rows") or []:
            keys = row.get("keys") or []
            if len(keys) < 5:
                continue
            impressions = _parse_int(str(row.get("impressions", "")))
            clicks = _parse_int(str(row.get("clicks", "")))
            db.add(
                SeoPerformanceRow(
                    tenant_id=user.tenant_id,
                    import_id=imported.id,
                    source="gsc_api",
                    date=str(keys[0]),
                    query=str(keys[1]),
                    page_url=str(keys[2]),
                    country=str(keys[3]),
                    device=str(keys[4]),
                    clicks=clicks,
                    impressions=impressions,
                    ctr=round(float(row.get("ctr") or 0) * 100, 4),
                    position=round(float(row.get("position") or 0), 2) if row.get("position") is not None else None,
                )
            )
            count += 1
        imported.rows_imported = count
        run.status = "ok"
        run.rows_imported = count
        run.note = "GSC Search Analytics 同步完成。"
        run.finished_at = datetime.now(timezone.utc)
        conn.status = "connected"
        conn.last_sync_at = run.finished_at
        conn.last_error = ""
        _finish_data_sync(
            db,
            user,
            source="gsc",
            mode=mode,
            status="ok",
            rows_imported=count,
            note=f"GSC Search Analytics {date_start}~{date_end}",
        )
        db.commit()
        return GscSyncOut(status="ok", rows_imported=count, date_start=date_start, date_end=date_end, note=run.note)
    except HTTPException as exc:
        run.status = "error"
        run.note = str(exc.detail)
        run.finished_at = datetime.now(timezone.utc)
        conn.status = "error"
        conn.last_error = str(exc.detail)
        _finish_data_sync(db, user, source="gsc", mode=mode, status="error", note=str(exc.detail))
        db.commit()
        raise


def _indexnow_key_location(tenant: Tenant) -> str:
    if settings.indexnow_key_location:
        return settings.indexnow_key_location
    origin = normalize_origin(tenant.site_origin or "")
    return f"{origin.rstrip('/')}/{settings.indexnow_key}.txt" if settings.indexnow_key else ""


def _indexnow_urls(tenant: Tenant, body: IndexNowSubmitIn) -> list[str]:
    origin = normalize_origin(tenant.site_origin or "")
    seen: set[str] = set()
    urls: list[str] = []
    for raw in [*body.urls, *body.paths]:
        item = raw.strip()
        if not item:
            continue
        url = item if urlparse(item).scheme else build_fetch_url(origin, item)
        if urlparse(url).hostname != urlparse(origin).hostname:
            continue
        if url not in seen:
            urls.append(url)
            seen.add(url)
    return urls[:10000]


@router.get("/performance", response_model=SeoPerformanceSummaryOut)
def seo_performance(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> SeoPerformanceSummaryOut:
    return _performance_summary(db, user)


@router.get("/serp/status", response_model=SerpSummaryOut)
def serp_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> SerpSummaryOut:
    return _serp_summary(db, user)


@router.get("/integrations", response_model=IntegrationSettingsOut)
def get_integration_settings(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> IntegrationSettingsOut:
    return _integration_settings_out(db, user.tenant_id)


@router.patch("/integrations", response_model=IntegrationSettingsOut)
def update_integration_settings(
    body: IntegrationSettingsIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IntegrationSettingsOut:
    existing = _integration_rows(db, user.tenant_id)
    for key in body.clear_keys:
        if key not in INTEGRATION_FIELDS:
            continue
        row = existing.get(key)
        if row:
            db.delete(row)

    values = body.model_dump(exclude={"clear_keys"}, exclude_none=True)
    for key, raw in values.items():
        if key not in INTEGRATION_FIELDS:
            continue
        value = str(raw or "").strip()
        if not value:
            continue
        row = existing.get(key)
        if row is None:
            row = IntegrationSetting(tenant_id=user.tenant_id, key=key)
            db.add(row)
        row.value = value
        row.updated_by = user.id

    db.commit()
    return _integration_settings_out(db, user.tenant_id)


@router.post("/serp/run", response_model=SerpRunBatchOut)
def run_serp(
    body: SerpRunIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SerpRunBatchOut:
    if not _serp_configured(db, user.tenant_id):
        return SerpRunBatchOut(
            status="未配置",
            configured=False,
            note="服务器未配置 Bright Data Dataset SERP API。请配置 BRIGHTDATA_DATASET_API_KEY / BRIGHTDATA_SERP_DATASET_ID。",
        )
    keywords = _target_serp_keywords(db, user, body.keywords, limit=min(5, body.limit))
    if not keywords:
        raise HTTPException(status_code=400, detail="没有可查询的关键词。请先在首页配置客户 SEO 目标关键词。")
    runs: list[SerpRun] = []
    for keyword in keywords:
        runs.append(_run_one_serp(db, user, keyword, country=body.country, locale=body.locale, device=body.device, limit=body.limit))
    failed = sum(1 for row in runs if row.status == "error")
    _finish_data_sync(
        db,
        user,
        source="serp",
        mode="manual",
        status="error" if failed == len(runs) else "ok",
        rows_imported=sum(row.result_count for row in runs),
        note=f"Bright Data SERP 查询 {len(runs)} 个关键词，失败 {failed} 个。",
    )
    db.commit()
    for row in runs:
        db.refresh(row)
    return SerpRunBatchOut(
        status="ok" if failed == 0 else "partial",
        configured=True,
        ran=len(runs),
        failed=failed,
        note=f"SERP 查询完成：关键词 {len(runs)} 个，失败 {failed} 个。",
        runs=[_serp_run_out(row) for row in runs],
    )


@router.get("/gsc/status", response_model=GscStatusOut)
def gsc_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> GscStatusOut:
    return _gsc_status(db, user)


@router.get("/gsc/auth-url", response_model=GscAuthUrlOut)
def gsc_auth_url(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> GscAuthUrlOut:
    if not _gsc_configured(db, user.tenant_id):
        return GscAuthUrlOut(configured=False, redirect_uri=_gsc_redirect_uri(db, user.tenant_id), note="服务器未配置 GSC OAuth Client ID / Secret。")
    params = {
        "client_id": _integration_value(db, user.tenant_id, "gsc_oauth_client_id"),
        "redirect_uri": _gsc_redirect_uri(db, user.tenant_id),
        "response_type": "code",
        "scope": GSC_SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": user.tenant_id,
    }
    return GscAuthUrlOut(
        configured=True,
        auth_url=f"{GSC_AUTH_ENDPOINT}?{urlencode(params)}",
        redirect_uri=_gsc_redirect_uri(db, user.tenant_id),
        note="打开授权链接后，Google 会回到诊断页并带上 code。",
    )


@router.post("/gsc/connect", response_model=GscStatusOut)
def gsc_connect(
    body: GscConnectIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GscStatusOut:
    if not _gsc_configured(db, user.tenant_id):
        raise HTTPException(status_code=400, detail="服务器未配置 GSC OAuth Client ID / Secret。")
    tenant = _tenant(db, user)
    data = _exchange_gsc_code(db, user, body.code)
    conn = _gsc_connection(db, user.tenant_id)
    if conn is None:
        conn = GscConnection(tenant_id=user.tenant_id)
        db.add(conn)
    conn.site_url = _gsc_site_url(tenant, body.site_url)
    conn.status = "connected"
    conn.access_token = data.get("access_token", "")
    if data.get("refresh_token"):
        conn.refresh_token = data.get("refresh_token", "")
    conn.scopes = data.get("scope", GSC_SCOPE)
    expires_in = int(data.get("expires_in") or 3600)
    conn.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    conn.connected_by = user.id
    conn.last_error = ""
    db.commit()
    return _gsc_status(db, user)


@router.post("/gsc/sync", response_model=GscSyncOut)
def gsc_sync(
    body: GscSyncIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GscSyncOut:
    if not _gsc_configured(db, user.tenant_id):
        raise HTTPException(status_code=400, detail="服务器未配置 GSC OAuth Client ID / Secret。")
    conn = _gsc_connection(db, user.tenant_id)
    if conn is None or not conn.refresh_token:
        raise HTTPException(status_code=400, detail="尚未连接 Google Search Console。")
    return _sync_gsc_rows(db, user, conn, body)


@router.get("/data-sync/status", response_model=DataSyncStatusOut)
def data_sync_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> DataSyncStatusOut:
    rows = (
        db.query(DataSyncRun)
        .filter(DataSyncRun.tenant_id == user.tenant_id)
        .order_by(DataSyncRun.started_at.desc())
        .limit(12)
        .all()
    )
    return DataSyncStatusOut(runs=[DataSyncRunOut(**row.__dict__) for row in rows])


@router.post("/data-sync/run-due", response_model=DataSyncRunDueOut)
def data_sync_run_due(
    body: DataSyncRunDueIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DataSyncRunDueOut:
    requested = set(body.sources or ["gsc"])
    if "gsc" not in requested:
        return DataSyncRunDueOut(status="skipped", skipped=1, note="本次没有请求可自动同步的数据源。")
    if not _gsc_configured(db, user.tenant_id):
        return DataSyncRunDueOut(status="skipped", skipped=1, note="GSC OAuth 未配置，无法执行自动同步。")
    conn = _gsc_connection(db, user.tenant_id)
    if conn is None or not conn.refresh_token:
        return DataSyncRunDueOut(status="skipped", skipped=1, note="尚未连接 Google Search Console。")
    if not body.force and not _gsc_sync_due(conn):
        return DataSyncRunDueOut(status="skipped", skipped=1, note="GSC 最近已同步，未达到自动同步间隔。")

    days = max(1, min(180, settings.gsc_auto_sync_days))
    result = _sync_gsc_rows(db, user, conn, GscSyncIn(days=days, row_limit=25000), mode="manual" if body.force else "scheduled")
    latest = (
        db.query(DataSyncRun)
        .filter(DataSyncRun.tenant_id == user.tenant_id, DataSyncRun.source == "gsc")
        .order_by(DataSyncRun.started_at.desc())
        .limit(1)
        .all()
    )
    return DataSyncRunDueOut(
        status="ok",
        ran=1,
        runs=[DataSyncRunOut(**row.__dict__) for row in latest],
        note=f"{result.note} {result.date_start} 至 {result.date_end}，导入 {result.rows_imported} 行。",
    )


@router.get("/bing/status", response_model=BingStatusOut)
def bing_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> BingStatusOut:
    configured = bool(settings.bing_webmaster_api_key)
    return BingStatusOut(
        configured=configured,
        status="configured" if configured else "unconfigured",
        note="Bing Webmaster API Key 已配置；下一步可接入具体站点数据同步。" if configured else "服务器未配置 Bing Webmaster API Key。本阶段不编造 Bing 数据。",
    )


@router.get("/indexnow/status", response_model=IndexNowStatusOut)
def indexnow_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> IndexNowStatusOut:
    tenant = _tenant(db, user)
    last = (
        db.query(IndexNowSubmission)
        .filter(IndexNowSubmission.tenant_id == user.tenant_id)
        .order_by(IndexNowSubmission.submitted_at.desc())
        .first()
    )
    host = origin_host(normalize_origin(tenant.site_origin)) if tenant.site_origin else ""
    configured = bool(settings.indexnow_key and tenant.site_origin)
    return IndexNowStatusOut(
        configured=configured,
        host=host,
        key_location=_indexnow_key_location(tenant) if configured else "",
        last_submitted_at=last.submitted_at if last else None,
        last_status=last.status if last else "",
        note="IndexNow 可提交 URL 更新通知；不保证抓取、收录或排名。" if configured else "请先配置 INDEXNOW_KEY 并设置客户官网。",
    )


@router.post("/indexnow/submit", response_model=IndexNowSubmitOut)
def indexnow_submit(
    body: IndexNowSubmitIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IndexNowSubmitOut:
    tenant = _tenant(db, user)
    if not settings.indexnow_key:
        raise HTTPException(status_code=400, detail="服务器未配置 INDEXNOW_KEY。")
    if not tenant.site_origin:
        raise HTTPException(status_code=400, detail="请先设置客户官网。")
    urls = _indexnow_urls(tenant, body)
    if not urls:
        raise HTTPException(status_code=400, detail="没有可提交的同域 URL。")
    host = origin_host(normalize_origin(tenant.site_origin))
    payload = {
        "host": host,
        "key": settings.indexnow_key,
        "keyLocation": _indexnow_key_location(tenant),
        "urlList": urls,
    }
    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(INDEXNOW_ENDPOINT, json=payload)
        status = "submitted" if response.status_code in {200, 202} else "error"
        note = "IndexNow 已接收 URL 更新通知；这不保证收录或排名。" if status == "submitted" else f"IndexNow 返回异常：{response.text[:500]}"
    except httpx.HTTPError as exc:
        response = None
        status = "error"
        note = f"IndexNow 提交失败：{exc}"
    db.add(
        IndexNowSubmission(
            tenant_id=user.tenant_id,
            host=host,
            key_location=payload["keyLocation"],
            urls="\n".join(urls),
            status=status,
            http_status=response.status_code if response is not None else None,
            response_text=(response.text if response is not None else note)[:1000],
            submitted_by=user.id,
        )
    )
    _finish_data_sync(db, user, source="indexnow", mode="manual", status=status, submitted=len(urls), note=note)
    db.commit()
    return IndexNowSubmitOut(status=status, submitted=len(urls), http_status=response.status_code if response is not None else None, note=note)


@router.post("/performance/import-csv", response_model=SeoPerformanceImportOut, status_code=201)
def import_seo_performance_csv(
    body: SeoPerformanceImportIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SeoPerformanceImportOut:
    reader = csv.DictReader(StringIO(body.csv_text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV 没有表头，无法识别字段。")
    imported = SeoPerformanceImport(
        tenant_id=user.tenant_id,
        source=body.source,
        filename=body.filename or PERFORMANCE_SOURCE_LABELS.get(body.source, body.source),
        imported_by=user.id,
        note="已按中英文常见字段解析 clicks / impressions / CTR / position。",
    )
    db.add(imported)
    db.flush()
    count = 0
    for raw in reader:
        clicks = _parse_int(_csv_value(raw, "clicks"))
        impressions = _parse_int(_csv_value(raw, "impressions"))
        query = _csv_value(raw, "query")
        page_url = _csv_value(raw, "page_url")
        if not any([clicks, impressions, query, page_url]):
            continue
        db.add(
            SeoPerformanceRow(
                tenant_id=user.tenant_id,
                import_id=imported.id,
                source=body.source,
                date=_csv_value(raw, "date"),
                country=_csv_value(raw, "country"),
                device=_csv_value(raw, "device"),
                query=query,
                page_url=page_url,
                clicks=clicks,
                impressions=impressions,
                ctr=_parse_float(_csv_value(raw, "ctr")),
                position=_parse_float(_csv_value(raw, "position")),
            )
        )
        count += 1
    if count == 0:
        raise HTTPException(status_code=400, detail="没有识别到可导入的搜索表现数据。请确认 CSV 包含查询、页面、点击、曝光等字段。")
    imported.rows_imported = count
    db.commit()
    db.refresh(imported)
    return SeoPerformanceImportOut(**imported.__dict__)


@router.post("/performance/pagespeed", response_model=list[PageSpeedAuditOut])
def run_pagespeed_audits(
    body: PageSpeedRunIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PageSpeedAuditOut]:
    tenant = _tenant(db, user)
    if not tenant.site_origin:
        raise HTTPException(status_code=400, detail="请先设置客户官网，再运行测速。")
    pages = db.query(SitePage).filter(SitePage.tenant_id == user.tenant_id).order_by(SitePage.path).all()
    urls = _pagespeed_targets(tenant, pages, body.urls, body.limit)
    strategies = [s for s in body.strategies if s in {"mobile", "desktop"}] or ["mobile"]
    audits: list[PageSpeedAudit] = []
    for url in urls:
        for strategy in strategies:
            try:
                metrics = _run_pagespeed(db, user.tenant_id, url, strategy)
                audit = PageSpeedAudit(tenant_id=user.tenant_id, url=url, strategy=strategy, status="ok", **metrics)
            except Exception as exc:
                audit = PageSpeedAudit(
                    tenant_id=user.tenant_id,
                    url=url,
                    strategy=strategy,
                    status="error",
                    detail=f"PageSpeed Insights 测速失败：{exc}",
                )
            db.add(audit)
            audits.append(audit)
    db.commit()
    for audit in audits:
        db.refresh(audit)
    return [PageSpeedAuditOut(**audit.__dict__) for audit in audits]


@router.get("/report", response_model=SeoReportOut)
def seo_report(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> SeoReportOut:
    tenant = _tenant(db, user)
    targets = _diagnosis_targets(db, user)
    performance = _performance_summary(db, user)
    serp = performance.serp
    target_markets = targets["markets"]
    target_keywords = targets["keywords"]
    market_by_id = targets["market_by_id"]
    seo_by_id = {p.id: p for p in targets["seo_pages"]}
    pages = db.query(SitePage).filter(SitePage.tenant_id == user.tenant_id).order_by(SitePage.path).all()
    issues = (
        db.query(OnsiteIssue)
        .options(selectinload(OnsiteIssue.page))
        .filter(OnsiteIssue.tenant_id == user.tenant_id)
        .order_by(OnsiteIssue.severity, OnsiteIssue.status, OnsiteIssue.created_at)
        .all()
    )
    sessions = (
        db.query(CrawlSession)
        .filter(CrawlSession.tenant_id == user.tenant_id)
        .order_by(CrawlSession.started_at.desc())
        .limit(1)
        .all()
    )
    generated = datetime.now(timezone.utc)
    active = [i for i in issues if _active_issue(i)]
    critical = [i for i in active if i.severity == "critical"]
    high = [i for i in active if i.severity == "high"]
    low = [i for i in active if i.severity == "low"]
    product_pages = [p for p in pages if _page_type(p) in {"product", "solution"}]
    sitemap_pages = [p for p in pages if p.is_in_sitemap == "yes"]
    orphan_issues = [i for i in issues if i.title.startswith("孤岛页面") and i.status not in {"verified", "wont_fix"}]
    inaccessible = [p for p in pages if (p.crawl_status or "").startswith("http_") or p.crawl_status in {"fetch_error", "robots_blocked"}]
    needs_js = [p for p in pages if p.crawl_status == "needs_js" or p.needs_js]
    priority = sorted(active, key=_issue_sort_key)
    groups = _issue_group_rows(active)
    gsc_needed = [i for i in active if i.category == "index"]
    b2b_issues = [i for i in active if i.category == "b2b"]
    lines = [
        f"# SEO 诊断报告 - {tenant.name}",
        "",
        "## 一句话结论",
        "",
        f"本次诊断共检查 {len(pages)} 个页面，发现 {len(active)} 个待处理问题，其中紧急 {len(critical)} 个、重要 {len(high)} 个、一般 {len(low)} 个。"
        "建议先处理影响抓取、收录确认、规范 URL、结构化数据和 B2B 转化信息的问题，再进入内容优化。",
        "",
        "## 本次诊断范围",
        "",
        f"- 客户站点：{tenant.site_origin or '未设置'}",
        f"- 报告时间：{generated.strftime('%Y-%m-%d %H:%M')}",
        f"- 已发现页面：{len(pages)} 个",
        f"- sitemap 覆盖：{len(sitemap_pages)} 个页面",
        f"- 产品/方案类页面：{len(product_pages)} 个",
        f"- GSC 状态：{performance.gsc_status}。Bing 状态：{performance.bing_status}。",
        f"- SERP 市场表现：{serp.status if serp else '未配置'}，已查询 {serp.total_runs if serp else 0} 轮。",
        f"- 测速状态：PageSpeed Insights {performance.pagespeed_status}。",
        "",
        "## 诊断目标",
        "",
        "### 目标国家 / 市场",
        "",
    ]
    if target_markets:
        for market in target_markets:
            lines.append(f"- {market.name}（{market.country_code} / {market.primary_locale}）：{market.status}，机会分 {market.opportunity_score}")
    else:
        lines.append("- 未设置目标国家。建议先在洞察模块登记目标市场，再进行 SEO 诊断。")
    lines += [
        "",
        "### 目标关键词 / 选题",
        "",
    ]
    if target_keywords:
        for keyword, locale, market_name, status in target_keywords[:12]:
            lines.append(f"- {keyword}（{locale} / {market_name} / {status}）")
        if len(target_keywords) > 12:
            lines.append(f"- 另有 {len(target_keywords) - 12} 个关键词/需求信号未在摘要中展开。")
    else:
        lines.append("- 未设置目标关键词。建议先登记核心产品词、行业词、采购意图词，再跑诊断。")
    lines += [
        "",
        "### 诊断口径",
        "",
        "- 技术 SEO 问题会优先服务目标国家和目标关键词对应页面。",
        "- 未绑定目标关键词的页面仍会诊断，但在整改优先级上应低于核心产品/方案页。",
        "- 速度体验使用 PageSpeed Insights；搜索表现优先使用 GSC/Bing CSV 或后续授权 API。",
        "",
    ]
    lines += [
        "## SEO 表现",
        "",
    ]
    if performance.total_impressions:
        lines += [
            f"- 总曝光：{performance.total_impressions}，总点击：{performance.total_clicks}，平均 CTR：{performance.avg_ctr if performance.avg_ctr is not None else '未测'}%，平均排名：{performance.avg_position if performance.avg_position is not None else '未测'}。",
            "- 重点国家：" + "；".join(f"{item.key} 曝光 {item.impressions} / 点击 {item.clicks}" for item in performance.by_country[:5]),
            "- 重点关键词：" + "；".join(f"{item.key} 曝光 {item.impressions} / 点击 {item.clicks} / 排名 {item.position or '未测'}" for item in performance.by_query[:5]),
            "",
        ]
    else:
        lines += [
            "- 暂未导入 GSC/Bing 搜索表现数据，无法判断真实曝光、点击、CTR 和平均排名。",
            "- 当前收录相关结论仍按“需授权核验”处理，不能直接判定已收录或未收录。",
            "",
        ]
    lines += ["### SERP 竞争表现", ""]
    if serp and serp.latest_runs:
        lines += [
            f"- Bright Data SERP 状态：{serp.status}。已记录 {serp.total_runs} 轮关键词查询。",
            f"- 我方可见：{serp.own_visible_runs} 轮；竞品可见：{serp.competitor_visible_runs} 轮；我方平均最佳排名：{serp.avg_own_position if serp.avg_own_position is not None else '未出现'}。",
            "",
        ]
        for run in serp.latest_runs[:8]:
            own = run.own_best_position if run.own_best_position is not None else "未出现"
            comp = run.competitor_best_position if run.competitor_best_position is not None else "未出现"
            lines.append(f"- {run.keyword}（{run.country}/{run.device}）：我方 {own}，竞品 {comp}，前 {run.result_count} 条第三方 {run.third_party_count} 个。")
        if serp.top_third_party_domains:
            lines.append("- 高频第三方域名：" + "；".join(f"{item['domain']}({item['count']})" for item in serp.top_third_party_domains[:6]))
        lines.append("")
    else:
        lines += [
            "- 暂未运行 SERP 查询。建议用目标国家和核心关键词查询 Google 前 10/20，判断我方、竞品和第三方平台占位。",
            "- SERP 查询结果是市场可见度证据，不等同 GSC 点击/曝光，也不等同真实外链权重。",
            "",
        ]
    if performance.speed_latest:
        lines += ["### 速度体验", ""]
        for audit in performance.speed_latest[:6]:
            lines.append(
                f"- {audit.strategy} · {audit.url}：性能 {_score_text(audit.performance_score)}，SEO {_score_text(audit.seo_score)}，LCP {audit.lcp_ms or '未测'}ms，状态 {audit.status}。"
            )
        lines.append("")
    else:
        lines += [
            "### 速度体验",
            "",
            "- 暂未运行 PageSpeed Insights 测速。建议先测首页、核心产品页、核心方案页的移动端和桌面端。",
            "",
        ]
    if sessions:
        s = sessions[0]
        lines += [
            "## 抓取概况",
            "",
            f"- 本次最多抓取 {s.max_urls} 个 URL，最大深度 {s.max_depth}。",
            f"- 实际发现 {s.discovered} 个 URL，成功读取 {s.fetched} 个，失败 {s.failed} 个。",
            f"- robots 阻止 {s.robots_blocked} 个，疑似需要浏览器渲染 {s.needs_js} 个。",
            f"- 备注：{s.note or '无'}",
            "",
        ]
    lines += [
        "## 主要风险",
        "",
        f"1. 抓取与访问风险：{len(inaccessible)} 个页面存在访问失败、404、服务器错误或 robots 阻止。",
        f"2. 收录确认风险：{len(gsc_needed)} 个页面需要接入 GSC 后确认真实索引状态。",
        f"3. 结构与规范风险：{sum(1 for i in active if i.category in {'canonical', 'schema', 'heading'})} 个问题影响搜索引擎和 AI 对页面的理解。",
        f"4. B2B 获客风险：{len(b2b_issues)} 个问题影响海外买家判断供应商能力和发起询盘。",
        f"5. JS 渲染风险：{len(needs_js)} 个页面疑似需要浏览器渲染，普通 HTML 抓取可能读不到完整内容。",
        f"6. SERP 可见度风险：{(serp.total_runs - serp.own_visible_runs) if serp else '未测'} 个关键词查询轮次未观察到我方自然结果。",
        "",
        "## 问题汇总",
        "",
    ]
    if groups:
        for (severity, category, title), count in groups[:12]:
            lines.append(f"- {_severity_label(severity)} · {_category_label(category)} · {title}：涉及 {count} 个页面")
    else:
        lines.append("- 当前没有待处理问题。")
    lines += [
        "",
        "## 优先整改清单",
        "",
    ]
    for idx, issue in enumerate(priority[:20], start=1):
        page = issue.page
        lines += [
            f"### {idx}. {_severity_label(issue.severity)} · {issue.title}",
            "",
            f"- 页面：{_page_label(page)}",
            f"- 目标国家：{_issue_target_market(issue, page, market_by_id)}",
            f"- 关联关键词：{_issue_target_keyword(issue, page, seo_by_id)}",
            f"- 问题类型：{_category_label(issue.category)}",
            f"- 当前状态：{_status_name(issue.status)}",
            f"- 为什么重要：{_issue_impact(issue)}",
            f"- 诊断依据：{issue.detail or '暂无详细证据'}",
            f"- 建议动作：{_issue_action(issue)}",
            f"- 建议负责人：{_issue_owner(issue)}",
            f"- 复测方式：{_issue_retest(issue)}",
            "",
        ]
    if not priority:
        lines.append("当前没有诊断问题。")
    lines += [
        "",
        "## 需要客户配合",
        "",
        "1. 提供 Google Search Console / Bing Webmaster Tools 授权，用于确认真实收录、曝光和点击。",
        "2. 确认产品参数、认证、应用行业、MOQ、交期、质保、案例等 B2B 事实，避免 AI 或执行人员误写。",
        "3. 指定客户网站技术联系人，处理 404、canonical、schema、sitemap、robots、页面模板等技术项。",
        "4. 每轮修改上线后，回到系统执行复测，形成“发现问题 - 整改 - 复测”的闭环。",
        "",
        "## 下一步建议",
        "",
        "1. 第一优先级：处理无法访问、noindex、canonical、schema、重复 URL 等基础问题。",
        "2. 第二优先级：补齐产品/方案页的 B2B 转化信息，包括参数、应用场景、认证、案例和询盘入口。",
        "3. 第三优先级：优化文章、图片 alt、内链和页面深度，提升搜索引擎与 AI 系统的可理解性。",
        "4. 报告中的 AI 建议均为草案，客户业务事实必须人工确认后再上线。",
        "",
    ]
    return SeoReportOut(title=f"SEO 诊断报告 - {tenant.name}", markdown="\n".join(lines), generated_at=generated)


@router.get("/report-table", response_model=SeoReportTableOut)
def seo_report_table(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> SeoReportTableOut:
    targets = _diagnosis_targets(db, user)
    market_by_id = targets["market_by_id"]
    seo_by_id = {p.id: p for p in targets["seo_pages"]}
    performance_rows = db.query(SeoPerformanceRow).filter(SeoPerformanceRow.tenant_id == user.tenant_id).all()
    serp = _serp_summary(db, user)
    issues = (
        db.query(OnsiteIssue)
        .options(selectinload(OnsiteIssue.page))
        .filter(OnsiteIssue.tenant_id == user.tenant_id)
        .order_by(OnsiteIssue.severity, OnsiteIssue.status, OnsiteIssue.created_at)
        .all()
    )
    generated = datetime.now(timezone.utc)
    active = sorted([i for i in issues if _active_issue(i)], key=_issue_sort_key)
    has_speed = db.query(PageSpeedAudit.id).filter(PageSpeedAudit.tenant_id == user.tenant_id).first() is not None
    out = StringIO()
    writer = csv.writer(out)
    writer.writerow([
        "优先级",
        "严重程度",
        "问题类型",
        "目标国家/地区",
        "关联关键词",
        "页面",
        "页面URL",
        "当前状态",
        "客户能理解的问题",
        "为什么影响获客",
        "建议整改动作",
        "建议负责人",
        "复测方式",
        "抓取状态",
        "HTTP状态",
        "sitemap状态",
        "页面类型",
        "URL深度",
        "正文规模",
        "图片Alt缺失",
        "测速状态",
        "页面抓取方式",
        "JS渲染状态",
        "SERP我方可见轮次",
        "SERP竞品可见轮次",
        "SERP第三方高频域名",
        "曝光",
        "点击",
        "CTR",
        "平均排名",
        "技术证据",
    ])
    for index, issue in enumerate(active, start=1):
        page = issue.page
        page_perf = _page_performance(performance_rows, page)
        page_type = _page_type(page) if page else "other"
        word_count = page.word_count if page else 0
        missing_alt = page.images_missing_alt if page else 0
        image_count = page.image_count if page else 0
        evidence_bits = []
        if page:
            evidence_bits.append(f"抓取={_crawl_label(page.crawl_status)}")
            if page.http_status:
                evidence_bits.append(f"HTTP={page.http_status}")
            if page.content_type:
                evidence_bits.append(f"Content-Type={page.content_type}")
            if page.ttfb_ms is not None:
                evidence_bits.append(f"TTFB={page.ttfb_ms}ms")
            if page.redirect_count:
                evidence_bits.append(f"跳转={page.redirect_count}次")
            if page.body_hash:
                evidence_bits.append(f"内容指纹={page.body_hash[:12]}")
            if page.fetch_mode:
                evidence_bits.append(f"抓取方式={page.fetch_mode}")
            if page.render_status and page.render_status != "not_needed":
                evidence_bits.append(f"渲染={page.render_status}")
            evidence_bits.append(f"sitemap={_sitemap_label(page.is_in_sitemap)}")
            evidence_bits.append(f"URL深度={_url_depth(page.path)}")
            if word_count:
                evidence_bits.append(f"正文约{word_count}词")
            if image_count:
                evidence_bits.append(f"图片缺alt {missing_alt}/{image_count}")
        if issue.evidence:
            evidence_bits.append(issue.evidence.replace("\n", " / ")[:500])
        writer.writerow([
            f"P{index}",
            _severity_label(issue.severity),
            _category_label(issue.category),
            _issue_target_market(issue, page, market_by_id),
            _issue_target_keyword(issue, page, seo_by_id),
            page.title or page.meta_title or page.path if page else "",
            page.path if page else "",
            _status_name(issue.status),
            issue.title,
            _issue_impact(issue),
            _issue_action(issue),
            _issue_owner(issue),
            _issue_retest(issue),
            _crawl_label(page.crawl_status if page else None),
            page.http_status if page and page.http_status else "未测",
            _sitemap_label(page.is_in_sitemap if page else None),
            PAGE_TYPE_LABELS.get(page_type, page_type),
            _url_depth(page.path) if page else "",
            f"约 {word_count or 0} 词",
            f"{missing_alt or 0}/{image_count or 0}",
            "见 PageSpeed 汇总" if has_speed else "未测速",
            page.fetch_mode if page else "",
            page.render_status if page else "",
            serp.own_visible_runs if serp else "未测",
            serp.competitor_visible_runs if serp else "未测",
            "；".join(f"{item['domain']}({item['count']})" for item in (serp.top_third_party_domains if serp else [])[:5]) or "未测",
            page_perf.impressions if page_perf else "未导入",
            page_perf.clicks if page_perf else "未导入",
            f"{page_perf.ctr}%" if page_perf and page_perf.ctr is not None else "未导入",
            page_perf.position if page_perf and page_perf.position is not None else "未导入",
            "；".join(evidence_bits) or issue.detail,
        ])
    return SeoReportTableOut(filename=f"seo整改执行表-{generated.date().isoformat()}.csv", csv=out.getvalue(), generated_at=generated)


@router.post("/crawl-or-seed", response_model=CrawlOrSeedOut)
def crawl_or_seed(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> CrawlOrSeedOut:
    """Expand inventory from seeded internal links. No live HTTP, no GSC."""
    pages = db.query(SitePage).filter(SitePage.tenant_id == user.tenant_id).all()
    known = {p.path for p in pages}
    seeded = 0
    for page in pages:
        for path in parse_internal_paths(page.internal_links):
            if path in known:
                continue
            db.add(
                SitePage(
                    tenant_id=user.tenant_id,
                    market_id=page.market_id,
                    path=path,
                    locale=page.locale,
                    title=path.rsplit("/", 1)[-1] or path,
                    index_status="untested",
                    crawl_status="untested",
                    notes="由工作区内链种子登记。未抓取线上，收录未测。",
                )
            )
            known.add(path)
            seeded += 1
    db.commit()
    total = db.query(func.count(SitePage.id)).filter(SitePage.tenant_id == user.tenant_id).scalar() or 0
    return CrawlOrSeedOut(
        seeded=seeded,
        pages=total,
        note="只从已登记页的内链扩清单。线上回抓请用「抓这一站」。不跑 GSC。",
    )


@router.get("/settings", response_model=SiteSettingsOut)
def get_site_settings(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> SiteSettingsOut:
    tenant = _tenant(db, user)
    return SiteSettingsOut(site_origin=tenant.site_origin or "")


@router.patch("/settings", response_model=SiteSettingsOut)
def update_site_settings(
    body: SiteOriginIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SiteSettingsOut:
    tenant = _tenant(db, user)
    try:
        tenant.site_origin = normalize_origin(body.site_origin)
    except OriginError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return SiteSettingsOut(site_origin=tenant.site_origin)


@router.post("/fetch-registered", response_model=FetchRegisteredOut)
def fetch_registered(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> FetchRegisteredOut:
    """HTTP GET already-registered pages only. Observation layer only. No GSC."""
    tenant = _tenant(db, user)
    origin = _require_origin(tenant)
    pages = db.query(SitePage).filter(SitePage.tenant_id == user.tenant_id).all()
    targets = registered_targets(origin, pages)
    rows = fetch_many(targets, origin)
    fetched, failed, verified, created, results = _ingest_snapshots(db, user, rows)
    pages_after = db.query(SitePage).filter(SitePage.tenant_id == user.tenant_id).all()
    db.commit()
    note = (
        f"只抓已登记页（含站点根），主机名必须是 {origin_host(origin)}。"
        "观察层已覆盖并按规则验收。改稿未动，本请求不跑 LLM。收录仍未测。"
    )
    return FetchRegisteredOut(
        origin=origin,
        fetched=fetched,
        failed=failed,
        verified=verified,
        created=created,
        pages=len(pages_after),
        note=note,
        results=results,
        ai_status="skipped",
    )


@router.post("/crawl-site", response_model=CrawlSessionOut)
def crawl_site(
    body: CrawlSiteIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CrawlSessionOut:
    """Discover sitemap/internal links and crawl a bounded set of same-host pages."""
    tenant = _tenant(db, user)
    origin = _require_origin(tenant)
    session = CrawlSession(
        tenant_id=user.tenant_id,
        origin=origin,
        mode="site",
        max_urls=body.max_urls,
        max_depth=body.max_depth,
        status="running",
        note="站点诊断抓取运行中。",
    )
    db.add(session)
    db.flush()
    pages = db.query(SitePage).filter(SitePage.tenant_id == user.tenant_id).all()
    rows = fetch_site(origin, pages, max_urls=body.max_urls, max_depth=body.max_depth)
    fetched = failed = created = verified = robots_blocked = needs_js_count = 0
    known_by_path = {p.path: p for p in db.query(SitePage).filter(SitePage.tenant_id == user.tenant_id).all()}
    for target, snap in rows:
        path = urlparse(snap.final_url or target.url).path or "/"
        page = target.page or known_by_path.get(path)
        if page is None:
            page = SitePage(
                tenant_id=user.tenant_id,
                path=path,
                locale="und",
                title=path.rsplit("/", 1)[-1] or "/",
                index_status="untested",
                crawl_status="untested",
                discovery_source=target.source,
                is_in_sitemap="yes" if target.in_sitemap else "no",
                notes="由站点抓取自动发现。收录仍未测。",
            )
            db.add(page)
            db.flush()
            known_by_path[path] = page
        page.discovery_source = target.source or page.discovery_source or "internal_link"
        page.is_in_sitemap = "yes" if target.in_sitemap else (page.is_in_sitemap or "no")
        apply_observation(page, snap)
        if snap.usable:
            fetched += 1
            c, _s, v = _analyze_one(db, user, page)
            created += c
            verified += v
        else:
            failed += 1
        if snap.crawl_status == "robots_disallow":
            robots_blocked += 1
        if snap.needs_js:
            needs_js_count += 1
    site_created, site_refreshed = _reconcile_site_patterns(
        db, user, db.query(SitePage).filter(SitePage.tenant_id == user.tenant_id).all()
    )
    created += site_created
    session.status = "finished"
    session.discovered = len(rows)
    session.fetched = fetched
    session.failed = failed
    session.created = created
    session.verified = verified
    session.robots_blocked = robots_blocked
    session.needs_js = needs_js_count
    session.finished_at = datetime.now(timezone.utc)
    session.note = (
        f"已完成站点诊断抓取：发现 {len(rows)} 个 URL，成功 {fetched}，失败 {failed}，"
        f"新增问题 {created}，刷新站点级问题 {site_refreshed}，验收 {verified}。AI 不参与抓取事实。"
    )
    db.commit()
    db.refresh(session)
    return _crawl_session_out(session)


@router.get("/crawl-sessions", response_model=list[CrawlSessionOut])
def list_crawl_sessions(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CrawlSessionOut]:
    rows = (
        db.query(CrawlSession)
        .filter(CrawlSession.tenant_id == user.tenant_id)
        .order_by(CrawlSession.started_at.desc())
        .limit(10)
        .all()
    )
    return [_crawl_session_out(row) for row in rows]


@router.post("/pages/{page_id}/fetch", response_model=FetchRegisteredOut)
def fetch_one_page(
    page_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FetchRegisteredOut:
    tenant = _tenant(db, user)
    origin = _require_origin(tenant)
    page = _owned_page(db, user, page_id)
    snap, created, verified = _fetch_one_registered(db, user, page, origin)
    db.commit()
    failed = 0 if snap.usable else 1
    fetched = 1 if snap.usable else 0
    note = "已回抓本页观察层并按规则验收。改稿未覆盖，本请求不跑 LLM。收录仍未测。"
    return FetchRegisteredOut(
        origin=origin,
        fetched=fetched,
        failed=failed,
        verified=verified,
        created=created,
        pages=1,
        note=note,
        results=[
            FetchPageResultOut(
                page_id=page.id,
                path=page.path,
                url=build_fetch_url(origin, page.path),
                crawl_status=snap.crawl_status,
                http_status=snap.http_status,
                final_url=snap.final_url,
                needs_js=snap.needs_js,
                fetch_mode=snap.fetch_mode,
                render_status=snap.render_status,
                error=snap.error,
                verified=verified,
                created=created,
            )
        ],
        ai_status="skipped",
    )


def _tenant(db: Session, user: User) -> Tenant:
    tenant = db.get(Tenant, user.tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="租户不存在")
    return tenant


def _require_origin(tenant: Tenant) -> str:
    try:
        return normalize_origin(tenant.site_origin or "")
    except OriginError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _page_issues(db: Session, page_id: str) -> list[OnsiteIssue]:
    return db.query(OnsiteIssue).filter(OnsiteIssue.page_id == page_id).all()


def _upsert_site_issue(
    db: Session,
    *,
    user: User,
    page: SitePage,
    category: str,
    title: str,
    detail: str,
    severity: str,
    proposed_change: str,
) -> tuple[int, int]:
    row = (
        db.query(OnsiteIssue)
        .filter(
            OnsiteIssue.tenant_id == user.tenant_id,
            OnsiteIssue.page_id == page.id,
            OnsiteIssue.category == category,
            OnsiteIssue.title == title,
        )
        .first()
    )
    if row is None:
        db.add(
            OnsiteIssue(
                tenant_id=user.tenant_id,
                page_id=page.id,
                category=category,
                title=title,
                detail=detail,
                proposed_change=proposed_change,
                severity=severity,
                risk=severity_to_risk(severity),
                status="open",
                metric_status="untested",
            )
        )
        return 1, 0
    if row.status in OPENISH:
        row.detail = detail
        row.severity = severity
        return 0, 1
    return 0, 0


def _reconcile_site_patterns(db: Session, user: User, pages: list[SitePage]) -> tuple[int, int]:
    created = refreshed = 0
    by_title: dict[str, list[SitePage]] = {}
    by_desc: dict[str, list[SitePage]] = {}
    inlinks: dict[str, int] = {p.path: 0 for p in pages}
    for page in pages:
        title = (page.meta_title or "").strip().lower()
        desc = (page.meta_description or "").strip().lower()
        if title:
            by_title.setdefault(title, []).append(page)
        if desc and len(desc) > 20:
            by_desc.setdefault(desc, []).append(page)
        for raw in parse_internal_paths(page.internal_links):
            if raw in inlinks:
                inlinks[raw] += 1

    def add(page: SitePage, category: str, title: str, detail: str, severity: str, proposed: str) -> None:
        nonlocal created, refreshed
        c, r = _upsert_site_issue(
            db,
            user=user,
            page=page,
            category=category,
            title=title,
            detail=detail,
            severity=severity,
            proposed_change=proposed,
        )
        created += c
        refreshed += r

    for title, rows in by_title.items():
        if len(rows) < 2:
            continue
        paths = ", ".join(p.path for p in rows[:8])
        for page in rows:
            add(
                page,
                "tdk",
                "Title 重复",
                f"当前 Title 与 {len(rows) - 1} 个页面重复：{paths}。",
                "high",
                "为不同产品/方案页面写唯一 Title，体现产品名、应用场景和目标市场。",
            )
    for desc, rows in by_desc.items():
        if len(rows) < 2:
            continue
        paths = ", ".join(p.path for p in rows[:8])
        for page in rows:
            add(
                page,
                "tdk",
                "Description 重复",
                f"当前 Description 与 {len(rows) - 1} 个页面重复：{paths}。",
                "low",
                "为每个核心页面写不同的描述，突出应用、参数、认证或询盘价值。",
            )
    for page in pages:
        if (page.path or "/") == "/":
            continue
        if page.is_in_sitemap == "yes" and inlinks.get(page.path, 0) == 0:
            add(
                page,
                "internal_link",
                "孤岛页面（sitemap 有但无内链入口）",
                "当前页面出现在 sitemap 中，但本次抓取未发现其他已抓页面链接到它。",
                "high",
                "从首页、产品分类页、相关文章或导航增加到该页面的可抓取内链。",
            )
        if page.is_in_sitemap != "yes" and inlinks.get(page.path, 0) > 0:
            add(
                page,
                "internal_link",
                "内链页面未进入 sitemap",
                "当前页面可从站内链接发现，但未确认出现在 sitemap 中。",
                "low",
                "确认该 URL 是否为正式页面；如是，加入 sitemap 并保持 canonical 一致。",
            )
    return created, refreshed


def _analyze_one(db: Session, user: User, page: SitePage) -> tuple[int, int, int]:
    created, skipped, verified = reconcile_issues(
        db, tenant_id=user.tenant_id, page=page, issues=_page_issues(db, page.id)
    )
    db.flush()
    return created, skipped, verified


def _ensure_root_page(db: Session, user: User, path: str = "/") -> SitePage:
    page = (
        db.query(SitePage)
        .filter(SitePage.tenant_id == user.tenant_id, SitePage.path == path)
        .first()
    )
    if page is None:
        page = SitePage(
            tenant_id=user.tenant_id,
            path=path,
            locale="und",
            title=path or "/",
            index_status="untested",
            crawl_status="untested",
            notes="站点根。由抓取登记，未编收录。",
        )
        db.add(page)
        db.flush()
    return page


def _ingest_snapshots(
    db: Session,
    user: User,
    rows: list[tuple[str, SitePage | None, object]],
) -> tuple[int, int, int, int, list[FetchPageResultOut]]:
    fetched = failed = verified = created = 0
    results: list[FetchPageResultOut] = []
    for url, page, snap in rows:
        if page is None:
            path = "/"
            page = _ensure_root_page(db, user, path)
        apply_observation(page, snap)
        page_created = page_verified = 0
        if snap.usable:
            fetched += 1
            c, _s, v = _analyze_one(db, user, page)
            page_created, page_verified = c, v
            created += c
            verified += v
        else:
            failed += 1
        results.append(
            FetchPageResultOut(
                page_id=page.id,
                path=page.path,
                url=url,
                crawl_status=snap.crawl_status,
                http_status=snap.http_status,
                final_url=snap.final_url,
                needs_js=snap.needs_js,
                fetch_mode=snap.fetch_mode,
                render_status=snap.render_status,
                error=snap.error,
                verified=page_verified,
                created=page_created,
            )
        )
    return fetched, failed, verified, created, results


def _fetch_one_registered(db: Session, user: User, page: SitePage, origin: str):
    url = build_fetch_url(origin, page.path)
    with make_client() as client:
        robots = load_robots(origin, client)
        snap = fetch_url(url, allowed_hosts_from_origin(origin), client=client, robots=robots)
    apply_observation(page, snap)
    created = verified = 0
    if snap.usable:
        created, _skipped, verified = _analyze_one(db, user, page)
    return snap, created, verified


def _ai_after_analyze(db: Session, user: User, pages: list[SitePage], *, limit: int = 3) -> tuple[str, int, int]:
    issues = [i for i in _ai_issue_candidates(db, user) if _issue_needs_ai(i)]
    if not configured():
        limit = len(issues)
    by_id = {p.id: p for p in pages}
    processed = 0
    for issue in issues[:limit]:
        page = by_id.get(issue.page_id) or db.get(SitePage, issue.page_id)
        if page is None:
            continue
        assist_onsite_issue(db, issue, page, step="analyze")
        processed += 1
    remaining = max(len(issues) - processed, 0)
    return (UNCONFIGURED if not configured() else "ok", processed, remaining)


@router.post("/analyze", response_model=AnalyzeOut)
def analyze_inventory(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> AnalyzeOut:
    pages = db.query(SitePage).filter(SitePage.tenant_id == user.tenant_id).all()
    created = skipped = verified = 0
    for page in pages:
        c, s, v = _analyze_one(db, user, page)
        created += c
        skipped += s
        verified += v
    site_created, site_skipped = _reconcile_site_patterns(db, user, pages)
    created += site_created
    skipped += site_skipped
    ai_status, ai_processed, ai_remaining = _ai_after_analyze(db, user, pages)
    db.commit()
    note = "分析只读当前观察，不改改稿，也不应用到线上。已满足的工单标为已验收。"
    if ai_processed:
        note += f" 已先生成 {ai_processed} 条 AI 建议。"
    if ai_remaining:
        note += f" 还有 {ai_remaining} 条可继续批量生成。"
    if ai_status == UNCONFIGURED:
        note += " LLM 未配置，诊断/改稿未编造。"
    return AnalyzeOut(
        created=created, skipped=skipped, verified=verified, pages=len(pages), note=note, ai_status=ai_status
    )


@router.post("/pages/{page_id}/analyze", response_model=AnalyzeOut)
def analyze_one_page(
    page_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalyzeOut:
    page = _owned_page(db, user, page_id)
    created, skipped, verified = _analyze_one(db, user, page)
    ai_status, ai_processed, ai_remaining = _ai_after_analyze(db, user, [page])
    db.commit()
    note = "分析只读当前观察，不改改稿，也不应用到线上。已满足的工单标为已验收。"
    if ai_processed:
        note += f" 已先生成 {ai_processed} 条 AI 建议。"
    if ai_remaining:
        note += f" 还有 {ai_remaining} 条可继续批量生成。"
    if ai_status == UNCONFIGURED:
        note += " LLM 未配置，诊断/改稿未编造。"
    return AnalyzeOut(
        created=created, skipped=skipped, verified=verified, pages=1, note=note, ai_status=ai_status
    )


@router.post("/pages/{page_id}/issues", response_model=OnsiteIssueOut, status_code=201)
def create_issue(
    page_id: str,
    body: OnsiteIssueCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OnsiteIssueOut:
    page = _owned_page(db, user, page_id)
    if body.category not in CATEGORIES:
        raise HTTPException(status_code=400, detail="无效问题类型")
    severity = body.severity or default_severity(body.category)
    if severity not in SEVERITIES:
        raise HTTPException(status_code=400, detail="无效严重级别")
    risk = body.risk or severity_to_risk(severity)
    if risk not in RISKS:
        raise HTTPException(status_code=400, detail="无效风险等级")
    row = OnsiteIssue(
        tenant_id=user.tenant_id,
        page_id=page.id,
        category=body.category,
        title=body.title,
        detail=body.detail,
        proposed_change=body.proposed_change,
        severity=severity,
        risk=risk,
        status="open",
        metric_status="untested",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _issue_out(row, page)


@router.patch("/issues/{issue_id}/draft", response_model=OnsiteIssueOut)
def write_change_draft(
    issue_id: str,
    body: OnsiteDraftIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OnsiteIssueOut:
    row = _owned_issue(db, user, issue_id)
    if not body.proposed_change.strip():
        raise HTTPException(status_code=400, detail="改稿草稿不能为空")
    row.proposed_change = body.proposed_change
    if row.status == "open":
        row.status = "drafted"
    db.commit()
    db.refresh(row)
    return _issue_out(row)


@router.post("/issues/{issue_id}/apply-draft", response_model=OnsiteIssueOut)
def apply_draft(
    issue_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OnsiteIssueOut:
    row = _owned_issue(db, user, issue_id)
    if needs_confirm(row.severity, row.risk):
        raise HTTPException(status_code=400, detail="高风险任务不能自动落草稿，请走人工确认")
    if not (row.proposed_change or "").strip():
        raise HTTPException(status_code=400, detail="请先写改稿草稿，分析与应用是两步")
    page = db.get(SitePage, row.page_id)
    if page is None or page.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="页面不存在")
    row.status = "draft_applied"
    db.commit()
    db.refresh(row)
    return _issue_out(row, page)


@router.post("/issues/{issue_id}/confirm-apply", response_model=OnsiteIssueOut)
def confirm_apply(
    issue_id: str,
    body: ConfirmReadyIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OnsiteIssueOut:
    require_confirm(body.confirmed, action="应用到线上站点")
    row = _owned_issue(db, user, issue_id)
    if not needs_confirm(row.severity, row.risk):
        raise HTTPException(status_code=400, detail="低风险任务请用工作区落草稿，无需线上确认")
    if not (row.proposed_change or "").strip():
        raise HTTPException(status_code=400, detail="请先写改稿草稿，分析与应用是两步")
    page = db.get(SitePage, row.page_id)
    if page is None or page.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="页面不存在")
    row.status = "confirmed"
    tenant = _tenant(db, user)
    if (tenant.site_origin or "").strip():
        try:
            origin = normalize_origin(tenant.site_origin)
            _fetch_one_registered(db, user, page, origin)
        except OriginError:
            pass
    db.commit()
    db.refresh(row)
    return _issue_out(row, page)


@router.post("/issues/{issue_id}/mark-executed", response_model=OnsiteIssueOut)
def mark_executed(
    issue_id: str,
    body: OnsiteStatusIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OnsiteIssueOut:
    require_confirm(body.confirmed, action="标记已执行")
    row = _owned_issue(db, user, issue_id)
    if not (row.proposed_change or "").strip():
        raise HTTPException(status_code=400, detail="请先保存处理方案，再标记已执行")
    page = db.get(SitePage, row.page_id)
    if page is None or page.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="页面不存在")
    row.status = "confirmed"
    note = (body.note or "").strip()
    if note:
        row.evidence = ((row.evidence or "").rstrip() + f"\n人工执行记录：{note}").strip()
    db.commit()
    db.refresh(row)
    return _issue_out(row, page)


@router.post("/issues/{issue_id}/retest", response_model=OnsiteIssueOut)
def retest_issue(
    issue_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OnsiteIssueOut:
    row = _owned_issue(db, user, issue_id)
    page = db.get(SitePage, row.page_id)
    if page is None or page.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="页面不存在")
    tenant = _tenant(db, user)
    origin = _require_origin(tenant)
    try:
        _fetch_one_registered(db, user, page, origin)
    except OriginError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.flush()
    db.refresh(row)
    db.commit()
    db.refresh(row)
    return _issue_out(row, page)


@router.post("/issues/{issue_id}/wont-fix", response_model=OnsiteIssueOut)
def wont_fix_issue(
    issue_id: str,
    body: OnsiteStatusIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OnsiteIssueOut:
    row = _owned_issue(db, user, issue_id)
    page = db.get(SitePage, row.page_id)
    if page is None or page.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="页面不存在")
    row.status = "wont_fix"
    note = (body.note or "").strip()
    if note:
        row.evidence = ((row.evidence or "").rstrip() + f"\n忽略原因：{note}").strip()
    db.commit()
    db.refresh(row)
    return _issue_out(row, page)


@router.post("/issues/{issue_id}/reopen", response_model=OnsiteIssueOut)
def reopen_issue(
    issue_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OnsiteIssueOut:
    row = _owned_issue(db, user, issue_id)
    page = db.get(SitePage, row.page_id)
    if page is None or page.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="页面不存在")
    row.status = "drafted" if (row.proposed_change or "").strip() else "open"
    db.commit()
    db.refresh(row)
    return _issue_out(row, page)


@router.post("/issues/{issue_id}/ai", response_model=AiAssistOut)
def ai_issue(
    issue_id: str,
    body: AiStepIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AiAssistOut:
    row = db.get(OnsiteIssue, issue_id)
    if row is None or row.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="任务不存在")
    page = db.get(SitePage, row.page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="页面不存在")
    payload = assist_onsite_issue(db, row, page, step=body.step)
    db.commit()
    return AiAssistOut(**payload)


@router.post("/ai", response_model=AiAssistOut)
def ai_onsite_engine(
    body: AiStepIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AiAssistOut:
    pages = db.query(SitePage).filter(SitePage.tenant_id == user.tenant_id).all()
    created = skipped = 0
    limit = _ai_batch_limit(body.limit)
    if body.step in {"analyze", "all"}:
        for page in pages:
            c, s, _v = _analyze_one(db, user, page)
            created += c
            skipped += s
        site_created, site_skipped = _reconcile_site_patterns(db, user, pages)
        created += site_created
        skipped += site_skipped
    issues = [i for i in _ai_issue_candidates(db, user) if _issue_needs_ai(i)]
    if not issues:
        db.commit()
        return AiAssistOut(
            status="skipped",
            step=body.step,
            processed=0,
            remaining=0,
            limit=limit,
            detail=f"没有待处理问题。规则诊断新建 {created} 条，刷新 {skipped} 条。",
        )
    last: dict = {"status": UNCONFIGURED, "step": body.step, "detail": ""}
    processed = drafted = ok = errors = unconfigured = 0
    by_id = {p.id: p for p in pages}
    batch = issues[:limit]
    for issue in batch:
        page = by_id.get(issue.page_id)
        if page is None:
            continue
        last = assist_onsite_issue(db, issue, page, step=body.step)
        processed += 1
        if last.get("status") == "ok":
            ok += 1
        elif last.get("status") == UNCONFIGURED:
            unconfigured += 1
        elif last.get("status") == "error":
            errors += 1
        if (last.get("draft") or "").strip():
            drafted += 1
    db.commit()
    remaining = max(len(issues) - processed, 0)
    last["detail"] = (
        f"本次已处理 {processed} 条 AI 建议；"
        f"生成草案 {drafted} 条，成功 {ok} 条，未配置 {unconfigured} 条，错误 {errors} 条；"
        f"剩余约 {remaining} 条可继续处理。"
        f"规则诊断新建 {created} 条，刷新 {skipped} 条。"
    )
    last["processed"] = processed
    last["remaining"] = remaining
    last["limit"] = limit
    return AiAssistOut(**last)
