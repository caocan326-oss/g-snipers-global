"""GEO helpers. No live AI-engine calls; no invented citation rates."""

from app.models import SeoPage, Tenant

ENGINES = ("chatgpt", "perplexity", "gemini", "claude")

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


def build_llms_txt(tenant: Tenant, pages: list[SeoPage]) -> str:
    lines = [
        f"# {tenant.name}",
        "",
        "> 这是给客户经理改稿的 llms.txt 草稿，不是已发布文件，也不能证明任何模型引用了本站。",
        "",
    ]
    if not pages:
        lines.append("## Pages")
        lines.append("- （还没有选题。从 SEO 工作台产出页面后再生成。）")
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
