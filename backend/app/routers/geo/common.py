import hashlib
import json
import re
from urllib.parse import urlparse

from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.geo_citations import is_owned_url, marketplace_urls, split_citations
from app.geo_helpers import DIAGNOSES, ENGINE_LABELS, ENGINES, engine_region
from app.geo_loop import (
    HANDOFF_LABELS,
    cite_pack_for_prompt,
    cite_paste_for_prompt,
    cite_published_url,
    cite_stage,
    cite_stage_label,
    recorded_from_label,
    watch_state,
    parse_ticket_evidence,
    ticket_channel_key,
    ticket_channel_name,
    ticket_compose_url,
    ticket_customer_note,
    ticket_handoff,
    ticket_live_url,
    ticket_offsite_draft,
    ticket_offsite_url,
    ticket_paste,
)
from app.models import (
    Competitor,
    GeoObservation,
    GeoPrompt,
    GeoSampleResult,
    GeoSampleRun,
    GeoTicket,
    Market,
    Tenant,
    User,
)
from app.schemas import (
    GeoObservationOut,
    GeoPromptOut,
    GeoSampleResultOut,
    GeoSampleRunOut,
    GeoTicketOut,
)

from .constants import EVIDENCE_LABELS, EXPORT_B2B_PACK_ID, EXPORT_B2B_PROMPTS, RECORDED_OBS


