"""GEO closed loop: name a page or channel, retest the same question, record only the change.

Doing the work does not mean the next sample will mention the brand.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import GeoPrompt, GeoSampleResult, GeoSampleRun, GeoTicket, SitePage, SourcePlatform
from app.official_apis import OFFICIAL_APIS

HONEST_ACCEPTANCE = (
    "对应页已上线，或帖已发出；同一买家问题再抽查一次。"
    "抽查只记有没有变化：上次没有 → 这次有 / 这次仍没有。"
    "提到才算提到，不要求这次必须提到。"
)
HONEST_RETEST = "对同一买家问题再跑一轮联网抽查，记下提到、给出官网、只推竞品。结果只作记录，不作为完成条件。"
VERIFY_ACCEPTANCE = "打开抽查里给出的网址，记下能不能打开、是不是客户页。核对完再标已核验。不要求下一次抽查必须提到。"

_STOP = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "that",
    "this",
    "what",
    "which",
    "best",
    "should",
    "before",
    "after",
    "into",
    "your",
    "our",
    "how",
    "are",
    "was",
    "can",
    "not",
}

_CHANNEL_ORDER = (
    "linkedin_company",
    "x_twitter",
    "facebook_page",
    "instagram_business",
    "youtube_channel",
    "pinterest",
)


def short_prompt(text: str, limit: int = 28) -> str:
    value = " ".join((text or "").split())
    if len(value) <= limit:
        return value or "这个问题"
    return value[: limit - 1].rstrip() + "…"


def _json_list(raw: str) -> list[str]:
    try:
        data = json.loads(raw or "[]")
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [str(item) for item in data if str(item).strip()]


def _tokens(text: str) -> set[str]:
    found = re.findall(r"[a-z0-9\u4e00-\u9fff]{3,}", (text or "").lower())
    return {token for token in found if token not in _STOP}


def _owned(row: GeoSampleResult) -> bool:
    return bool(_json_list(row.owned_citations_json))


def _third_party(row: GeoSampleResult) -> bool:
    return bool(_json_list(row.third_party_citations_json))


def run_counts(run: GeoSampleRun | None) -> tuple[int, int, int, int]:
    results = list(getattr(run, "results", None) or [])
    return (
        len(results),
        sum(1 for row in results if row.mentioned),
        sum(1 for row in results if _owned(row)),
        sum(1 for row in results if _third_party(row)),
    )


def compare_runs_note(latest: GeoSampleRun | None, previous: GeoSampleRun | None) -> str:
    if latest is None or not getattr(latest, "results", None):
        return ""
    latest_n, latest_mentioned, latest_owned, _ = run_counts(latest)
    if previous is None or not getattr(previous, "results", None):
        return ""
    prev_n, prev_mentioned, prev_owned, _ = run_counts(previous)
    if prev_mentioned == 0 and latest_mentioned == 0:
        mention = f"上次抽查 {prev_n} 问都没提到；这次 {latest_n} 问仍没提到。"
    elif prev_mentioned == 0 and latest_mentioned > 0:
        mention = f"上次抽查都没提到；这次有 {latest_mentioned} 问提到了。"
    elif prev_mentioned > 0 and latest_mentioned == 0:
        mention = f"上次有 {prev_mentioned} 问提到；这次抽查没有提到。"
    else:
        mention = f"上次提到 {prev_mentioned}/{prev_n}；这次提到 {latest_mentioned}/{latest_n}。"
    if prev_owned == 0 and latest_owned == 0:
        owned = "两次都没有给出官网。"
    elif prev_owned == 0 and latest_owned > 0:
        owned = f"这次有 {latest_owned} 条给出了疑似官网，还要核对。"
    elif prev_owned > 0 and latest_owned == 0:
        owned = "这次没有给出官网。"
    else:
        owned = f"上次给出官网 {prev_owned} 条，这次 {latest_owned} 条。"
    return f"{mention}{owned}抽查变化只记事实，不写成已经稳定推荐。"


def compare_prompt_note(latest_rows: list[GeoSampleResult], previous_rows: list[GeoSampleResult]) -> str:
    curr_m = any(row.mentioned for row in latest_rows)
    curr_o = any(_owned(row) for row in latest_rows)
    if not previous_rows:
        mentioned = "这一次提到了。" if curr_m else "这一次没有提到。"
        owned = "给出了疑似官网，还要核对。" if curr_o else "没有给出官网。"
        return mentioned + owned
    prev_m = any(row.mentioned for row in previous_rows)
    prev_o = any(_owned(row) for row in previous_rows)
    if not prev_m and not curr_m:
        mention = "上次没有提到，这次仍没有提到。"
    elif not prev_m and curr_m:
        mention = "上次没有提到，这次提到了。"
    elif prev_m and not curr_m:
        mention = "上次提到了，这次没有提到。"
    else:
        mention = "上次提到了，这次也提到了。"
    if not prev_o and not curr_o:
        owned = "两次都没有给出官网。"
    elif not prev_o and curr_o:
        owned = "这次给出了疑似官网，还要核对。"
    elif prev_o and not curr_o:
        owned = "这次没有给出官网。"
    else:
        owned = "两次都有疑似官网。"
    return mention + owned


def suggest_page(db: Session, tenant_id: str, prompt_text: str) -> SitePage | None:
    pages = db.query(SitePage).filter(SitePage.tenant_id == tenant_id).all()
    if not pages:
        return None
    want = _tokens(prompt_text)
    ranked: list[tuple[int, int, SitePage]] = []
    for page in pages:
        hay = _tokens(f"{page.title} {page.path} {page.meta_title} {page.headings}")
        overlap = len(want & hay) if want else 0
        path = (page.path or "/").strip() or "/"
        home_penalty = 0 if path == "/" else 1
        ranked.append((overlap, home_penalty, page))
    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    best_overlap, _, best = ranked[0]
    if best_overlap > 0:
        return best
    return next((page for page in pages if (page.path or "/").strip() in {"", "/"}), pages[0])


def suggest_channel(db: Session, tenant_id: str) -> tuple[str, str]:
    rows = (
        db.query(SourcePlatform)
        .filter(SourcePlatform.tenant_id == tenant_id, SourcePlatform.status == "active")
        .all()
    )
    official = [row for row in rows if row.has_official_api or row.platform_key in OFFICIAL_APIS]
    pool = official or rows
    if not pool:
        return "站外分发里的一张渠道卡", "/offsite"

    def rank(row: SourcePlatform) -> tuple[int, str]:
        try:
            order = _CHANNEL_ORDER.index(row.platform_key)
        except ValueError:
            order = 99
        return (order, row.name or row.platform_key)

    pick = sorted(pool, key=rank)[0]
    return pick.name or pick.platform_key, "/offsite"


def page_label(page: SitePage | None) -> str:
    if page is None:
        return "还没有对应页，先补一页"
    title = page.title or page.meta_title or "未命名页面"
    path = page.path or "/"
    return f"{title}（{path}）"


def loop_ticket_spec(
    db: Session,
    tenant_id: str,
    prompt: GeoPrompt,
    kind: str,
    *,
    third_party: bool = False,
) -> dict:
    page = suggest_page(db, tenant_id, prompt.prompt_text)
    channel_name, _channel_href = suggest_channel(db, tenant_id)
    short = short_prompt(prompt.prompt_text)
    page_bit = page_label(page)
    titles = {
        "absent": f"买家问「{short}」时没提到我们",
        "no_owned": f"买家问「{short}」时提到了品牌，但没给出官网",
        "competitor": f"买家问「{short}」时先推了别人",
        "unverified": f"买家问「{short}」时给出的网址还没打开核对",
    }
    diagnoses = {
        "absent": "absent",
        "no_owned": "mentioned",
        "competitor": "competitor_dominated",
        "unverified": "mentioned",
    }
    actions = {
        "absent": f"先改 {page_bit}，把这个问题写清楚。同时在站外分发打开「{channel_name}」发出去。我们不代改线上、不代发。",
        "no_owned": f"在 {page_bit} 补可引用的事实和官网链接。也可以在「{channel_name}」发一条指向该页。我们不代发。",
        "competitor": f"在 {page_bit} 补对照说明。也可以在「{channel_name}」发出客户自己的说法。我们不代发。",
        "unverified": "打开抽查里给出的网址，记下能不能打开、是不是客户页。核对完再标已核验。",
    }
    rationale = f"对应页：{page_bit} · 渠道：{channel_name}"
    if third_party and kind == "absent":
        rationale += "。回答里出现了外来网址，没有我们。"
    return {
        "title": titles[kind],
        "diagnosis": diagnoses[kind],
        "rationale": rationale,
        "recommended_action": actions[kind],
        "acceptance_criteria": VERIFY_ACCEPTANCE if kind == "unverified" else HONEST_ACCEPTANCE,
        "retest_method": HONEST_RETEST,
        "priority": "P1" if kind in {"absent", "competitor"} else "P2",
        "owner_hint": "内容运营 / 客户经理",
        "evidence": {
            "kind": kind,
            "prompt_id": prompt.id,
            "page_id": page.id if page else "",
            "page_path": page.path if page else "",
            "channel": channel_name,
            "honest_loop": True,
        },
    }


def kinds_from_sample_rows(rows: list[GeoSampleResult]) -> list[str]:
    mentioned = any(row.mentioned for row in rows)
    owned = any(_owned(row) for row in rows)
    competitors = any((row.competitor_hits or "").strip() for row in rows)
    kinds: list[str] = []
    if not mentioned:
        kinds.append("absent")
    elif not owned:
        kinds.append("no_owned")
    if competitors:
        kinds.append("competitor")
    return kinds


def write_ticket_retest(
    db: Session,
    tenant_id: str,
    latest: GeoSampleRun | None,
    previous: GeoSampleRun | None,
) -> int:
    if latest is None or not getattr(latest, "results", None) or previous is None:
        return 0
    latest_by: dict[str, list[GeoSampleResult]] = {}
    previous_by: dict[str, list[GeoSampleResult]] = {}
    for row in latest.results:
        latest_by.setdefault(row.prompt_id, []).append(row)
    for row in getattr(previous, "results", None) or []:
        previous_by.setdefault(row.prompt_id, []).append(row)
    tickets = (
        db.query(GeoTicket)
        .filter(
            GeoTicket.tenant_id == tenant_id,
            GeoTicket.prompt_id.in_(list(latest_by)),
            ~GeoTicket.status.in_(["done", "closed", "ignored"]),
        )
        .all()
    )
    now = datetime.now(timezone.utc)
    updated = 0
    for ticket in tickets:
        ticket.retest_result = compare_prompt_note(latest_by.get(ticket.prompt_id, []), previous_by.get(ticket.prompt_id, []))
        ticket.last_checked_at = now
        updated += 1
    return updated


def geo_href(ticket: GeoTicket) -> str:
    try:
        payload = json.loads(ticket.evidence or "")
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, dict):
        page_id = str(payload.get("page_id") or "").strip()
        if page_id:
            return f"/onsite/{page_id}"
        if payload.get("channel"):
            return "/offsite"
    return "/geo"
