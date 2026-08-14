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

# Stable titles so re-analyze is idempotent per page + category + title.
FINDINGS = {
    "tdk_title": ("tdk", "缺少 Title", SEV_HIGH),
    "tdk_desc": ("tdk", "Description 过短或为空", SEV_LOW),
    "tdk_zh": ("tdk", "TDK 含中文", SEV_HIGH),
    "heading": ("heading", "缺少 H1", SEV_HIGH),
    "internal_link": ("internal_link", "缺少内链", SEV_LOW),
    "schema": ("schema", "缺少 JSON-LD / schema", CRITICAL),
    "index": ("index", "收录状态未测（需 GSC）", CRITICAL),
    "canonical": ("canonical", "Canonical 未登记", CRITICAL),
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
    if (page.index_status or "untested") == "untested":
        out.append(
            Finding(
                category="index",
                title=FINDINGS["index"][1],
                detail="未接 GSC，不能从 HTML 编已收录或 0 页。",
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
                detail="当前观察无 Canonical。无 GSC 不判断是否被选为规范 URL。",
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
