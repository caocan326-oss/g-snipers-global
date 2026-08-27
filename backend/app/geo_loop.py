"""GEO closed loop: name a page or channel, retest the same question, record only the change.

Doing the work does not mean the next sample will mention the brand.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.geo_citations import citation_host, classify_citation
from app.geo_helpers import ENGINE_LABELS
from app.models import (
    Competitor,
    FactPack,
    GeoObservation,
    GeoPrompt,
    GeoSampleResult,
    GeoSampleRun,
    GeoTicket,
    SitePage,
    SourcePlatform,
    Tenant,
)
from app.official_apis import OFFICIAL_APIS, official_api_for

HONEST_ACCEPTANCE = (
    "对应页已上线，或帖已发出；同一买家问题再抽查一次。"
    "抽查只记有没有变化：上次没有 → 这次有 / 这次仍没有。"
    "提到才算提到，不要求这次必须提到。"
)
HONEST_RETEST = "对同一买家问题再跑一轮联网抽查，记下提到、给出官网、只推竞品。结果只作记录，不作为完成条件。只有客户页已上线或帖已发出后才再测；工作台打勾不算官网已改。"
VERIFY_ACCEPTANCE = "打开抽查里给出的网址，记下能不能打开、是不是客户页。核对完再标已核验。不要求下一次抽查必须提到。"
HANDOFFS = ("drafted", "sent", "live")
HANDOFF_LABELS = {
    "drafted": "工作台已写改法，还没发给客户",
    "sent": "已把改法发给客户，客户页还没上线",
    "live": "客户说页已上线或帖已发出，可以再测同一问",
}
CUSTOMER_CLOSE = "我们不代改官网、不代发。改完告诉我，我再用同一问看一次。不保证这次被提到。"
_WORKBENCH_PHRASES = (
    "我们不代改官网、不代发。",
    "工作台打勾不算官网已改。",
    "工作台打勾不是官网已改。",
    "再测只记变化，不要求这次必须提到。",
    "我们不代改线上、不代发。",
)

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


def short_prompt(text: str, limit: int = 240) -> str:
    value = " ".join((text or "").split())
    if not value:
        return "这个问题"
    if len(value) <= limit:
        return value
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


# 博查常给中文购物页，不当成「海外源提到了却没官网」的开单依据。
_CN_LEAN_ENGINES = frozenset({"bocha"})


def _is_overseas_engine(engine: str) -> bool:
    return (engine or "").strip().lower() not in _CN_LEAN_ENGINES


def _overseas_rows(rows: list[GeoSampleResult]) -> list[GeoSampleResult]:
    return [row for row in rows if _is_overseas_engine(row.engine or "")]


def _mention_signal(rows: list[GeoSampleResult]) -> bool:
    """Retest / ticket gates: prefer overseas sources when the round has them."""
    overseas = _overseas_rows(rows)
    if overseas:
        return any(row.mentioned for row in overseas)
    return any(row.mentioned for row in rows)


def sample_reason_for_ticket(rows: list[GeoSampleResult], kind: str) -> str:
    if not rows:
        return ""
    split = mention_split_note(rows)
    if kind == "no_owned":
        return f"海外联网源提到了品牌，没有给出客户官网{split}"
    if kind == "absent":
        return f"这一轮联网源都没提到我们{split}"
    if kind == "competitor":
        return f"回答里先推了别人{split}"
    if kind == "unverified":
        if any(_owned(row) for row in rows):
            return f"抽查里有疑似官网，还没打开核对{split}"
        return f"给出的网址还没打开核对{split}"
    return split.strip("（）。") if split else ""


def run_counts(run: GeoSampleRun | None) -> tuple[int, int, int, int]:
    results = list(getattr(run, "results", None) or [])
    return (
        len(results),
        sum(1 for row in results if row.mentioned),
        sum(1 for row in results if _owned(row)),
        sum(1 for row in results if _third_party(row)),
    )


def summarize_runs(runs: list[GeoSampleRun] | None) -> tuple[int, int, int, int]:
    sampled = mentioned = owned = third = 0
    for run in runs or []:
        n, m, o, t = run_counts(run)
        sampled += n
        mentioned += m
        owned += o
        third += t
    return sampled, mentioned, owned, third


def _started(run: GeoSampleRun):
    return getattr(run, "started_at", None)


def same_sample_batch(left: GeoSampleRun, right: GeoSampleRun, window_sec: int = 180) -> bool:
    start_left, start_right = _started(left), _started(right)
    if start_left is None or start_right is None:
        return False
    return abs((start_left - start_right).total_seconds()) <= window_sec


def pick_sample_batches(runs_desc: list[GeoSampleRun]) -> tuple[list[GeoSampleRun], list[GeoSampleRun]]:
    nonempty = [run for run in runs_desc if getattr(run, "results", None)]
    if not nonempty:
        return [], []
    latest = nonempty[0]
    latest_batch = [run for run in nonempty if same_sample_batch(run, latest)]
    rest = [run for run in nonempty if run.id not in {item.id for item in latest_batch}]
    if not rest:
        return latest_batch, []
    previous = rest[0]
    previous_batch = [run for run in rest if same_sample_batch(run, previous)]
    return latest_batch, previous_batch


def compare_batches_note(latest_runs: list[GeoSampleRun], previous_runs: list[GeoSampleRun]) -> str:
    if not latest_runs:
        return ""
    latest_n, latest_mentioned, latest_owned, _ = summarize_runs(latest_runs)
    if not latest_n:
        return ""
    if not previous_runs:
        return ""
    prev_n, prev_mentioned, prev_owned, _ = summarize_runs(previous_runs)
    if not prev_n:
        return ""
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


def prompt_sample_verdict(rows: list[GeoSampleResult]) -> str:
    if not rows:
        return ""
    mentioned = any(row.mentioned for row in rows)
    owned = any(_owned(row) for row in rows)
    third = any(_third_party(row) for row in rows)
    split = mention_split_note(rows)
    if mentioned and owned:
        head = "联网抽查：有的源提到了品牌，并给出了疑似官网，还要核对。"
    elif mentioned:
        head = "联网抽查：有的源提到了品牌，没有给出官网。"
    elif third:
        head = "联网抽查：没提到我们，回答里是外来网址。"
    else:
        head = "联网抽查：没提到我们，也没有给出官网。"
    return f"{head}{split}"


def engine_label(engine: str) -> str:
    key = (engine or "").strip()
    return ENGINE_LABELS.get(key, key or "未知源")


def mention_split_note(rows: list[GeoSampleResult]) -> str:
    if not rows:
        return ""
    bits: list[str] = []
    for row in rows:
        label = engine_label(row.engine or "")
        if row.mentioned:
            bits.append(f"{label} 提到")
        else:
            bits.append(f"{label} 未提到")
    return "（" + "；".join(bits) + "。）"


def mention_split_for_runs(runs: list[GeoSampleRun]) -> str:
    rows: list[GeoSampleResult] = []
    for run in runs:
        rows.extend(list(getattr(run, "results", None) or []))
    return mention_split_note(rows)


def prompt_sample_tally(rows: list[GeoSampleResult], prompt: GeoPrompt | None = None) -> str:
    if not rows:
        return ""
    mentioned = sum(1 for row in rows if row.mentioned)
    note = f"{mentioned} / {len(rows)} 提到{mention_split_note(rows)}"
    caveat = overseas_source_note(rows, prompt)
    return f"{note}{caveat}" if caveat else note


def latest_prompt_rows(db: Session, tenant_id: str) -> dict[str, list[GeoSampleResult]]:
    recent = (
        db.query(GeoSampleRun)
        .options(selectinload(GeoSampleRun.results))
        .filter(GeoSampleRun.tenant_id == tenant_id)
        .order_by(GeoSampleRun.started_at.desc())
        .limit(12)
        .all()
    )
    latest, _previous = pick_sample_batches(recent)
    by_prompt: dict[str, list[GeoSampleResult]] = {}
    for run in latest:
        for row in list(getattr(run, "results", None) or []):
            by_prompt.setdefault(row.prompt_id, []).append(row)
    return by_prompt


def compare_runs_note(latest: GeoSampleRun | None, previous: GeoSampleRun | None) -> str:
    return compare_batches_note([latest] if latest else [], [previous] if previous else [])


def _as_runs(value: GeoSampleRun | list[GeoSampleRun] | None) -> list[GeoSampleRun]:
    if value is None:
        return []
    if isinstance(value, list):
        return [run for run in value if run is not None]
    return [value]


def compare_prompt_note(latest_rows: list[GeoSampleResult], previous_rows: list[GeoSampleResult]) -> str:
    # Only mention + owned. Shop-page counts are not visibility.
    curr_m = _mention_signal(latest_rows)
    curr_o = any(_owned(row) for row in latest_rows)
    if not previous_rows:
        mentioned = "这一次提到了。" if curr_m else "这一次没有提到。"
        owned = "给出了疑似官网，还要核对。" if curr_o else "没有给出官网。"
        return mentioned + owned
    prev_m = _mention_signal(previous_rows)
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


RECORDED_FROM_LABELS = {
    "sales": "销售听到的",
    "inquiry": "询盘里的",
    "exhibition": "展会听到的",
    "customer": "客户自己说的",
    "": "已记原句",
}
RECORDED_FROM = set(RECORDED_FROM_LABELS)


def recorded_from_label(value: str) -> str:
    return RECORDED_FROM_LABELS.get((value or "").strip(), "已记原句")


WATCH_INTERVAL_DAYS = 7


def last_sampled_at_by_prompt(db: Session, tenant_id: str) -> dict[str, datetime]:
    rows = (
        db.query(GeoSampleResult.prompt_id, func.max(GeoSampleResult.sampled_at))
        .filter(GeoSampleResult.tenant_id == tenant_id)
        .group_by(GeoSampleResult.prompt_id)
        .all()
    )
    found: dict[str, datetime] = {}
    for prompt_id, sampled_at in rows:
        if sampled_at is None:
            continue
        found[prompt_id] = sampled_at if sampled_at.tzinfo else sampled_at.replace(tzinfo=timezone.utc)
    return found


def watch_state(last_sampled: datetime | None, *, now: datetime | None = None, interval_days: int = WATCH_INTERVAL_DAYS) -> dict:
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    if last_sampled is None:
        return {
            "due": True,
            "last_sampled_at": None,
            "next_watch_at": current,
            "note": "还没抽过。记下后就算进常驻监控。到期该复测。不保证这次被提到。",
        }
    sampled = last_sampled if last_sampled.tzinfo else last_sampled.replace(tzinfo=timezone.utc)
    next_at = sampled + timedelta(days=interval_days)
    if current >= next_at:
        return {
            "due": True,
            "last_sampled_at": sampled,
            "next_watch_at": current,
            "note": f"上次抽查已过 {interval_days} 天，到期该复测。不保证这次被提到。",
        }
    return {
        "due": False,
        "last_sampled_at": sampled,
        "next_watch_at": next_at,
        "note": f"常驻监控中。下次复测大约 {next_at.date().isoformat()}。不保证这次被提到。",
    }


def due_watch_prompts(db: Session, tenant_id: str, *, now: datetime | None = None) -> list[GeoPrompt]:
    prompts = (
        db.query(GeoPrompt)
        .filter(GeoPrompt.tenant_id == tenant_id)
        .order_by(GeoPrompt.created_at.desc())
        .all()
    )
    last_by = last_sampled_at_by_prompt(db, tenant_id)
    return [prompt for prompt in prompts if watch_state(last_by.get(prompt.id), now=now)["due"]]


def rows_by_prompt(runs: list[GeoSampleRun]) -> dict[str, list[GeoSampleResult]]:
    grouped: dict[str, list[GeoSampleResult]] = {}
    for run in runs:
        for row in list(getattr(run, "results", None) or []):
            grouped.setdefault(row.prompt_id, []).append(row)
    return grouped


def prompt_batch_rows(db: Session, tenant_id: str) -> tuple[dict[str, list[GeoSampleResult]], dict[str, list[GeoSampleResult]]]:
    recent = (
        db.query(GeoSampleRun)
        .options(selectinload(GeoSampleRun.results))
        .filter(GeoSampleRun.tenant_id == tenant_id)
        .order_by(GeoSampleRun.started_at.desc())
        .limit(12)
        .all()
    )
    latest, previous = pick_sample_batches(recent)
    return rows_by_prompt(latest), rows_by_prompt(previous)


def prompt_compare_note_for(prompt_id: str, latest_by: dict[str, list[GeoSampleResult]], previous_by: dict[str, list[GeoSampleResult]]) -> str:
    latest_rows = latest_by.get(prompt_id) or []
    if not latest_rows:
        return "还没联网抽查。"
    return compare_prompt_note(latest_rows, previous_by.get(prompt_id) or [])


def _citation_hosts(rows: list[GeoSampleResult]) -> list[str]:
    hosts: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for url in _json_list(row.third_party_citations_json):
            host = urlparse(url).netloc.lower().removeprefix("www.")
            if host and host not in seen:
                seen.add(host)
                hosts.append(host)
    return hosts[:3]


def prompt_trend_points(db: Session, tenant_id: str, prompt_id: str) -> list[dict]:
    runs = (
        db.query(GeoSampleRun)
        .options(selectinload(GeoSampleRun.results))
        .filter(GeoSampleRun.tenant_id == tenant_id)
        .order_by(GeoSampleRun.started_at.asc())
        .all()
    )
    usable = [run for run in runs if any(row.prompt_id == prompt_id for row in list(getattr(run, "results", None) or []))]
    batches: list[list[GeoSampleRun]] = []
    used: set[str] = set()
    for run in usable:
        if run.id in used:
            continue
        batch = [item for item in usable if item.id not in used and same_sample_batch(item, run)]
        used.update(item.id for item in batch)
        if batch:
            batches.append(batch)
    points: list[dict] = []
    for batch in batches[-8:]:
        rows = [row for run in batch for row in list(getattr(run, "results", None) or []) if row.prompt_id == prompt_id]
        mentioned = _mention_signal(rows)
        started = min((run.started_at for run in batch if run.started_at), default=None)
        points.append(
            {
                "at": started.isoformat() if started else "",
                "mentioned": mentioned,
                "owned": any(_owned(row) for row in rows),
                "note": "提到了" if mentioned else "没提到",
                "others": _citation_hosts(rows),
            }
        )
    return points


def trend_note(points: list[dict]) -> str:
    if not points:
        return "还没有抽查记录，谈不上趋势。"
    marks = " · ".join(str(point.get("note") or "没提到") for point in points)
    return f"{len(points)} 轮：{marks}。不保证下一轮会提到。"


FACT_PACK_BLOCK = "没有 Fact Pack（已批英文说明 + 官网）不能出对外草稿。不要编规格。"


def load_fact_pack(db: Session, tenant: Tenant | None) -> FactPack | None:
    if tenant is None:
        return None
    approved = (
        db.query(FactPack)
        .filter(FactPack.tenant_id == tenant.id, FactPack.status == "approved")
        .order_by(FactPack.updated_at.desc())
        .first()
    )
    if approved is not None:
        return approved
    return (
        db.query(FactPack)
        .filter(FactPack.tenant_id == tenant.id)
        .order_by(FactPack.updated_at.desc())
        .first()
    )


def fact_pack_ready(fact: FactPack | None, tenant: Tenant | None = None) -> bool:
    if fact is None or (fact.status or "") != "approved":
        return False
    boiler = (fact.approved_boilerplate_en or "").strip()
    website = (fact.website or (tenant.site_origin if tenant else "") or "").strip()
    return bool(boiler) and bool(website)


def fact_pack_phase(fact: FactPack | None, tenant: Tenant | None = None) -> str:
    """missing | draft | ready. Draft cannot unlock outbound page copy."""
    if fact_pack_ready(fact, tenant):
        return "ready"
    if fact is None:
        return "missing"
    filled = any(
        (part or "").strip()
        for part in (
            fact.approved_boilerplate_en,
            fact.website,
            fact.legal_name,
            fact.brand_names,
        )
    )
    return "draft" if filled else "missing"


def page_draft_for_prompt(db: Session, tenant: Tenant | None, prompt: GeoPrompt) -> str:
    fact = load_fact_pack(db, tenant)
    if not fact_pack_ready(fact, tenant):
        return FACT_PACK_BLOCK
    brand = (tenant.name if tenant else "") or "this company"
    website = ((tenant.site_origin if tenant else "") or "").rstrip("/")
    cats = boiler = specs = certs = ""
    if fact is not None:
        names = [part.strip() for part in (fact.brand_names or "").split(",") if part.strip()]
        brand = names[0] if names else (fact.legal_name or brand)
        website = (fact.website or website).rstrip("/")
        cats = (fact.product_categories_en or "").strip()
        boiler = (fact.approved_boilerplate_en or "").strip()
        specs = (fact.key_specs or "").strip()
        certs = (fact.certifications or "").strip()
    page = suggest_page(db, tenant.id, prompt.prompt_text) if tenant is not None else None
    path = (page.path if page else "/") or "/"
    url = f"{website}{path}" if website else ""
    lines = [
        f'Buyers ask: "{(prompt.prompt_text or "").strip()}"',
        f"{brand} official website: {website or '[NEED_INPUT: website]'}",
    ]
    if cats:
        lines.append(f"What we supply: {cats}")
    if boiler:
        lines.append(boiler)
    else:
        lines.append("[NEED_INPUT: approved English description. Do not invent specs.]")
    if specs:
        lines.append(f"Public specs: {specs}")
    if certs:
        lines.append(f"Public certifications: {certs}")
    if url:
        lines.append(f"Read more: {url}")
    lines.append("Paste this onto the matching page. We do not edit the live site. Same question will be sampled again. Mention is not guaranteed.")
    return "\n".join(lines)


def cite_pack_for_prompt(db: Session, tenant: Tenant | None, prompt: GeoPrompt) -> dict[str, str]:
    fact = load_fact_pack(db, tenant)
    if not fact_pack_ready(fact, tenant):
        return {"page_draft": FACT_PACK_BLOCK, "faq_draft": "", "llms_txt": ""}
    page_draft = page_draft_for_prompt(db, tenant, prompt)
    brand = (tenant.name if tenant else "") or "this company"
    website = ((tenant.site_origin if tenant else "") or "").rstrip("/")
    boiler = ""
    if fact is not None:
        names = [part.strip() for part in (fact.brand_names or "").split(",") if part.strip()]
        brand = names[0] if names else (fact.legal_name or brand)
        website = (fact.website or website).rstrip("/")
        boiler = (fact.approved_boilerplate_en or "").strip()
    question = (prompt.prompt_text or "").strip()
    answer = boiler or "[NEED_INPUT: approved English answer. Do not invent specs.]"
    faq_draft = "\n".join(
        [
            f"Q: {question}",
            f"A: {answer}",
            f"Official page: {website or '[NEED_INPUT: website]'}",
            "Publish this FAQ on the matching page. We do not edit the live site.",
        ]
    )
    llms_txt = "\n".join(
        [
            f"# {brand}",
            website or "[NEED_INPUT: website]",
            boiler or "[NEED_INPUT: approved English description. Do not invent specs.]",
            "",
            "# Buyer questions we can answer with public facts",
            f"- {question}" if question else "- [NEED_INPUT: recorded buyer question]",
            "",
            "# Note",
            "Only recorded facts. Mention in AI answers is not guaranteed.",
        ]
    )
    return {"page_draft": page_draft, "faq_draft": faq_draft, "llms_txt": llms_txt}


CITE_STAGES = ("draft", "sent", "published")
CITE_STAGE_LABELS = {
    "draft": "草稿已出，还没把这段发给客户",
    "sent": "已把这段发给客户，客户还没贴上",
    "published": "客户说已贴上，可以用同一问再测",
}
CITE_LOOP_CLOSE = "请自己贴到对应页。我们不代改。贴完告诉我，我再用同一问看一次。不保证这次被提到。"


def cite_stage(prompt: GeoPrompt) -> str:
    value = (getattr(prompt, "cite_stage", "") or "draft").strip()
    return value if value in CITE_STAGES else "draft"


def cite_stage_label(value: str) -> str:
    return CITE_STAGE_LABELS.get((value or "").strip(), CITE_STAGE_LABELS["draft"])


def cite_published_url(prompt: GeoPrompt) -> str:
    return (getattr(prompt, "cite_published_url", "") or "").strip()


def cite_paste_for_prompt(pack: dict[str, str], prompt: GeoPrompt | None = None) -> str:
    page = (pack.get("page_draft") or "").strip()
    if page == FACT_PACK_BLOCK:
        return FACT_PACK_BLOCK
    question = ((prompt.prompt_text if prompt is not None else "") or "").strip()
    parts = [CITE_LOOP_CLOSE]
    if question:
        parts.append(f'Buyers ask: "{question}"')
    faq = (pack.get("faq_draft") or "").strip()
    llms = (pack.get("llms_txt") or "").strip()
    if page:
        parts.append(page)
    if faq:
        parts.append(faq)
    if llms:
        parts.append(llms)
    return "\n\n".join(parts)


def set_cite_stage(prompt: GeoPrompt, stage: str, published_url: str = "") -> None:
    if stage not in CITE_STAGES:
        raise ValueError("cite_stage")
    url = (published_url or cite_published_url(prompt) or "").strip()
    if stage == "published":
        if not is_http_url(url):
            raise ValueError("published_url")
        prompt.cite_published_url = url
    elif stage == "draft":
        prompt.cite_published_url = ""
    elif url and is_http_url(url):
        prompt.cite_published_url = url
    prompt.cite_stage = stage


def competitor_note(rows: list[GeoSampleResult]) -> str:
    names: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for part in (row.competitor_hits or "").replace(";", ",").split(","):
            name = part.strip()
            key = name.lower()
            if name and key not in seen:
                seen.add(key)
                names.append(name)
    others = _citation_hosts(rows)
    bits: list[str] = []
    if names:
        bits.append("同一问里还出现了：" + "、".join(names[:4]))
    if others:
        bits.append("AI 引用的外来站：" + "、".join(others))
    if not bits:
        return ""
    return "。".join(bits) + "。不是我们编的竞品名单。"


SOURCE_KIND_LABELS = {
    "owned": "客户官网",
    "marketplace": "购物站",
    "competitor": "竞品站",
    "other": "第三方",
}


def _urls_from_text(text: str) -> list[str]:
    found: list[str] = []
    for part in re.split(r"[\s,，;；]+", text or ""):
        value = part.strip().strip(").,]>\"'")
        if value.startswith("http://") or value.startswith("https://"):
            found.append(value)
    return found


def _name_parts(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"[\n,，;；|/]+", text or "") if part.strip()]


def _empty_trust_map(note: str) -> dict:
    return {
        "sources": [],
        "competitors": [],
        "owned_hits": 0,
        "other_hits": 0,
        "marketplace_hits": 0,
        "competitor_site_hits": 0,
        "note": note,
        "empty": True,
        "prompts": [],
        "rounds": [],
        "compare_note": "",
    }


def _result_urls(row: GeoSampleResult) -> list[str]:
    return (
        _json_list(row.owned_citations_json)
        + _json_list(row.third_party_citations_json)
        + _json_list(row.citations_json)
    )


def _classify_host(url: str, root: str, competitor_hosts: dict[str, str]) -> tuple[str, str]:
    host = citation_host(url)
    if not host:
        return "", ""
    kind = "competitor" if host in competitor_hosts else classify_citation(url, root)
    return host, kind


def _slice_from_rows(
    rows: list[GeoSampleResult],
    *,
    root: str,
    competitor_hosts: dict[str, str],
    own_names: set[str],
    registered_names: dict[str, str],
    label: str,
) -> dict:
    hosts: list[str] = []
    owned_hosts: list[str] = []
    other_hosts: list[str] = []
    names: list[str] = []
    seen_h: set[str] = set()
    seen_n: set[str] = set()
    for row in rows:
        for url in _result_urls(row):
            host, kind = _classify_host(url, root, competitor_hosts)
            if not host or host in seen_h:
                continue
            seen_h.add(host)
            hosts.append(host)
            if kind == "owned":
                owned_hosts.append(host)
            else:
                other_hosts.append(host)
        for raw in _name_parts(row.competitor_hits or ""):
            if raw.lower() in own_names:
                continue
            key = raw.lower()
            if key in seen_n:
                continue
            seen_n.add(key)
            names.append(registered_names.get(key, raw))
    started = None
    for row in rows:
        sampled = getattr(row, "sampled_at", None)
        if sampled and (started is None or sampled < started):
            started = sampled
    return {
        "label": label,
        "at": started.isoformat() if started else "",
        "mentioned": any(row.mentioned for row in rows),
        "owned": any(_owned(row) for row in rows),
        "hosts": hosts[:8],
        "owned_hosts": owned_hosts[:8],
        "other_hosts": other_hosts[:8],
        "competitors": names[:8],
        "sampled": len(rows),
        "mentioned_count": sum(1 for row in rows if row.mentioned),
    }


def _compare_slices(latest: dict | None, previous: dict | None) -> str:
    if not latest:
        return "还没抽查引用。不会编来源。"
    if not previous:
        return "只有一轮抽查，还不能对照。不保证这次被提到。"
    bits: list[str] = []
    if latest["mentioned"] and not previous["mentioned"]:
        bits.append("这一轮提到了，上一轮没有。")
    elif not latest["mentioned"] and previous["mentioned"]:
        bits.append("这一轮没提到，上一轮提到了。")
    elif latest["mentioned"] and previous["mentioned"]:
        bits.append("两轮都提到了。")
    else:
        bits.append("两轮都没提到。")
    latest_h = list(latest.get("hosts") or [])
    previous_h = list(previous.get("hosts") or [])
    appeared = [host for host in latest_h if host not in previous_h]
    missing = [host for host in previous_h if host not in latest_h]
    if appeared:
        bits.append("新出现：" + "、".join(appeared[:4]) + "。")
    if missing:
        bits.append("这一轮没再出现：" + "、".join(missing[:4]) + "。")
    if latest_h and not appeared and not missing:
        bits.append("引用的站没变。")
    latest_c = list(latest.get("competitors") or [])
    previous_c = list(previous.get("competitors") or [])
    new_c = [name for name in latest_c if name not in previous_c]
    if new_c:
        bits.append("新提到：" + "、".join(new_c[:3]) + "。")
    return "".join(bits) + "不保证这次被提到。"


def trust_map_for_tenant(db: Session, tenant_id: str, tenant: Tenant | None = None) -> dict:
    """Who AI cited / named. Empty if there is no recorded sample. Never invents sources."""
    tenant = tenant or db.get(Tenant, tenant_id)
    root = (tenant.site_origin if tenant else "") or ""
    own_names: set[str] = set()
    if tenant and tenant.name:
        own_names.add(tenant.name.strip().lower())
    if root:
        host = citation_host(root)
        if host:
            own_names.add(host)
            own_names.add(host.split(".")[0])

    registered = db.query(Competitor).filter(Competitor.tenant_id == tenant_id).all()
    registered_names = {row.name.strip().lower(): row.name for row in registered if (row.name or "").strip()}
    competitor_hosts = {
        citation_host(row.website): row.name for row in registered if (row.website or "").strip()
    }

    prompt_rows = db.query(GeoPrompt).filter(GeoPrompt.tenant_id == tenant_id).all()
    if not prompt_rows:
        return _empty_trust_map("没有原句，没有信任源地图。不会编来源，不编竞品。")

    prompts = {row.id: row.prompt_text for row in prompt_rows}
    sources: dict[str, dict] = {}
    competitors: dict[str, dict] = {}

    def add_url(url: str, prompt_id: str) -> None:
        value = (url or "").strip()
        if not value:
            return
        host = citation_host(value)
        if not host:
            return
        kind = "competitor" if host in competitor_hosts else classify_citation(value, root)
        bucket = sources.setdefault(
            host,
            {
                "host": host,
                "kind": kind,
                "kind_label": SOURCE_KIND_LABELS.get(kind, SOURCE_KIND_LABELS["other"]),
                "hits": 0,
                "prompt_ids": set(),
                "sample_url": value,
                "sample_prompt": prompts.get(prompt_id, ""),
            },
        )
        bucket["hits"] += 1
        bucket["prompt_ids"].add(prompt_id)
        rank = {"owned": 3, "competitor": 2, "marketplace": 1, "other": 0}
        if rank.get(kind, 0) > rank.get(bucket["kind"], 0):
            bucket["kind"] = kind
            bucket["kind_label"] = SOURCE_KIND_LABELS.get(kind, SOURCE_KIND_LABELS["other"])

    def add_competitor(name: str, prompt_id: str) -> None:
        raw = (name or "").strip()
        if not raw or raw.lower() in own_names:
            return
        key = raw.lower()
        bucket = competitors.setdefault(
            key,
            {
                "name": registered_names.get(key, raw),
                "hits": 0,
                "prompt_ids": set(),
                "registered": key in registered_names,
                "sample_prompt": prompts.get(prompt_id, ""),
            },
        )
        bucket["hits"] += 1
        bucket["prompt_ids"].add(prompt_id)

    results = db.query(GeoSampleResult).filter(GeoSampleResult.tenant_id == tenant_id).all()
    sampled_ids = {row.prompt_id for row in results}
    observations = db.query(GeoObservation).filter(GeoObservation.tenant_id == tenant_id).all()
    for obs in observations:
        if obs.prompt_id in sampled_ids:
            continue
        for url in _urls_from_text(obs.citation_urls or ""):
            add_url(url, obs.prompt_id)
        for name in _name_parts(obs.competitor_mentions or ""):
            add_competitor(name, obs.prompt_id)
    for row in results:
        for url in _result_urls(row):
            add_url(url, row.prompt_id)
        for name in _name_parts(row.competitor_hits or ""):
            add_competitor(name, row.prompt_id)

    source_rows = []
    owned_hits = other_hits = marketplace_hits = competitor_site_hits = 0
    for item in sorted(sources.values(), key=lambda row: (-row["hits"], row["host"])):
        kind = item["kind"]
        hits = item["hits"]
        if kind == "owned":
            owned_hits += hits
        elif kind == "marketplace":
            marketplace_hits += hits
        elif kind == "competitor":
            competitor_site_hits += hits
        else:
            other_hits += hits
        source_rows.append(
            {
                "host": item["host"],
                "kind": kind,
                "kind_label": item["kind_label"],
                "hits": hits,
                "prompt_count": len(item["prompt_ids"]),
                "sample_url": item["sample_url"],
                "sample_prompt": item["sample_prompt"],
            }
        )

    competitor_rows = [
        {
            "name": item["name"],
            "hits": item["hits"],
            "prompt_count": len(item["prompt_ids"]),
            "registered": item["registered"],
            "sample_prompt": item["sample_prompt"],
        }
        for item in sorted(competitors.values(), key=lambda row: (-row["hits"], row["name"].lower()))
    ]

    empty = not source_rows and not competitor_rows
    if empty:
        note = "已记问句，还没有抽查引用。不会编来源，不编竞品。"
    else:
        bits = []
        if owned_hits:
            bits.append(f"客户官网出现 {owned_hits} 次")
        if other_hits:
            bits.append(f"第三方 {other_hits} 次")
        if marketplace_hits:
            bits.append(f"购物站 {marketplace_hits} 次")
        if competitor_site_hits:
            bits.append(f"竞品站 {competitor_site_hits} 次")
        if competitor_rows:
            bits.append(f"提到竞品 {len(competitor_rows)} 家")
        note = "；".join(bits) + "。只记抽查里出现的，不保证这次被提到。"

    latest_by, previous_by = prompt_batch_rows(db, tenant_id)
    prompt_out: list[dict] = []
    for prompt in prompt_rows:
        latest_rows = latest_by.get(prompt.id) or []
        previous_rows = previous_by.get(prompt.id) or []
        latest_slice = (
            _slice_from_rows(
                latest_rows,
                root=root,
                competitor_hosts=competitor_hosts,
                own_names=own_names,
                registered_names=registered_names,
                label="这一轮",
            )
            if latest_rows
            else None
        )
        previous_slice = (
            _slice_from_rows(
                previous_rows,
                root=root,
                competitor_hosts=competitor_hosts,
                own_names=own_names,
                registered_names=registered_names,
                label="上一轮",
            )
            if previous_rows
            else None
        )
        if latest_slice is None and not any(
            (obs.prompt_id == prompt.id and ((obs.citation_urls or "").strip() or (obs.competitor_mentions or "").strip()))
            for obs in observations
        ):
            continue
        if latest_slice is None:
            obs_rows = [obs for obs in observations if obs.prompt_id == prompt.id]
            hosts: list[str] = []
            names: list[str] = []
            for obs in obs_rows:
                for url in _urls_from_text(obs.citation_urls or ""):
                    host, _kind = _classify_host(url, root, competitor_hosts)
                    if host and host not in hosts:
                        hosts.append(host)
                for raw in _name_parts(obs.competitor_mentions or ""):
                    if raw.lower() not in own_names and raw not in names:
                        names.append(raw)
            latest_slice = {
                "label": "已记观察",
                "at": "",
                "mentioned": any((obs.status or "") in {"mentioned", "cited", "verified"} for obs in obs_rows),
                "owned": any(classify_citation(url, root) == "owned" for obs in obs_rows for url in _urls_from_text(obs.citation_urls or "")),
                "hosts": hosts[:8],
                "owned_hosts": [host for host in hosts if classify_citation(f"https://{host}", root) == "owned"][:8],
                "other_hosts": [host for host in hosts if classify_citation(f"https://{host}", root) != "owned"][:8],
                "competitors": names[:8],
                "sampled": len(obs_rows),
                "mentioned_count": 1 if any((obs.status or "") in {"mentioned", "cited", "verified"} for obs in obs_rows) else 0,
            }
        prompt_out.append(
            {
                "prompt_id": prompt.id,
                "prompt_text": prompt.prompt_text,
                "latest": latest_slice,
                "previous": previous_slice,
                "compare": _compare_slices(latest_slice, previous_slice),
            }
        )
        if len(prompt_out) >= 8:
            break

    recent = (
        db.query(GeoSampleRun)
        .options(selectinload(GeoSampleRun.results))
        .filter(GeoSampleRun.tenant_id == tenant_id)
        .order_by(GeoSampleRun.started_at.desc())
        .limit(12)
        .all()
    )
    latest_batch, previous_batch = pick_sample_batches(recent)
    rounds: list[dict] = []
    for batch, label in ((previous_batch, "上一轮"), (latest_batch, "这一轮")):
        if not batch:
            continue
        rows = [row for run in batch for row in list(getattr(run, "results", None) or [])]
        if not rows:
            continue
        slice_row = _slice_from_rows(
            rows,
            root=root,
            competitor_hosts=competitor_hosts,
            own_names=own_names,
            registered_names=registered_names,
            label=label,
        )
        started = min((run.started_at for run in batch if run.started_at), default=None)
        slice_row["at"] = started.isoformat() if started else slice_row["at"]
        rounds.append(slice_row)
    latest_round = next((row for row in rounds if row["label"] == "这一轮"), None)
    previous_round = next((row for row in rounds if row["label"] == "上一轮"), None)
    compare_note = _compare_slices(latest_round, previous_round) if latest_round else ""

    return {
        "sources": source_rows[:12],
        "competitors": competitor_rows[:12],
        "owned_hits": owned_hits,
        "other_hits": other_hits,
        "marketplace_hits": marketplace_hits,
        "competitor_site_hits": competitor_site_hits,
        "note": note,
        "empty": empty,
        "prompts": prompt_out,
        "rounds": rounds,
        "compare_note": compare_note if not empty else "",
    }


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


def suggest_channel(db: Session, tenant_id: str) -> tuple[str, str, str]:
    rows = (
        db.query(SourcePlatform)
        .filter(SourcePlatform.tenant_id == tenant_id, SourcePlatform.status == "active")
        .all()
    )
    official = [row for row in rows if row.has_official_api or row.platform_key in OFFICIAL_APIS]
    pool = official or rows
    if not pool:
        return "", "", ""

    def rank(row: SourcePlatform) -> tuple[int, str]:
        try:
            order = _CHANNEL_ORDER.index(row.platform_key)
        except ValueError:
            order = 99
        return (order, row.name or row.platform_key)

    verified = [row for row in pool if is_http_url((row.profile_url or "").strip())]
    if not verified:
        return "", "", ""
    pick = sorted(verified, key=rank)[0]
    return pick.name or pick.platform_key, pick.platform_key or "", "/offsite"


_PLACE_LEAKS = (
    "Shanghai, Xiamen, Chengdu",
    "Xiamen, Chengdu",
    "厦门、成都",
    "厦门成都",
    "厦门",
    "成都",
    "Xiamen",
    "Chengdu",
)


def clean_public_title(title: str) -> str:
    text = title or ""
    for mark in _PLACE_LEAKS:
        text = text.replace(mark, "")
    text = re.sub(r"\s*[|｜]\s*", " | ", text)
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"[\s|｜,.-]+$", "", text)
    return text.strip()


def page_label(page: SitePage | None) -> str:
    if page is None:
        return "还没有对应页，先补一页"
    title = clean_public_title(page.title or page.meta_title or "未命名页面") or "官网页面"
    path = page.path or "/"
    return f"{title}（{path}）"


def page_url(db: Session, tenant_id: str, page: SitePage | None) -> str:
    tenant = db.get(Tenant, tenant_id)
    origin = ((tenant.site_origin if tenant else "") or "").rstrip("/")
    path = (page.path if page else "/") or "/"
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{origin}{path}" if origin else path


def _english_buyer_question(prompt: GeoPrompt | None) -> bool:
    if prompt is None:
        return False
    locale = (prompt.locale or "").lower()
    if locale.startswith("en"):
        return True
    text = prompt.prompt_text or ""
    letters = len(re.findall(r"[A-Za-z]", text))
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    return letters >= 12 and letters > cjk


def overseas_source_note(rows: list[GeoSampleResult], prompt: GeoPrompt | None) -> str:
    if not rows or not _english_buyer_question(prompt):
        return ""
    if any((row.engine or "") == "bocha" for row in rows):
        return "博查这条按中文网页看，不写成海外 AI 结论。"
    return ""


def parse_ticket_evidence(ticket: GeoTicket) -> dict:
    try:
        data = json.loads(ticket.evidence or "")
    except json.JSONDecodeError:
        data = None
    return data if isinstance(data, dict) else {}


def ticket_handoff(ticket: GeoTicket) -> str:
    value = str(parse_ticket_evidence(ticket).get("handoff") or "drafted")
    return value if value in HANDOFFS else "drafted"


def is_http_url(url: str) -> bool:
    parsed = urlparse((url or "").strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def ticket_live_url(ticket: GeoTicket) -> str:
    return str(parse_ticket_evidence(ticket).get("live_url") or "").strip()


def ticket_offsite_url(ticket: GeoTicket) -> str:
    return str(parse_ticket_evidence(ticket).get("offsite_url") or "").strip()


def ticket_channel_key(ticket: GeoTicket) -> str:
    ev = parse_ticket_evidence(ticket)
    key = str(ev.get("channel_key") or "").strip()
    if key in OFFICIAL_APIS:
        return key
    name = str(ev.get("channel") or "").strip()
    if not name:
        return ""
    blob = f"{name} {key}".lower()
    for api_key, spec in OFFICIAL_APIS.items():
        if api_key.replace("_", " ") in blob or spec.label.lower() in blob:
            return api_key
    if "linkedin" in blob:
        return "linkedin_company"
    return ""


def verified_channel_or_blank(db: Session, tenant_id: str, stored: str) -> str:
    name = (stored or "").strip()
    if not name or not tenant_id:
        return ""
    rows = (
        db.query(SourcePlatform)
        .filter(SourcePlatform.tenant_id == tenant_id, SourcePlatform.status == "active")
        .all()
    )
    hay = name.lower()
    for row in rows:
        if not is_http_url((row.profile_url or "").strip()):
            continue
        label = (row.name or "").strip()
        key = (row.platform_key or "").strip()
        if name in {label, key}:
            return name
        if label and label.lower() in hay:
            return name
        if key and key.replace("_", " ") in hay:
            return name
    return ""


def ticket_channel_name(ticket: GeoTicket, db: Session | None = None) -> str:
    ev = parse_ticket_evidence(ticket)
    name = str(ev.get("channel") or "").strip()
    if not name:
        spec = official_api_for(ticket_channel_key(ticket))
        name = spec.label if spec else ""
    if db is not None:
        return verified_channel_or_blank(db, ticket.tenant_id, name)
    return name


def ticket_compose_url(ticket: GeoTicket, db: Session | None = None) -> str:
    if db is not None and not ticket_channel_name(ticket, db):
        return ""
    spec = official_api_for(ticket_channel_key(ticket))
    return spec.compose_url if spec else ""


def offsite_post_draft(*, question: str, page_url: str) -> str:
    question = " ".join((question or "").split()) or "this product"
    url = (page_url or "").strip()
    lines = [f'Buyers are asking: "{question}"']
    if url:
        lines.append(f"Official page: {url}")
    else:
        lines.append("Official page: add the product URL first.")
    return "\n".join(lines)


def ticket_offsite_draft(ticket: GeoTicket, prompt: GeoPrompt | None = None, db: Session | None = None) -> str:
    ev = parse_ticket_evidence(ticket)
    channel = str(ev.get("channel") or "").strip()
    if db is not None:
        channel = ticket_channel_name(ticket, db)
    if not channel:
        return ""
    prompt = prompt if prompt is not None else getattr(ticket, "prompt", None)
    question = " ".join(((prompt.prompt_text if prompt else "") or "").split())
    if not question:
        found = re.search(r"「([^」]+)」", ticket.title or "")
        question = found.group(1) if found else ""
    page_url = str(ev.get("page_url") or "").strip()
    if not page_url:
        found_url = re.search(r"https?://[^\s]+", ticket.recommended_action or "")
        page_url = found_url.group(0).rstrip("。.") if found_url else ""
    return offsite_post_draft(question=question, page_url=page_url)


def set_ticket_offsite_url(ticket: GeoTicket, post_url: str) -> None:
    url = (post_url or "").strip()
    if not is_http_url(url):
        raise ValueError("offsite_url")
    payload = parse_ticket_evidence(ticket)
    payload["offsite_url"] = url
    ticket.evidence = json.dumps(payload, ensure_ascii=False, indent=2)


def customer_note(
    *,
    kind: str,
    question: str,
    page_bit: str,
    url: str,
    channel: str,
) -> str:
    question = " ".join((question or "").split()) or "这个问题"
    if kind == "unverified":
        return "抽查里给出的网址还没打开核对。外来网址不能算官网。"
    lines: list[str] = []
    if page_bit and not page_bit.startswith("还没有对应页"):
        lines.append(f"请改这一页：{page_bit}")
        if url:
            lines.append(url)
    elif url:
        lines.append(f"请改这一页：{url}")
    else:
        lines.append("还没有对应页，请先补一页再写这个问题。")
    asks = {
        "absent": f"页里用英文写清买家问的「{question}」，并放上可点的官网链接。",
        "no_owned": (
            f"页里用英文写清能回答「{question}」的产品事实（规格、卖点、适用场景），"
            f"并放上可点的官网链接（指向本页或官网产品页）。"
            f"现在搜索提到了品牌，但链接里没有给出官网；改完告诉我，我再用同一问测一次。"
            f"不保证这次一定给出官网。"
        ),
        "competitor": f"页里补和别人的对照（英文），并放上可点的官网链接。",
    }
    if kind in asks:
        lines.append(asks[kind])
    if channel and kind in asks:
        lines.append(f"站外在「{channel}」发一条指向该页。")
    return "\n".join(lines)


def _slim_stored_action(raw: str) -> str:
    text = (raw or "").replace("请客户改这一页", "请改这一页")
    for phrase in _WORKBENCH_PHRASES:
        text = text.replace(phrase, "")
    return " ".join(text.split())


def ticket_customer_note(ticket: GeoTicket, prompt: GeoPrompt | None = None, db: Session | None = None) -> str:
    ev = parse_ticket_evidence(ticket)
    prompt = prompt if prompt is not None else getattr(ticket, "prompt", None)
    kind = str(ev.get("kind") or "")
    if kind not in {"absent", "no_owned", "competitor", "unverified"}:
        kind = {"absent": "absent", "mentioned": "no_owned", "competitor_dominated": "competitor"}.get(
            ticket.diagnosis, "no_owned"
        )
    question = " ".join(((prompt.prompt_text if prompt else "") or "").split())
    if not question:
        found = re.search(r"「([^」]+)」", ticket.title or "")
        question = found.group(1) if found else ""
    page_bit = str(ev.get("page_label") or "").strip()
    if not page_bit:
        page_bit = str(ev.get("page_path") or "").strip()
    url = str(ev.get("page_url") or "").strip()
    channel = str(ev.get("channel") or "").strip()
    if db is not None:
        channel = ticket_channel_name(ticket, db)
    if ev.get("kind") or page_bit or url:
        note = customer_note(kind=kind, question=question, page_bit=page_bit, url=url, channel=channel)
    else:
        note = _slim_stored_action(ticket.recommended_action) or ticket.title
    note = (note or "").strip()
    if note and "不代改" not in note:
        note = f"{note}\n{CUSTOMER_CLOSE}"
    elif not note:
        note = CUSTOMER_CLOSE
    return note


def ticket_offsite_ask(ticket: GeoTicket, prompt: GeoPrompt | None = None, db: Session | None = None) -> str:
    draft = ticket_offsite_draft(ticket, prompt, db).strip()
    if not draft:
        return ""
    channel = ticket_channel_name(ticket, db) or "站外"
    return f"请在「{channel}」自己发这一条（我们不代发）：\n{draft}"


def ticket_paste(ticket: GeoTicket, prompt: GeoPrompt | None = None, db: Session | None = None) -> str:
    note = ticket_customer_note(ticket, prompt, db)
    parts = [ticket.title.strip(), note.strip(), ticket_offsite_ask(ticket, prompt, db)]
    return "\n\n".join(part for part in parts if part)


def weekly_paste(tenant_name: str, items: list[str]) -> str:
    from app.onsite_loop import weekly_customer_heading

    name = (tenant_name or "客户").strip() or "客户"
    if not items:
        return f"{name} 这周还没有要改的三处。\n\n{CUSTOMER_CLOSE}"
    numbered = "\n\n".join(f"{index}. {item}" for index, item in enumerate(items, 1))
    return f"{weekly_customer_heading(tenant_name, items)}\n\n{numbered}\n\n{CUSTOMER_CLOSE}"


def status_for_handoff(handoff: str) -> str:
    return {"drafted": "open", "sent": "in_progress", "live": "verify"}.get(handoff, "open")


def sync_ticket_status_to_handoff(ticket: GeoTicket) -> bool:
    if ticket.status in {"done", "closed", "ignored", "reopened"}:
        return False
    want = status_for_handoff(ticket_handoff(ticket))
    if ticket.status == want:
        return False
    ticket.status = want
    return True


def reconcile_open_ticket_status(db: Session, tenant_id: str) -> int:
    tickets = (
        db.query(GeoTicket)
        .filter(
            GeoTicket.tenant_id == tenant_id,
            ~GeoTicket.status.in_(["done", "closed", "ignored"]),
        )
        .all()
    )
    updated = 0
    for ticket in tickets:
        if sync_ticket_status_to_handoff(ticket):
            updated += 1
    return updated


def set_ticket_handoff(ticket: GeoTicket, handoff: str, live_url: str = "") -> None:
    if handoff not in HANDOFFS:
        raise ValueError(handoff)
    payload = parse_ticket_evidence(ticket)
    url = (live_url or payload.get("live_url") or "").strip()
    if handoff == "live":
        if not is_http_url(url):
            raise ValueError("live_url")
        payload["live_url"] = url
    elif url and is_http_url(url):
        payload["live_url"] = url
    payload["handoff"] = handoff
    ticket.evidence = json.dumps(payload, ensure_ascii=False, indent=2)
    if ticket.status in {"done", "closed", "ignored"}:
        return
    ticket.status = status_for_handoff(handoff)


def loop_ticket_spec(
    db: Session,
    tenant_id: str,
    prompt: GeoPrompt,
    kind: str,
    *,
    third_party: bool = False,
    sample_rows: list[GeoSampleResult] | None = None,
) -> dict:
    page = suggest_page(db, tenant_id, prompt.prompt_text)
    channel_name, channel_key, _channel_href = suggest_channel(db, tenant_id)
    short = short_prompt(prompt.prompt_text)
    page_bit = page_label(page)
    url = page_url(db, tenant_id, page)
    question = " ".join((prompt.prompt_text or "").split()) or short
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
    note_page = page_bit if page else ""
    note_url = url if page else ""
    actions = {}
    for action_kind in ("absent", "no_owned", "competitor", "unverified"):
        note = customer_note(
            kind=action_kind,
            question=question,
            page_bit=note_page,
            url=note_url,
            channel=channel_name,
        )
        actions[action_kind] = note if action_kind == "unverified" else f"{note}\n{CUSTOMER_CLOSE}"
    rationale = f"对应页：{page_bit} · 官网：{url} · 渠道：{channel_name}"
    reason = sample_reason_for_ticket(sample_rows or [], kind)
    if reason:
        rationale += f"。{reason}"
    caveat = overseas_source_note(sample_rows or [], prompt)
    if caveat:
        rationale += f"。{caveat}"
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
            "page_label": page_bit if page else "",
            "page_url": url,
            "channel": channel_name,
            "channel_key": channel_key,
            "handoff": "drafted",
            "honest_loop": True,
        },
    }


def apply_loop_spec(ticket: GeoTicket, spec: dict, *, keep_handoff: bool = True) -> None:
    handoff = ticket_handoff(ticket) if keep_handoff else "drafted"
    ticket.title = spec["title"]
    ticket.diagnosis = spec["diagnosis"]
    ticket.rationale = spec["rationale"]
    ticket.recommended_action = spec["recommended_action"]
    ticket.acceptance_criteria = spec["acceptance_criteria"]
    ticket.retest_method = spec["retest_method"]
    evidence = dict(spec["evidence"])
    evidence["handoff"] = handoff
    if keep_handoff:
        live_url = ticket_live_url(ticket)
        offsite_url = ticket_offsite_url(ticket)
        if live_url:
            evidence["live_url"] = live_url
        if offsite_url:
            evidence["offsite_url"] = offsite_url
    ticket.evidence = json.dumps(evidence, ensure_ascii=False, indent=2)


def kinds_from_sample_rows(rows: list[GeoSampleResult]) -> list[str]:
    mentioned = any(row.mentioned for row in rows)
    owned = any(_owned(row) for row in rows)
    overseas_mentioned = any(row.mentioned for row in _overseas_rows(rows))
    competitors = any((row.competitor_hits or "").strip() for row in rows)
    kinds: list[str] = []
    if not mentioned:
        kinds.append("absent")
    elif not owned and overseas_mentioned:
        # Only when an overseas source (e.g. Tavily) mentioned us without an owned URL.
        # Bocha-only mention with shop pages is not a reason to ask the customer to fix a page.
        kinds.append("no_owned")
    if competitors:
        kinds.append("competitor")
    return kinds


def write_ticket_retest(
    db: Session,
    tenant_id: str,
    latest: GeoSampleRun | list[GeoSampleRun] | None,
    previous: GeoSampleRun | list[GeoSampleRun] | None,
) -> int:
    latest_runs = [run for run in _as_runs(latest) if getattr(run, "results", None)]
    previous_runs = [run for run in _as_runs(previous) if getattr(run, "results", None)]
    if not latest_runs:
        return 0
    latest_by: dict[str, list[GeoSampleResult]] = {}
    previous_by: dict[str, list[GeoSampleResult]] = {}
    for run in latest_runs:
        for row in run.results:
            latest_by.setdefault(row.prompt_id, []).append(row)
    for run in previous_runs:
        for row in run.results:
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
        rows = latest_by.get(ticket.prompt_id, [])
        kinds = kinds_from_sample_rows(rows)
        prompt = db.get(GeoPrompt, ticket.prompt_id)
        changed = False
        if prompt is not None and kinds:
            spec = loop_ticket_spec(
                db,
                tenant_id,
                prompt,
                kinds[0],
                third_party=any(_third_party(row) for row in rows),
                sample_rows=rows,
            )
            if (
                ticket.title != spec["title"]
                or ticket.diagnosis != spec["diagnosis"]
                or ticket.rationale != spec["rationale"]
                or ticket.recommended_action != spec["recommended_action"]
            ):
                apply_loop_spec(ticket, spec, keep_handoff=True)
                changed = True
        if previous_runs:
            note = compare_prompt_note(rows, previous_by.get(ticket.prompt_id, []))
            if ticket.retest_result != note:
                ticket.retest_result = note
                changed = True
        if changed:
            ticket.last_checked_at = now
            updated += 1
    return updated


def refresh_open_tickets_from_samples(db: Session, tenant_id: str) -> int:
    recent = (
        db.query(GeoSampleRun)
        .options(selectinload(GeoSampleRun.results))
        .filter(GeoSampleRun.tenant_id == tenant_id)
        .order_by(GeoSampleRun.started_at.desc())
        .limit(12)
        .all()
    )
    latest, previous = pick_sample_batches(recent)
    return write_ticket_retest(db, tenant_id, latest, previous)


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
