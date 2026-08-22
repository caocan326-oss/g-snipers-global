"""Onsite rules over the observation layer only.

Analysis never applies a change and never invents GSC index counts.
Re-analyze refreshes issue.detail from the current snapshot.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone

from app.models import OnsiteIssue, SitePage
from app.risk import CRITICAL, SEV_HIGH, SEV_LOW, default_severity, severity_to_risk
from app.schemas import SeoRankDistributionOut


def rank_distribution(positions: list[float | int | None]) -> SeoRankDistributionOut:
    out = SeoRankDistributionOut(total=len(positions))
    for position in positions:
        if position is None:
            out.unranked += 1
        elif position <= 10:
            out.top_10 += 1
        elif position <= 30:
            out.top_30 += 1
        elif position <= 50:
            out.top_50 += 1
        else:
            out.beyond_50 += 1
    return out

# Stable titles so re-analyze is idempotent per page + category + title.
FINDINGS = {
    "tdk_title": ("tdk", "缺少 Title", SEV_HIGH),
    "tdk_desc": ("tdk", "Description 过短或为空", SEV_LOW),
    "tdk_zh": ("tdk", "TDK 含中文", SEV_HIGH),
    "heading": ("heading", "缺少 H1", SEV_HIGH),
    "internal_link": ("internal_link", "缺少内链", SEV_LOW),
    "schema": ("schema", "页面缺少给搜索看的说明", CRITICAL),
    "schema_org": ("schema", "首页缺少公司介绍说明", CRITICAL),
    "schema_product": ("schema", "产品页缺少给搜索看的产品说明", SEV_HIGH),
    "schema_body_mismatch": ("schema", "页面说明和正文对不上", SEV_LOW),
    "index": ("index", "收录状态未测（需 GSC）", SEV_LOW),
    "noindex": ("index", "页面声明 noindex", CRITICAL),
    "geo_noindex": ("index", "关键页告诉搜索不要收录", CRITICAL),
    "canonical": ("canonical", "Canonical 未登记", CRITICAL),
    "js_shell": ("crawl", "不打开脚本时几乎没有正文", CRITICAL),
    "prefix_answer": ("content", "页面开头没有直接回答买家问题", SEV_HIGH),
    "image_alt": ("image", "图片 Alt 缺失", SEV_LOW),
    "thin_content": ("content", "正文内容过薄", SEV_LOW),
    "b2b_product": ("b2b", "B2B 产品/方案页信息不足", SEV_HIGH),
    "url_depth": ("crawl", "URL 层级过深", SEV_LOW),
}

_CJK = re.compile(r"[\u4e00-\u9fff]")
_LATIN_PREFIXES = ("en", "de", "fr", "es", "pt", "it", "nl", "pl", "sv", "da", "fi", "no", "cs", "ro", "hu")

OPENISH = {"open", "drafted", "draft_applied", "confirmed"}


@dataclass
class Finding:
    category: str
    title: str
    detail: str
    severity: str
    suggested_fix: str
    metric_status: str


def _has_h1(headings: str) -> bool:
    text = (headings or "").lower()
    return "h1" in text or text.strip().startswith("# ")


def _latin_locale(locale: str) -> bool:
    prefix = (locale or "").strip().lower().replace("_", "-").split("-", 1)[0]
    return prefix in _LATIN_PREFIXES


def _url_depth(path: str) -> int:
    return len([part for part in (path or "/").split("/") if part])


def _b2b_page_like(page: SitePage) -> bool:
    text = f"{page.path} {page.title} {page.meta_title}".lower()
    return any(token in text for token in ("product", "products", "solution", "solutions", "application", "industry", "case"))


def _home_like(page: SitePage) -> bool:
    path = (page.path or "/").strip().lower()
    return path in {"", "/", "/en", "/en/", "/home", "/index"}


def _schema_types(page: SitePage) -> set[str]:
    raw = f"{page.structured_data or ''}, {getattr(page, 'json_ld_types', '') or ''}".lower()
    return {part.strip().replace("schema.org/", "") for part in re.split(r"[,|;\n]+", raw) if part.strip()}


_ANSWER_PAT = re.compile(r"(是指|定义为|指的是|\bis\b|\brefers to\b|in summary|第一步|step\s*1|如下[:：])", re.I)


def analyze_page(page: SitePage) -> list[Finding]:
    """Read observation fields only. Index stays 未测 without GSC."""
    out: list[Finding] = []
    title = (page.meta_title or "").strip()
    if not title:
        out.append(
            Finding(
                category="tdk",
                title=FINDINGS["tdk_title"][1],
                detail="当前观察 Title 为空。分析只记问题，不改观察层，也不写改稿。",
                severity=SEV_HIGH,
                suggested_fix=f"{page.title} | 补 Title（改稿留在工单，不写进观察）",
                metric_status="untested",
            )
        )
    desc = (page.meta_description or "").strip()
    if len(desc) < 40:
        out.append(
            Finding(
                category="tdk",
                title=FINDINGS["tdk_desc"][1],
                detail="当前观察 Description 空或过短。无 GSC 展示数据，指标未测。",
                severity=SEV_LOW,
                suggested_fix=f"围绕「{page.title}」写 140–160 字符描述。",
                metric_status="untested",
            )
        )
    observed_tdk = f"{title} {desc}"
    if _latin_locale(page.locale) and _CJK.search(observed_tdk):
        out.append(
            Finding(
                category="tdk",
                title=FINDINGS["tdk_zh"][1],
                detail="当前观察 TDK 含中文，而页面语言不是中文。以本次抓取为准，不回放旧工单。",
                severity=SEV_HIGH,
                suggested_fix="按目标语言重写 Title / Description，上线后再抓验收。",
                metric_status="untested",
            )
        )
    if not _has_h1(page.headings):
        out.append(
            Finding(
                category="heading",
                title=FINDINGS["heading"][1],
                detail="当前观察未见 H1。分析不会写入 headings。",
                severity=SEV_HIGH,
                suggested_fix=f"H1 {page.title}",
                metric_status="untested",
            )
        )
    if not (page.internal_links or "").strip():
        out.append(
            Finding(
                category="internal_link",
                title=FINDINGS["internal_link"][1],
                detail="当前观察内链为空。",
                severity=SEV_LOW,
                suggested_fix="补一条相关内链路径。",
                metric_status="untested",
            )
        )
    schema = (page.structured_data or "").strip() or (getattr(page, "json_ld_types", "") or "").strip()
    if not schema:
        out.append(
            Finding(
                category="schema",
                title=FINDINGS["schema"][1],
                detail="当前观察无 JSON-LD / schema。上线改 HTML 属 critical。须改稿后再确认，分析不落稿。",
                severity=CRITICAL,
                suggested_fix='{"@context":"https://schema.org","@type":"WebPage"}',
                metric_status="untested",
            )
        )
    robots_text = f"{getattr(page, 'meta_robots', '')} {getattr(page, 'x_robots_tag', '')}".lower()
    if "noindex" in robots_text:
        out.append(
            Finding(
                category="index",
                title=FINDINGS["noindex"][1],
                detail="当前观察到 meta robots 或 X-Robots-Tag 含 noindex。是否允许索引必须人工确认。",
                severity=CRITICAL,
                suggested_fix="确认该页面是否应参与搜索收录；如应收录，移除 noindex 后复测。",
                metric_status="untested",
            )
        )
        if _b2b_page_like(page) or _home_like(page):
            out.append(
                Finding(
                    category="index",
                    title=FINDINGS["geo_noindex"][1],
                    detail="首页/产品/方案等应收录页面观察到 noindex；这会直接影响 Google 与 AI 搜索素材来源。",
                    severity=CRITICAL,
                    suggested_fix="确认页面是否应参与获客；若应收录，移除 noindex 并用 GSC 复测。",
                    metric_status="untested",
                )
            )
    types = _schema_types(page)
    if _home_like(page) and schema and not ({"organization", "website"} & types):
        out.append(
            Finding(
                category="schema",
                title=FINDINGS["schema_org"][1],
                detail=f"首页/站点级页面当前 JSON-LD 类型为 {schema or '空'}，未见 Organization 或 WebSite。",
                severity=CRITICAL,
                suggested_fix="补 Organization 与 WebSite JSON-LD，并确保 name/url 与官网可见正文一致。",
                metric_status="untested",
            )
        )
    if _b2b_page_like(page) and schema and not ({"product", "service"} & types):
        out.append(
            Finding(
                category="schema",
                title=FINDINGS["schema_product"][1],
                detail=f"产品/方案页当前 JSON-LD 类型为 {schema or '空'}，未见 Product 或 Service。",
                severity=SEV_HIGH,
                suggested_fix="为产品/方案页补 Product 或 Service schema；参数、认证、应用场景要和可见正文一致。",
                metric_status="untested",
            )
        )
    if schema and getattr(page, "word_count", 0) and page.word_count < 80:
        out.append(
            Finding(
                category="schema",
                title=FINDINGS["schema_body_mismatch"][1],
                detail=f"页面有结构化数据（{schema[:120]}），但可抽取正文约 {page.word_count} 词，AI/搜索系统难以核对。",
                severity=SEV_LOW,
                suggested_fix="让 schema 中的名称、产品、认证、FAQ 在正文中也可见，避免只在脚本里出现。",
                metric_status="untested",
            )
        )
    if not (getattr(page, "canonical", None) or "").strip():
        out.append(
            Finding(
                category="canonical",
                title=FINDINGS["canonical"][1],
                detail="当前观察无 Canonical。无 GSC 不判断是否被选为规范 URL。",
                severity=CRITICAL,
                suggested_fix=page.path,
                metric_status="untested",
            )
        )
    if getattr(page, "image_count", 0) and getattr(page, "images_missing_alt", 0):
        out.append(
            Finding(
                category="image",
                title=FINDINGS["image_alt"][1],
                detail=f"当前观察到 {page.image_count} 张图片，其中 {page.images_missing_alt} 张缺少 alt。",
                severity=SEV_LOW,
                suggested_fix="为产品图、认证图和关键说明图补充准确 alt；无法确认图片内容时交给人工核对。",
                metric_status="untested",
            )
        )
    if getattr(page, "word_count", 0) and page.word_count < 120 and page.crawl_status != "needs_js":
        out.append(
            Finding(
                category="content",
                title=FINDINGS["thin_content"][1],
                detail=f"当前可抽取正文约 {page.word_count} 个词/字段，可能不足以支撑买家判断。",
                severity=SEV_LOW,
                suggested_fix="补充产品参数、应用场景、FAQ、案例或询盘入口；业务事实必须人工确认。",
                metric_status="untested",
            )
        )
    if page.crawl_status == "needs_js" or getattr(page, "needs_js", False):
        out.append(
            Finding(
                category="crawl",
                title=FINDINGS["js_shell"][1],
                detail="当前 HTTP 快照显示主内容可能依赖客户端渲染。AI 检索类爬虫未必能稳定抽取正文。",
                severity=CRITICAL,
                suggested_fix="关键产品、参数、认证、FAQ 和首段定义应 SSR/预渲染进无 JS HTML。",
                metric_status="untested",
            )
        )
    prefix_text = " ".join([page.meta_description or "", page.headings or "", page.notes or ""])[:400]
    if _b2b_page_like(page) and prefix_text.strip() and not _ANSWER_PAT.search(prefix_text):
        out.append(
            Finding(
                category="content",
                title=FINDINGS["prefix_answer"][1],
                detail="当前标题/描述/首段线索未形成清晰定义、结论或步骤入口，不利于 AI 直接引用。",
                severity=SEV_HIGH,
                suggested_fix="在页面开头补一句“该产品/方案是什么、适合谁、关键参数/认证是什么”的可引用答案。",
                metric_status="untested",
            )
        )
    if _url_depth(page.path) > 4:
        out.append(
            Finding(
                category="crawl",
                title=FINDINGS["url_depth"][1],
                detail=f"当前 URL 深度为 {_url_depth(page.path)}，对用户浏览和抓取路径都偏深。",
                severity=SEV_LOW,
                suggested_fix="评估是否需要更短的产品/方案 URL，或从导航、分类页、相关文章增加入口。",
                metric_status="untested",
            )
        )
    if _b2b_page_like(page) and page.crawl_status != "needs_js":
        internal = (page.internal_links or "").lower()
        has_contact_path = any(token in internal for token in ("contact", "inquiry", "quote", "rfq"))
        weak_copy = bool(getattr(page, "word_count", 0) and page.word_count < 300)
        if weak_copy or not has_contact_path:
            missing = []
            if weak_copy:
                missing.append("正文/参数信息偏少")
            if not has_contact_path:
                missing.append("未发现明显询盘/联系入口内链")
            out.append(
                Finding(
                    category="b2b",
                    title=FINDINGS["b2b_product"][1],
                    detail="；".join(missing) + "。B2B 买家通常需要参数、应用、认证、案例和询盘路径。",
                    severity=SEV_HIGH,
                    suggested_fix="补齐产品参数、应用场景、认证/质检、案例、FAQ、MOQ/交期等待确认字段，并增加询盘入口。",
                    metric_status="untested",
                )
            )
    return out


def parse_internal_paths(internal_links: str) -> list[str]:
    paths: list[str] = []
    for raw in (internal_links or "").replace(",", "\n").splitlines():
        item = raw.strip().split()[0] if raw.strip() else ""
        if item.startswith("/") and not item.startswith("//"):
            paths.append(item.split("#")[0])
    return paths


def finding_key(finding: Finding) -> tuple[str, str]:
    return finding.category, finding.title


def reconcile_issues(
    db,
    *,
    tenant_id: str,
    page: SitePage,
    issues: list[OnsiteIssue],
) -> tuple[int, int, int]:
    """Create missing findings; refresh still-open detail; verify satisfied ones."""
    findings = analyze_page(page)
    by_key = {finding_key(f): f for f in findings}
    created = skipped = verified = 0
    existing_keys: set[tuple[str, str]] = set()
    for issue in issues:
        key = (issue.category, issue.title)
        existing_keys.add(key)
        if issue.status not in OPENISH:
            continue
        found = by_key.get(key)
        if found is None:
            issue.status = "verified"
            issue.detail = f"当前观察已满足「{issue.title}」。未把改稿写进观察层。"
            verified += 1
            continue
        issue.detail = found.detail
        issue.severity = found.severity
        skipped += 1
    for finding in findings:
        key = finding_key(finding)
        if key in existing_keys:
            continue
        db.add(
            OnsiteIssue(
                tenant_id=tenant_id,
                page_id=page.id,
                category=finding.category,
                title=finding.title,
                detail=finding.detail,
                proposed_change="",
                severity=finding.severity,
                risk=severity_to_risk(finding.severity),
                status="open",
                metric_status=finding.metric_status,
            )
        )
        existing_keys.add(key)
        created += 1
    page.analyzed_at = datetime.now(timezone.utc)
    return created, skipped, verified


def default_sev(category: str) -> str:
    return default_severity(category)
