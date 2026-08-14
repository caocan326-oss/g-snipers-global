"""GEO helpers. No live AI-engine calls; no invented citation rates.

Skeleton after public GeoLook flow (prompt set → sample → diagnosis →
tickets with acceptance → verify / reopen). Do not copy GeoLook code.
Citation ≠ absorption. brand.com cite rate stays 未测 until a human records.
"""

from __future__ import annotations

from app.models import GeoObservation, GeoPrompt, OnsiteIssue, SeoPage, SitePage, Tenant

WESTERN_ENGINES = ("chatgpt", "perplexity", "gemini", "claude")
CHINA_ENGINES = ("deepseek", "doubao", "kimi", "tongyi")
ENGINES = WESTERN_ENGINES + CHINA_ENGINES

ENGINE_LABELS = {
    "chatgpt": "ChatGPT",
    "perplexity": "Perplexity",
    "gemini": "Gemini",
    "claude": "Claude",
    "deepseek": "DeepSeek",
    "doubao": "豆包",
    "kimi": "Kimi",
    "tongyi": "通义",
}

CHECKLIST_DEFS = (
    ("author_visible", "作者与资质可见"),
    ("lead_answer", "开篇有可摘取的结论句"),
    ("sources_cited", "数据或主张有来源"),
    ("date_visible", "更新日期可见"),
    ("heading_hierarchy", "标题层级清楚（一节一题）"),
    ("faq_block", "有 FAQ / 问答结构"),
    ("primary_entity", "品牌或产品名称前后一致"),
)

OBS_STATUSES = {"untested", "mentioned", "not_mentioned", "cited"}
CHECK_STATUSES = {"untested", "pass", "fail"}

DIAGNOSES = {
    "untested": "未测",
    "absent": "未出现",
    "mentioned": "被提及",
    "competitor_dominated": "竞品主导",
    "suspected_negative": "疑似负面",
}

TICKET_STATUSES = {"open", "in_progress", "verify", "done", "reopened"}

# Low-risk drafts write into the workspace page; never a live HTTP publish.
CATEGORY_WORKSPACE_FIELD = {
    "tdk": "meta_description",
    "heading": "headings",
    "internal_link": "internal_links",
    "schema": "structured_data",
    "canonical": "canonical",
}


def build_llms_txt(tenant: Tenant, pages: list[SeoPage]) -> str:
    lines = [
        f"# {tenant.name}",
        "",
        "> 这是给客户经理改稿的 llms.txt 草稿，不是已发布文件，也不能证明任何模型引用了本站。",
        "",
    ]
    if not pages:
        lines.append("## Pages")
        lines.append("- （还没有选题。从站内改页登记页面后再生成。）")
        return "\n".join(lines) + "\n"

    by_locale: dict[str, list[SeoPage]] = {}
    for page in pages:
        by_locale.setdefault(page.locale, []).append(page)
    for locale, group in by_locale.items():
        lines.append(f"## {locale}")
        for page in group:
            slug = page.target_keyword.replace(" ", "-")[:48]
            lines.append(f"- [{page.title}](/{locale}/{slug}): {page.target_keyword}")
        lines.append("")
    return "\n".join(lines)


def engine_region(engine: str) -> str:
    return "western" if engine in WESTERN_ENGINES else "china"


def ensure_engine_slots(db, tenant_id: str, prompt: GeoPrompt) -> None:
    existing = {o.engine for o in prompt.observations}
    for engine in ENGINES:
        if engine not in existing:
            db.add(
                GeoObservation(
                    tenant_id=tenant_id,
                    prompt_id=prompt.id,
                    engine=engine,
                    status="untested",
                )
            )


def apply_proposed_change(page: SitePage, issue: OnsiteIssue) -> None:
    """Write the change draft onto workspace fields. Does not touch a live site."""
    text = (issue.proposed_change or "").strip()
    if not text:
        return
    field = CATEGORY_WORKSPACE_FIELD.get(issue.category)
    if field:
        setattr(page, field, text)
        return
    if issue.category in {"index", "crawl", "canonical"}:
        note = f"[已确认方案 · {issue.category}] {text}"
        page.notes = "\n".join(x for x in (page.notes or "", note) if x).strip()