def _sha256(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _json_list(raw: str) -> list[str]:
    try:
        data = json.loads(raw or "[]")
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [str(item) for item in data if str(item).strip()]


def _dump_list(items: list[str]) -> str:
    return json.dumps(items, ensure_ascii=False)


def _extract_urls(text: str) -> list[str]:
    found = re.findall(r"https?://[^\s\)\]\>\"'，,；;]+", text or "")
    cleaned: list[str] = []
    seen: set[str] = set()
    for url in found:
        value = url.rstrip(".,，。；;")
        if value and value not in seen:
            cleaned.append(value)
            seen.add(value)
    return cleaned


def _split_urls(text: str) -> list[str]:
    candidates = re.split(r"[\s,，;；]+", text or "")
    return _extract_urls(" ".join(candidates))


def _host(value: str) -> str:
    host = urlparse(value if "://" in value else f"https://{value}").netloc.lower()
    return host[4:] if host.startswith("www.") else host


def _root_domain(domain: str) -> str:
    parsed = _host(domain) if domain else ""
    return parsed


def _is_owned_url(url: str, root: str, aliases: list[str]) -> bool:
    return is_owned_url(url, root, aliases)


def _citation_buckets(urls: list[str], root: str, aliases: list[str] | None = None) -> tuple[list[str], list[str]]:
    owned, _marketplace, _other = split_citations(urls, root, aliases)
    owned_set = set(owned)
    third_party: list[str] = []
    seen: set[str] = set()
    for url in urls:
        value = (url or "").strip()
        if not value or value in seen or value in owned_set:
            continue
        seen.add(value)
        third_party.append(value)
    return owned, third_party


def _tenant_brand_names(tenant: Tenant | None) -> list[str]:
    names = []
    if tenant and tenant.name:
        names.append(tenant.name)
    if tenant and tenant.site_origin:
        root = _root_domain(tenant.site_origin)
        if root:
            names.append(root)
            names.append(root.split(".")[0])
    return list(dict.fromkeys([n for n in names if n]))


def _locale_lang(locale: str) -> str:
    return (locale or "en").split("-", 1)[0].lower()


def _brand_short(brand: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9一-鿿 ]+", " ", brand or "").strip()
    return cleaned.split()[0] if cleaned.split() else brand


def _first_competitor(db: Session, tenant_id: str, market_id: str | None) -> str:
    q = db.query(Competitor).filter(Competitor.tenant_id == tenant_id)
    if market_id:
        q = q.filter(Competitor.market_id == market_id)
    row = q.order_by(Competitor.created_at.desc()).first()
    return row.name if row else "a leading competitor"


def _pack_fill(text: str, values: dict[str, str]) -> str:
    out = text
    for key, value in values.items():
        out = out.replace("{" + key + "}", value or "")
    return re.sub(r"\s+", " ", out).strip()


def _prompt_pack_candidates(
    db: Session,
    user: User,
    *,
    tenant: Tenant | None,
    market: Market | None,
    keyword: str,
    locale: str,
    seo_page_id: str | None = None,
    demand_signal_id: str | None = None,
    limit_per_source: int = 12,
) -> list[dict[str, str | None]]:
    brand = (tenant.name if tenant else "") or _root_domain(tenant.site_origin if tenant else "") or "the brand"
    product = keyword.strip() or "the product category"
    values = {
        "Brand": brand,
        "BrandShort": _brand_short(brand),
        "Competitor": _first_competitor(db, user.tenant_id, market.id if market else None),
        "ProductCategory": product,
        "ProductCategoryAlt": product,
        "Application": "industrial procurement",
        "Country": market.name if market else "the target market",
        "Cert": "ISO 9001",
    }
    lang = _locale_lang(locale)
    wanted_langs = {"en"}
    if lang.startswith("zh"):
        wanted_langs.add("zh")
    out: list[dict[str, str | None]] = []
    for key, ptype, prompt_lang, template in EXPORT_B2B_PROMPTS:
        if prompt_lang not in wanted_langs:
            continue
        out.append(
            {
                "prompt_text": _pack_fill(template, values),
                "locale": locale,
                "market_id": market.id if market else None,
                "seo_page_id": seo_page_id,
                "demand_signal_id": demand_signal_id,
                "prompt_pack_id": EXPORT_B2B_PACK_ID,
                "prompt_key": key,
                "prompt_type": ptype,
            }
        )
        if len(out) >= limit_per_source:
            break
    return out


def _evidence_tier(o: GeoObservation) -> str:
    if o.status == "verified":
        return "verified"
    if o.status == "cited" or (o.citation_urls or "").strip():
        return "cited"
    if o.status == "mentioned" or (o.brand_mentions or "").strip():
        return "mentioned"
    return "none"


def _obs_out(o: GeoObservation) -> GeoObservationOut:
    return GeoObservationOut(
        id=o.id,
        prompt_id=o.prompt_id,
        engine=o.engine,
        engine_label=ENGINE_LABELS.get(o.engine, o.engine),
        region=engine_region(o.engine),
        surface=o.surface or "manual_ai_answer",
        sample_type=o.sample_type or "manual",
        status=o.status,
        evidence_tier=_evidence_tier(o),
        evidence_label=EVIDENCE_LABELS.get(_evidence_tier(o), "无证据"),
        response_excerpt=o.response_excerpt or "",
        citation_urls=o.citation_urls or "",
        brand_mentions=o.brand_mentions or "",
        competitor_mentions=o.competitor_mentions or "",
        interpretation_note=o.interpretation_note or "",
        notes=o.notes,
        observed_at=o.observed_at,
    )


def _result_out(row: GeoSampleResult) -> GeoSampleResultOut:
    return GeoSampleResultOut(
        id=row.id,
        run_id=row.run_id,
        prompt_id=row.prompt_id,
        observation_id=row.observation_id,
        evidence_id=row.evidence_id,
        trial_index=row.trial_index,
        prompt_type=row.prompt_type or "custom",
        engine=row.engine,
        engine_label=ENGINE_LABELS.get(row.engine, row.engine),
        model=row.model,
        web_grounded=row.web_grounded,
        surface=row.surface,
        prompt_text_hash=row.prompt_text_hash,
        answer_text_hash=row.answer_text_hash,
        answer_excerpt=row.answer_excerpt or "",
        mentioned=row.mentioned,
        citations=_json_list(row.citations_json),
        owned_citations=_json_list(row.owned_citations_json),
        third_party_citations=_json_list(row.third_party_citations_json),
        marketplace_citations=marketplace_urls(_json_list(row.third_party_citations_json)),
        brand_hits=row.brand_hits or "",
        competitor_hits=row.competitor_hits or "",
        verification_status=row.verification_status,
        verification_note=row.verification_note or "",
        sampled_at=row.sampled_at,
    )


def _sample_aggregate(row: GeoSampleRun) -> dict:
    grouped: dict[tuple[str, str], list[GeoSampleResult]] = {}
    for result in row.results or []:
        grouped.setdefault((result.engine, result.prompt_id), []).append(result)
    by_prompt = []
    for (engine, prompt_id), results in sorted(grouped.items()):
        total = len(results)
        third_party_domains: dict[str, int] = {}
        for result in results:
            for url in _grounded_json_list(result, "third_party_citations_json"):
                host = _host(url)
                if host:
                    third_party_domains[host] = third_party_domains.get(host, 0) + 1
        prompt = results[0].prompt
        ptype = results[0].prompt_type or (prompt.prompt_type if prompt else "custom")
        by_prompt.append(
            {
                "prompt_id": prompt.prompt_key if prompt and prompt.prompt_key else prompt_id,
                "prompt_db_id": prompt_id,
                "type": ptype,
                "engine": engine,
                "trials": total,
                "mention_rate": round(sum(1 for r in results if r.mentioned) / total, 3) if total else 0,
                "citation_rate": round(sum(1 for r in results if _grounded_json_list(r, "citations_json")) / total, 3) if total else 0,
                "owned_citation_rate": round(sum(1 for r in results if _grounded_json_list(r, "owned_citations_json")) / total, 3) if total else 0,
                "third_party_citation_rate": round(sum(1 for r in results if _grounded_json_list(r, "third_party_citations_json")) / total, 3) if total else 0,
                "top_third_party_domains": [
                    host for host, _count in sorted(third_party_domains.items(), key=lambda item: item[1], reverse=True)[:10]
                ],
            }
        )
    return {
        "run_id": row.id,
        "engine": ",".join(_json_list(row.engines)),
        "prompt_pack_id": row.prompt_set_id,
        "config_hash": row.config_hash,
        "byPrompt": by_prompt,
    }


def _grounded_json_list(result: GeoSampleResult, field: str) -> list[str]:
    if result.web_grounded == "false":
        return []
    return _json_list(getattr(result, field))


def _run_rates(results: list[GeoSampleResult]) -> dict[str, str]:
    total = len(results)
    mentioned = [r for r in results if r.mentioned]
    cited = [r for r in results if _grounded_json_list(r, "owned_citations_json")]
    verified = [r for r in cited if r.verification_status == "passed"]
    return {
        "mention_rate": _rate(len(mentioned), total),
        "cite_rate": _rate(len(cited), total),
        "verified_citation_rate": _rate(len(verified), total),
    }


def _run_out(row: GeoSampleRun, include_results: bool = True) -> GeoSampleRunOut:
    results = list(row.results or [])
    rates = _run_rates(results)
    aggregate = _sample_aggregate(row) if results else {}
    return GeoSampleRunOut(
        id=row.id,
        protocol_version=row.protocol_version,
        prompt_set_id=row.prompt_set_id,
        config_hash=row.config_hash,
        domain=row.domain,
        brand_names=_json_list(row.brand_names),
        engines=_json_list(row.engines),
        trials_per_prompt=row.trials_per_prompt,
        region_hint=row.region_hint or "",
        language=row.language or "",
        status=row.status,
        note=row.note or "",
        started_at=row.started_at,
        finished_at=row.finished_at,
        results_count=len(results),
        mention_rate=rates["mention_rate"],
        cite_rate=rates["cite_rate"],
        verified_citation_rate=rates["verified_citation_rate"],
        results=[_result_out(r) for r in results] if include_results else [],
        aggregate=aggregate,
    )


def _rate(part: int, total: int) -> str:
    if total <= 0:
        return "未测"
    return f"{round(part / total * 100, 1)}%"


def _prompt_rates(observations: list[GeoObservation]) -> dict[str, str]:
    recorded = [o for o in observations if o.status in RECORDED_OBS]
    mentioned = [o for o in recorded if _evidence_tier(o) in {"mentioned", "cited", "verified"}]
    cited = [o for o in recorded if _evidence_tier(o) in {"cited", "verified"}]
    verified = [o for o in recorded if _evidence_tier(o) == "verified"]
    competitor = [o for o in recorded if (o.competitor_mentions or "").strip()]
    return {
        "mention_rate": _rate(len(mentioned), len(recorded)),
        "cite_rate": _rate(len(cited), len(recorded)),
        "verified_citation_rate": _rate(len(verified), len(recorded)),
        "competitor_rate": _rate(len(competitor), len(recorded)),
        "absorption_rate": _rate(len(mentioned), len(recorded)),
    }


def _sample_prompt_rates(rows: list[GeoSampleResult]) -> dict[str, str]:
    total = len(rows)
    mentioned = sum(1 for row in rows if row.mentioned)
    owned = sum(1 for row in rows if _grounded_json_list(row, "owned_citations_json"))
    return {
        "mention_rate": _rate(mentioned, total),
        "cite_rate": _rate(owned, total),
    }


def _prompt_out(
    row: GeoPrompt,
    sample_verdict: str = "",
    sample_rows: list[GeoSampleResult] | None = None,
    sample_compare_note: str = "",
    sample_trend: list | None = None,
    trend_note: str = "",
    cited_others: list[str] | None = None,
    competitor_note: str = "",
    page_draft: str = "",
    faq_draft: str = "",
    llms_txt: str = "",
    last_sampled_at=None,
) -> GeoPromptOut:
    diagnosis = row.diagnosis or "untested"
    rates = _prompt_rates(row.observations)
    if sample_rows:
        sample_rates = _sample_prompt_rates(sample_rows)
        rates["mention_rate"] = sample_rates["mention_rate"]
        rates["cite_rate"] = sample_rates["cite_rate"]
    watched = watch_state(last_sampled_at)
    return GeoPromptOut(
        id=row.id,
        prompt_text=row.prompt_text,
        locale=row.locale,
        market_id=row.market_id,
        seo_page_id=row.seo_page_id,
        demand_signal_id=row.demand_signal_id,
        prompt_pack_id=row.prompt_pack_id or "custom",
        prompt_key=row.prompt_key or "",
        prompt_type=row.prompt_type or "custom",
        diagnosis=diagnosis,
        diagnosis_label=DIAGNOSES.get(diagnosis, diagnosis),
        created_at=row.created_at,
        observations=[_obs_out(o) for o in row.observations],
        mention_rate=rates["mention_rate"],
        cite_rate=rates["cite_rate"],
        verified_citation_rate=rates["verified_citation_rate"],
        competitor_rate=rates["competitor_rate"],
        absorption_rate=rates["absorption_rate"],
        ai_status=row.ai_status or "untested",
        evidence=row.evidence or "",
        sample_verdict=sample_verdict,
        recorded_from=getattr(row, "recorded_from", "") or "",
        recorded_from_label=recorded_from_label(getattr(row, "recorded_from", "") or ""),
        source_note=getattr(row, "source_note", "") or "",
        sample_compare_note=sample_compare_note,
        sample_trend=sample_trend or [],
        trend_note=trend_note,
        cited_others=cited_others or [],
        competitor_note=competitor_note,
        page_draft=page_draft,
        faq_draft=faq_draft,
        llms_txt=llms_txt,
        cite_stage=cite_stage(row),
        cite_stage_label=cite_stage_label(cite_stage(row)),
        cite_published_url=cite_published_url(row),
        cite_paste=cite_paste_for_prompt(
            {"page_draft": page_draft, "faq_draft": faq_draft, "llms_txt": llms_txt},
            row,
        )
        if page_draft or faq_draft or llms_txt
        else "",
        watch_due=bool(watched["due"]),
        watch_note=str(watched["note"] or ""),
        last_sampled_at=watched["last_sampled_at"],
        next_watch_at=watched["next_watch_at"],
    )


def _ticket_out(row: GeoTicket, sample_note: str = "", db: Session | None = None, tenant: Tenant | None = None) -> GeoTicketOut:
    ev = parse_ticket_evidence(row)
    page_label = str(ev.get("page_label") or "").strip()
    page_url = str(ev.get("page_url") or "").strip()
    prompt = getattr(row, "prompt", None)
    if prompt is None and db is not None and row.prompt_id:
        prompt = db.get(GeoPrompt, row.prompt_id)
    paste = ticket_paste(row, prompt)
    if db is not None and prompt is not None:
        cite = cite_paste_for_prompt(cite_pack_for_prompt(db, tenant, prompt), prompt)
        if cite and cite not in paste:
            paste = f"{paste}\n\n{cite}" if paste else cite
    return GeoTicketOut(
        id=row.id,
        prompt_id=row.prompt_id,
        title=row.title,
        diagnosis=row.diagnosis,
        diagnosis_label=DIAGNOSES.get(row.diagnosis, row.diagnosis),
        rationale=row.rationale,
        acceptance_criteria=row.acceptance_criteria,
        priority=row.priority or "P2",
        owner_hint=row.owner_hint or "内容运营 / 客户经理",
        recommended_action=row.recommended_action or "补对应页。我们不代改线上、不代发。",
        customer_note=ticket_customer_note(row, prompt),
        customer_paste=paste,
        page_label=page_label,
        page_url=page_url,
        channel=ticket_channel_name(row),
        channel_key=ticket_channel_key(row),
        compose_url=ticket_compose_url(row),
        offsite_draft=ticket_offsite_draft(row, prompt),
        offsite_url=ticket_offsite_url(row),
        retest_method=row.retest_method or "对同一买家问题再抽查一次，只记有没有变化，不要求这次必须提到。",
        retest_result=row.retest_result or "",
        sample_note=sample_note,
        handoff=ticket_handoff(row),
        handoff_label=HANDOFF_LABELS[ticket_handoff(row)],
        result_url=ticket_live_url(row),
        blocked_reason=row.blocked_reason or "",
        status=row.status,
        verified_note=row.verified_note,
        ai_status=row.ai_status or "untested",
        ai_review=row.ai_review or "",
        # Keep in DB; API still returns for ops tools, UI must not show raw JSON.
        evidence=row.evidence or "",
        last_checked_at=row.last_checked_at,
        closed_at=row.closed_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _create_untested_slots(db: Session, user: User, prompt: GeoPrompt) -> None:
    for engine in ENGINES:
        db.add(
            GeoObservation(
                tenant_id=user.tenant_id,
                prompt_id=prompt.id,
                engine=engine,
                status="untested",
            )
        )


def _load_prompt(db: Session, prompt_id: str) -> GeoPrompt:
    return (
        db.query(GeoPrompt)
        .options(selectinload(GeoPrompt.observations))
        .filter(GeoPrompt.id == prompt_id)
        .one()
    )


def _prompt_key(text: str, locale: str) -> tuple[str, str]:
    return (" ".join((text or "").lower().split()), locale)


def _market_phrase(db: Session, market_id: str | None) -> str:
    if not market_id:
        return ""
    market = db.get(Market, market_id)
    if market is None:
        return ""
    return f" in {market.name}"


def _buyer_intent_prompts(keyword: str, market_phrase: str) -> list[str]:
    return [
        f"What is the best supplier for {keyword}{market_phrase}?",
        f"Which companies are recommended for {keyword}{market_phrase}?",
        f"What should I check before buying {keyword}{market_phrase}?",
        f"Compare leading {keyword} manufacturers{market_phrase}.",
    ]


def _brand_mentioned(text: str, brand_names: list[str]) -> tuple[bool, str]:
    lower = (text or "").lower()
    hits = [name for name in brand_names if name and name.lower() in lower]
    return bool(hits), ", ".join(hits)


def _ticket_exists(db: Session, tenant_id: str, prompt_id: str, title: str) -> bool:
    return (
        db.query(func.count(GeoTicket.id))
        .filter(GeoTicket.tenant_id == tenant_id, GeoTicket.prompt_id == prompt_id, GeoTicket.title == title)
        .scalar()
        or 0
    ) > 0

