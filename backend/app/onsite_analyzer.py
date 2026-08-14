"""Workspace site audit. Structure after public crawlers (inventory →
severity-grouped issues). No live customer HTTP, no GSC, no Semrush clone.
Analysis never applies a change.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models import SitePage
from app.risk import CRITICAL, SEV_HIGH, SEV_LOW, default_severity

# Stable titles so re-analyze is idempotent per page + category + title.
FINDINGS = {
    "tdk_title": ("tdk", "缺少 Title", SEV_HIGH),
    "tdk_desc": ("tdk", "Description 过短或为空", SEV_LOW),
    "heading": ("heading", "缺少 H1", SEV_HIGH),
    "internal_link": ("internal_link", "缺少内链", SEV_LOW),
    "schema": ("schema", "缺少 JSON-LD / schema", CRITICAL),
    "index": ("index", "收录状态未测（需 GSC）", CRITICAL),
    "canonical": ("canonical", "Canonical 未登记", CRITICAL),
}


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


def analyze_page(page: SitePage) -> list[Finding]:
    """Read workspace fields only. Index/canonical stay 未测 without GSC."""
    out: list[Finding] = []
    if not (page.meta_title or "").strip():
        out.append(
            Finding(
                category="tdk",
                title=FINDINGS["tdk_title"][1],
                detail="工作区 Title 为空。分析只记问题，不改字段。",
                severity=SEV_HIGH,
                suggested_fix=f"{page.title} | 补 Title（工作区草稿）",
                metric_status="untested",
            )
        )
    desc = (page.meta_description or "").strip()
    if len(desc) < 40:
        out.append(
            Finding(
                category="tdk",
                title=FINDINGS["tdk_desc"][1],
                detail="Description 空或过短。无 GSC 展示数据，指标未测。",
                severity=SEV_LOW,
                suggested_fix=f"围绕「{page.title}」写 140–160 字符描述。",
                metric_status="untested",
            )
        )
    if not _has_h1(page.headings):
        out.append(
            Finding(
                category="heading",
                title=FINDINGS["heading"][1],
                detail="未见 H1。分析不会写入 headings。",
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
                detail="工作区内链为空。",
                severity=SEV_LOW,
                suggested_fix="补一条相关内链路径。",
                metric_status="untested",
            )
        )
    if not (page.structured_data or "").strip():
        out.append(
            Finding(
                category="schema",
                title=FINDINGS["schema"][1],
                detail="上线会改 HTML，属 critical。须改稿后再确认，分析不落稿。",
                severity=CRITICAL,
                suggested_fix='{"@context":"https://schema.org","@type":"WebPage"}',
                metric_status="untested",
            )
        )
    if (page.index_status or "untested") == "untested":
        out.append(
            Finding(
                category="index",
                title=FINDINGS["index"][1],
                detail="未接 GSC，不能填已收录或 0 页。",
                severity=CRITICAL,
                suggested_fix="有 Search Console 后再测。在此之前保持未测。",
                metric_status="untested",
            )
        )
    if not (getattr(page, "canonical", None) or "").strip():
        out.append(
            Finding(
                category="canonical",
                title=FINDINGS["canonical"][1],
                detail="Canonical 未写。无 GSC 不判断是否被选为规范 URL。",
                severity=CRITICAL,
                suggested_fix=page.path,
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


def default_sev(category: str) -> str:
    return default_severity(category)
