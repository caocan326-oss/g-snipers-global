"""GEO closed loop: name a page or channel, retest the same question, record only the change.

Doing the work does not mean the next sample will mention the brand.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

from sqlalchemy.orm import Session, selectinload

from app.geo_helpers import ENGINE_LABELS
from app.models import GeoPrompt, GeoSampleResult, GeoSampleRun, GeoTicket, SitePage, SourcePlatform, Tenant
from app.official_apis import OFFICIAL_APIS

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
        "absent": f"页里写清买家问的「{question}」，并放上官网链接。",
        "no_owned": f"页里补能回答「{question}」的事实，并放上官网链接。",
        "competitor": f"页里补和别人的对照，并放上官网链接。",
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


def ticket_customer_note(ticket: GeoTicket, prompt: GeoPrompt | None = None) -> str:
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
    if ev.get("kind") or page_bit or url:
        return customer_note(kind=kind, question=question, page_bit=page_bit, url=url, channel=channel)
    slim = _slim_stored_action(ticket.recommended_action)
    return slim or ticket.title


def ticket_paste(ticket: GeoTicket, prompt: GeoPrompt | None = None) -> str:
    note = ticket_customer_note(ticket, prompt)
    parts = [ticket.title.strip(), note.strip(), CUSTOMER_CLOSE]
    return "\n\n".join(part for part in parts if part)


def weekly_paste(tenant_name: str, items: list[str]) -> str:
    name = (tenant_name or "客户").strip() or "客户"
    if not items:
        return f"{name} 这周还没有要改的三处。\n\n{CUSTOMER_CLOSE}"
    numbered = "\n\n".join(f"{index}. {item}" for index, item in enumerate(items, 1))
    return f"{name} 这周请改这几处：\n\n{numbered}\n\n{CUSTOMER_CLOSE}"


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
    channel_name, _channel_href = suggest_channel(db, tenant_id)
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
    if third_party and kind in {"absent", "no_owned"}:
        rationale += "。回答里出现了外来网址，不能写成给出了官网。"
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
    ticket.evidence = json.dumps(evidence, ensure_ascii=False, indent=2)


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
