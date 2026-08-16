import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from io import StringIO
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.ai_engine import assist_geo_asset, assist_geo_prompt, assist_geo_ticket
from app.auth import get_current_user
from app.database import get_db
from app.geo_helpers import (
    CHECKLIST_DEFS,
    CHECK_STATUSES,
    DIAGNOSES,
    ENGINES,
    ENGINE_LABELS,
    OBS_STATUSES,
    TICKET_STATUSES,
    build_llms_txt,
    engine_region,
    ensure_engine_slots,
)
from app.geo_providers import GeoProviderError, provider_statuses, sample_with_provider
from app.models import (
    Competitor,
    DemandSignal,
    GeoAsset,
    GeoChecklistItem,
    GeoObservation,
    GeoPrompt,
    GeoSampleResult,
    GeoSampleRun,
    GeoTicket,
    Market,
    SeoPage,
    Tenant,
    User,
)
from app.risk import require_confirm
from app.schemas import (
    AiAssistOut,
    AiStepIn,
    ConfirmReadyIn,
    GeoAutoSampleIn,
    GeoAssetOut,
    GeoAssetUpdate,
    GeoChecklistItemOut,
    GeoChecklistItemUpdate,
    GeoDiagnosisIn,
    GeoObservationOut,
    GeoObservationUpdate,
    GeoPromptCreate,
    GeoPromptOut,
    GeoProviderStatusListOut,
    GeoProviderStatusOut,
    GeoReportOut,
    GeoReportTableOut,
    GeoSampleResultOut,
    GeoSampleRunCreate,
    GeoSampleRunOut,
    GeoSeedOut,
    GeoSummary,
    GeoTicketCreate,
    GeoTicketDraftOut,
    GeoTicketOut,
    GeoTicketVerifyIn,
)

router = APIRouter(prefix="/api/geo", tags=["geo"])

RECORDED_OBS = {"mentioned", "not_mentioned", "cited", "verified"}
EVIDENCE_LABELS = {
    "none": "无证据",
    "mentioned": "正文提及",
    "cited": "引用待核验",
    "verified": "引用已核验",
}
PROTOCOL_VERSION = "geo-test-protocol-v1"
EXPORT_B2B_PACK_ID = "export-b2b-observation-v1"
PROMPT_TYPES = {"branded", "category", "competitor", "task", "custom"}
EXPORT_B2B_PROMPTS = [
    ("EX-EN-B01", "branded", "en", "What is {Brand} and what does the company do?"),
    ("EX-EN-B02", "branded", "en", "What is {Brand} best known for in {ProductCategory}?"),
    ("EX-EN-B03", "branded", "en", "Who should buy from {Brand}? What kind of buyers fit best?"),
    ("EX-EN-B04", "branded", "en", "What certifications or quality standards is {Brand} associated with?"),
    ("EX-EN-B05", "branded", "en", "Where is {Brand} based and which markets does it export to?"),
    ("EX-EN-C01", "category", "en", "Best {ProductCategory} manufacturers for export to {Country}"),
    ("EX-EN-C02", "category", "en", "How to choose a reliable {ProductCategory} supplier for B2B import?"),
    ("EX-EN-C03", "category", "en", "Key quality checks when sourcing {ProductCategory} from overseas"),
    ("EX-EN-C04", "category", "en", "{ProductCategory} specifications buyers usually request in RFQs"),
    ("EX-EN-C05", "category", "en", "Difference between industrial-grade and cheap {ProductCategoryAlt}"),
    ("EX-EN-C06", "category", "en", "Top considerations for OEM / ODM {ProductCategory} partnerships"),
    ("EX-EN-C07", "category", "en", "How are {ProductCategory} typically certified for {Country} market entry?"),
    ("EX-EN-C08", "category", "en", "Common failure modes or quality risks in {ProductCategory} supply chains"),
    ("EX-EN-P01", "competitor", "en", "{Brand} vs {Competitor} for {ProductCategory} - how should a buyer compare them?"),
    ("EX-EN-P02", "competitor", "en", "Alternatives to {Competitor} for {ProductCategory} export buyers"),
    ("EX-EN-P03", "competitor", "en", "Which companies are often mentioned for {ProductCategory} in {Application}?"),
    ("EX-EN-T01", "task", "en", "How should a B2B exporter structure a product page so engineers can evaluate {ProductCategory}?"),
    ("EX-EN-T02", "task", "en", "What documents should a {ProductCategory} supplier prepare for an international RFQ?"),
    ("EX-EN-T03", "task", "en", "How can a manufacturer measure whether AI search tools recommend their brand?"),
    ("EX-ZH-B01", "branded", "zh", "{Brand} 是做什么的？主要服务哪些客户？"),
    ("EX-ZH-B02", "branded", "zh", "{Brand} 在 {ProductCategory} 领域以什么闻名？"),
    ("EX-ZH-C01", "category", "zh", "出口到 {Country} 的 {ProductCategory} 供应商怎么选？"),
    ("EX-ZH-C02", "category", "zh", "进口 {ProductCategory} 时，B2B 买家通常看哪些质量与认证？"),
    ("EX-ZH-C03", "category", "zh", "{ProductCategory} 国际询盘里常见的技术参数有哪些？"),
    ("EX-ZH-P01", "competitor", "zh", "{Brand} 和 {Competitor} 在 {ProductCategory} 上如何比较？"),
    ("EX-ZH-T01", "task", "zh", "出口型 B2B 官网产品页应具备哪些工程师可评估的信息？"),
]


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
    host = _host(url)
    if not host or not root:
        return False
    normalized_aliases = {_root_domain(a) for a in aliases if a}
    return host == root or host.endswith("." + root) or host in normalized_aliases


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
    cleaned = re.sub(r"[^A-Za-z0-9\u4e00-\u9fff ]+", " ", brand or "").strip()
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


@router.get("/providers/status", response_model=GeoProviderStatusListOut)
def geo_provider_status(user: User = Depends(get_current_user)) -> GeoProviderStatusListOut:
    return GeoProviderStatusListOut(
        providers=[GeoProviderStatusOut(**row.__dict__) for row in provider_statuses()]
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


def _prompt_out(row: GeoPrompt) -> GeoPromptOut:
    diagnosis = row.diagnosis or "untested"
    rates = _prompt_rates(row.observations)
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
    )


def _ticket_out(row: GeoTicket) -> GeoTicketOut:
    return GeoTicketOut(
        id=row.id,
        prompt_id=row.prompt_id,
        title=row.title,
        diagnosis=row.diagnosis,
        diagnosis_label=DIAGNOSES.get(row.diagnosis, row.diagnosis),
        rationale=row.rationale,
        acceptance_criteria=row.acceptance_criteria,
        status=row.status,
        verified_note=row.verified_note,
        ai_status=row.ai_status or "untested",
        ai_review=row.ai_review or "",
        evidence=row.evidence or "",
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


@router.get("/summary", response_model=GeoSummary)
def geo_summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> GeoSummary:
    tid = user.tenant_id
    observations = db.query(GeoObservation).filter(GeoObservation.tenant_id == tid).all()
    recorded_rows = [o for o in observations if o.status in RECORDED_OBS]
    mentioned_rows = [o for o in recorded_rows if _evidence_tier(o) in {"mentioned", "cited", "verified"}]
    cited_rows = [o for o in recorded_rows if _evidence_tier(o) in {"cited", "verified"}]
    verified_rows = [o for o in recorded_rows if _evidence_tier(o) == "verified"]
    competitor_rows = [o for o in recorded_rows if (o.competitor_mentions or "").strip()]
    prompts = db.query(func.count(GeoPrompt.id)).filter(GeoPrompt.tenant_id == tid).scalar() or 0
    untested = (
        db.query(func.count(GeoObservation.id))
        .filter(GeoObservation.tenant_id == tid, GeoObservation.status == "untested")
        .scalar()
        or 0
    )
    recorded = (
        db.query(func.count(GeoObservation.id))
        .filter(GeoObservation.tenant_id == tid, GeoObservation.status != "untested")
        .scalar()
        or 0
    )
    check_untested = (
        db.query(func.count(GeoChecklistItem.id))
        .filter(GeoChecklistItem.tenant_id == tid, GeoChecklistItem.status == "untested")
        .scalar()
        or 0
    )
    assets_draft = (
        db.query(func.count(GeoAsset.id)).filter(GeoAsset.tenant_id == tid, GeoAsset.status == "draft").scalar() or 0
    )
    tickets_open = (
        db.query(func.count(GeoTicket.id))
        .filter(GeoTicket.tenant_id == tid, GeoTicket.status.in_(["open", "in_progress", "verify", "reopened"]))
        .scalar()
        or 0
    )
    sample_runs = db.query(func.count(GeoSampleRun.id)).filter(GeoSampleRun.tenant_id == tid).scalar() or 0
    evidence_results = db.query(func.count(GeoSampleResult.id)).filter(GeoSampleResult.tenant_id == tid).scalar() or 0
    latest_run = (
        db.query(GeoSampleRun)
        .filter(GeoSampleRun.tenant_id == tid)
        .order_by(GeoSampleRun.started_at.desc())
        .first()
    )
    return GeoSummary(
        prompts=prompts,
        untested=untested,
        recorded=recorded,
        checklist_untested=check_untested,
        assets_draft=assets_draft,
        tickets_open=tickets_open,
        mention_rate=_rate(len(mentioned_rows), len(recorded_rows)),
        cite_rate=_rate(len(cited_rows), len(recorded_rows)),
        verified_citation_rate=_rate(len(verified_rows), len(recorded_rows)),
        competitor_rate=_rate(len(competitor_rows), len(recorded_rows)),
        absorption_rate=_rate(len(mentioned_rows), len(recorded_rows)),
        competitor_mentions=len(competitor_rows),
        sample_runs=sample_runs,
        evidence_results=evidence_results,
        latest_run_id=latest_run.id if latest_run else None,
    )


@router.get("/prompts", response_model=list[GeoPromptOut])
def list_prompts(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[GeoPromptOut]:
    rows = (
        db.query(GeoPrompt)
        .options(selectinload(GeoPrompt.observations))
        .filter(GeoPrompt.tenant_id == user.tenant_id)
        .order_by(GeoPrompt.created_at.desc())
        .all()
    )
    dirty = False
    for row in rows:
        existing = {o.engine for o in row.observations}
        if any(engine not in existing for engine in ENGINES):
            ensure_engine_slots(db, user.tenant_id, row)
            dirty = True
    if dirty:
        db.commit()
        rows = (
            db.query(GeoPrompt)
            .options(selectinload(GeoPrompt.observations))
            .filter(GeoPrompt.tenant_id == user.tenant_id)
            .order_by(GeoPrompt.created_at.desc())
            .all()
        )
    return [_prompt_out(r) for r in rows]


@router.post("/prompts", response_model=GeoPromptOut, status_code=201)
def create_prompt(
    body: GeoPromptCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GeoPromptOut:
    if body.prompt_type not in PROMPT_TYPES:
        raise HTTPException(status_code=400, detail="无效问句类型")
    row = GeoPrompt(tenant_id=user.tenant_id, diagnosis="untested", **body.model_dump())
    db.add(row)
    db.flush()
    _create_untested_slots(db, user, row)
    db.commit()
    return _prompt_out(_load_prompt(db, row.id))


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


@router.post("/prompt-panel/seed", response_model=GeoSeedOut)
def seed_prompt_panel(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> GeoSeedOut:
    existing = {
        _prompt_key(p.prompt_text, p.locale)
        for p in db.query(GeoPrompt).filter(GeoPrompt.tenant_id == user.tenant_id).all()
    }
    created = skipped = 0
    candidates: list[dict[str, str | None]] = []
    tenant = db.get(Tenant, user.tenant_id)
    seo_pages = db.query(SeoPage).filter(SeoPage.tenant_id == user.tenant_id).order_by(SeoPage.created_at.desc()).limit(12).all()
    for page in seo_pages:
        keyword = (page.target_keyword or page.title or "").strip()
        if not keyword:
            continue
        market = db.get(Market, page.market_id) if page.market_id else None
        candidates.extend(
            _prompt_pack_candidates(
                db,
                user,
                tenant=tenant,
                market=market,
                keyword=keyword,
                locale=page.locale,
                seo_page_id=page.id,
                limit_per_source=20,
            )
        )
    signals = (
        db.query(DemandSignal)
        .filter(DemandSignal.tenant_id == user.tenant_id)
        .order_by(DemandSignal.created_at.desc())
        .limit(12)
        .all()
    )
    for signal in signals:
        theme = (signal.theme or "").strip()
        if not theme:
            continue
        market = db.get(Market, signal.market_id) if signal.market_id else None
        candidates.extend(
            _prompt_pack_candidates(
                db,
                user,
                tenant=tenant,
                market=market,
                keyword=theme,
                locale=signal.locale,
                demand_signal_id=signal.id,
                limit_per_source=20,
            )
        )
    if not candidates:
        total = db.query(func.count(GeoPrompt.id)).filter(GeoPrompt.tenant_id == user.tenant_id).scalar() or 0
        return GeoSeedOut(created=0, skipped=0, prompts=total, note="没有可生成问句的 SEO 目标。请先在首页配置目标关键词，或在 SEO 选题里登记 target keyword。")
    for item in candidates:
        key = _prompt_key(str(item["prompt_text"]), str(item["locale"]))
        if key in existing:
            skipped += 1
            continue
        row = GeoPrompt(tenant_id=user.tenant_id, diagnosis="untested", **item)
        db.add(row)
        db.flush()
        _create_untested_slots(db, user, row)
        existing.add(key)
        created += 1
        if created >= 20:
            break
    db.commit()
    total = db.query(func.count(GeoPrompt.id)).filter(GeoPrompt.tenant_id == user.tenant_id).scalar() or 0
    note = "已按出口 B2B GEO 观测包生成 branded/category/competitor/task 问句。"
    if created == 0 and skipped > 0:
        note = "这些 SEO 目标已经生成过问句，本次没有新增。"
    return GeoSeedOut(created=created, skipped=skipped, prompts=total, note=note)


@router.patch("/prompts/{prompt_id}/diagnosis", response_model=GeoPromptOut)
def set_diagnosis(
    prompt_id: str,
    body: GeoDiagnosisIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GeoPromptOut:
    if body.diagnosis not in DIAGNOSES:
        raise HTTPException(status_code=400, detail="无效诊断层")
    row = db.get(GeoPrompt, prompt_id)
    if row is None or row.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="问句不存在")
    row.diagnosis = body.diagnosis
    db.commit()
    return _prompt_out(_load_prompt(db, row.id))


@router.patch("/observations/{obs_id}", response_model=GeoObservationOut)
def record_observation(
    obs_id: str,
    body: GeoObservationUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GeoObservationOut:
    if body.status not in OBS_STATUSES:
        raise HTTPException(status_code=400, detail="无效观测状态")
    row = db.get(GeoObservation, obs_id)
    if row is None or row.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="观测不存在")
    row.status = body.status
    if body.surface is not None:
        row.surface = body.surface
    if body.sample_type is not None:
        row.sample_type = body.sample_type
    if body.response_excerpt is not None:
        row.response_excerpt = body.response_excerpt
    if body.citation_urls is not None:
        row.citation_urls = body.citation_urls
    if body.brand_mentions is not None:
        row.brand_mentions = body.brand_mentions
    if body.competitor_mentions is not None:
        row.competitor_mentions = body.competitor_mentions
    if body.interpretation_note is not None:
        row.interpretation_note = body.interpretation_note
    row.notes = body.notes
    if body.status == "untested":
        row.observed_at = None
        row.observed_by = None
    else:
        row.observed_at = datetime.now(timezone.utc)
        row.observed_by = user.id
    db.commit()
    db.refresh(row)
    return _obs_out(row)


@router.get("/sample-runs", response_model=list[GeoSampleRunOut])
def list_sample_runs(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[GeoSampleRunOut]:
    rows = (
        db.query(GeoSampleRun)
        .options(selectinload(GeoSampleRun.results))
        .filter(GeoSampleRun.tenant_id == user.tenant_id)
        .order_by(GeoSampleRun.started_at.desc())
        .limit(12)
        .all()
    )
    return [_run_out(row, include_results=True) for row in rows]


@router.post("/sample-runs/from-observations", response_model=GeoSampleRunOut, status_code=201)
def create_sample_run_from_observations(
    body: GeoSampleRunCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GeoSampleRunOut:
    tenant = db.get(Tenant, user.tenant_id)
    rows = (
        db.query(GeoObservation)
        .join(GeoPrompt, GeoPrompt.id == GeoObservation.prompt_id)
        .filter(GeoObservation.tenant_id == user.tenant_id, GeoObservation.status.in_(RECORDED_OBS))
        .order_by(GeoPrompt.created_at.desc(), GeoObservation.engine.asc())
        .all()
    )
    if not rows:
        raise HTTPException(status_code=400, detail="还没有可沉淀为证据包的 GEO 观测。请先记录至少一条提及、未出现、引用或已核验。")

    prompts = {o.prompt_id: o.prompt for o in rows}
    languages = {p.locale for p in prompts.values() if p.locale}
    engines = sorted({o.engine for o in rows})
    prompt_pack_ids = {p.prompt_pack_id for p in prompts.values() if p.prompt_pack_id}
    prompt_set_id = body.prompt_set_id or (prompt_pack_ids.pop() if len(prompt_pack_ids) == 1 else "manual-panel")
    domain = tenant.site_origin if tenant else ""
    root = _root_domain(domain)
    brand_names = _tenant_brand_names(tenant)
    manifest = {
        "protocol_version": PROTOCOL_VERSION,
        "prompt_set_id": prompt_set_id,
        "domain": root or domain,
        "brand_names": brand_names,
        "prompt_ids": sorted((p.prompt_key or pid) for pid, p in prompts.items()),
        "engines": engines,
        "trials_per_prompt": 1,
        "language": body.language or (languages.pop() if len(languages) == 1 else "mixed"),
        "region_hint": body.region_hint,
    }
    config_hash = _sha256(json.dumps(manifest, sort_keys=True, ensure_ascii=False))[:16]
    now = datetime.now(timezone.utc)
    run = GeoSampleRun(
        tenant_id=user.tenant_id,
        protocol_version=PROTOCOL_VERSION,
        prompt_set_id=prompt_set_id,
        config_hash=config_hash,
        domain=root or domain,
        brand_names=_dump_list(brand_names),
        engines=_dump_list(engines),
        trials_per_prompt=1,
        region_hint=body.region_hint or "",
        language=manifest["language"],
        operator_id=user.id,
        status="done",
        note=body.note or "从人工记录的 GEO 观测生成证据运行。",
        started_at=now,
        finished_at=now,
    )
    db.add(run)
    db.flush()

    for index, obs in enumerate(rows, start=1):
        prompt = obs.prompt
        excerpt = obs.response_excerpt or obs.notes or ""
        citations = _split_urls(obs.citation_urls or "") + [
            u for u in _extract_urls(excerpt) if u not in _split_urls(obs.citation_urls or "")
        ]
        owned = [url for url in citations if _is_owned_url(url, root, [])]
        third_party = [url for url in citations if url not in owned]
        tier = _evidence_tier(obs)
        evidence_id = f"ev_{run.id[:8]}_{obs.id[:8]}"
        result = GeoSampleResult(
            tenant_id=user.tenant_id,
            run_id=run.id,
            prompt_id=prompt.id,
            observation_id=obs.id,
            evidence_id=evidence_id,
            trial_index=1,
            prompt_type=prompt.prompt_type or "custom",
            engine=obs.engine,
            model="manual",
            web_grounded="unknown",
            surface=obs.surface or "manual_ai_answer",
            prompt_text_hash=_sha256(prompt.prompt_text),
            answer_text_hash=_sha256(excerpt),
            answer_excerpt=excerpt[:2000],
            mentioned=tier in {"mentioned", "cited", "verified"},
            citations_json=_dump_list(citations),
            owned_citations_json=_dump_list(owned),
            third_party_citations_json=_dump_list(third_party),
            brand_hits=obs.brand_mentions or "",
            competitor_hits=obs.competitor_mentions or "",
            verification_status="passed" if tier == "verified" else ("pending" if owned else "skipped"),
            verification_note=obs.interpretation_note or "",
            sampled_at=obs.observed_at or now,
        )
        db.add(result)
        # Preserve a short evidence pointer on the manual observation without overwriting raw notes.
        marker = f"evidence_id={evidence_id}; run_id={run.id}; protocol={PROTOCOL_VERSION}"
        obs.interpretation_note = "\n".join([x for x in [obs.interpretation_note, marker] if x])

    db.commit()
    refreshed = (
        db.query(GeoSampleRun)
        .options(selectinload(GeoSampleRun.results))
        .filter(GeoSampleRun.id == run.id)
        .one()
    )
    return _run_out(refreshed, include_results=True)


def _brand_mentioned(text: str, brand_names: list[str]) -> tuple[bool, str]:
    lower = (text or "").lower()
    hits = [name for name in brand_names if name and name.lower() in lower]
    return bool(hits), ", ".join(hits)


@router.post("/sample-runs/auto", response_model=GeoSampleRunOut, status_code=201)
def create_auto_sample_run(
    body: GeoAutoSampleIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GeoSampleRunOut:
    tenant = db.get(Tenant, user.tenant_id)
    q = db.query(GeoPrompt).filter(GeoPrompt.tenant_id == user.tenant_id)
    if body.prompt_ids:
        q = q.filter(GeoPrompt.id.in_(body.prompt_ids))
    prompts = q.order_by(GeoPrompt.created_at.desc()).limit(body.limit).all()
    if not prompts:
        raise HTTPException(status_code=400, detail="没有可自动采样的 GEO 问句。")
    provider_key = body.provider or body.engine or "deepseek"
    engines = [provider_key]
    domain = tenant.site_origin if tenant else ""
    root = _root_domain(domain)
    brand_names = _tenant_brand_names(tenant)
    prompt_set_id = prompts[0].prompt_pack_id or EXPORT_B2B_PACK_ID
    manifest = {
        "protocol_version": PROTOCOL_VERSION,
        "prompt_set_id": prompt_set_id,
        "domain": root or domain,
        "brand_names": brand_names,
        "prompt_ids": [p.prompt_key or p.id for p in prompts],
        "engines": engines,
        "trials_per_prompt": body.trials,
        "language": "mixed" if len({p.locale for p in prompts}) > 1 else prompts[0].locale,
        "region_hint": body.region_hint,
        "web_grounded": body.web_grounded,
        "provider": provider_key,
    }
    config_hash = _sha256(json.dumps(manifest, sort_keys=True, ensure_ascii=False))[:16]
    now = datetime.now(timezone.utc)
    run = GeoSampleRun(
        tenant_id=user.tenant_id,
        protocol_version=PROTOCOL_VERSION,
        prompt_set_id=prompt_set_id,
        config_hash=config_hash,
        domain=root or domain,
        brand_names=_dump_list(brand_names),
        engines=_dump_list(engines),
        trials_per_prompt=body.trials,
        region_hint=body.region_hint or "",
        language=str(manifest["language"]),
        operator_id=user.id,
        status="running",
        note="自动 GEO provider 采样；DeepSeek/普通 LLM 不计入真实联网引用。",
        started_at=now,
    )
    db.add(run)
    db.flush()

    result_count = 0
    errors: list[str] = []
    for prompt in prompts:
        for trial in range(1, body.trials + 1):
            try:
                sampled = sample_with_provider(
                    provider_key,
                    prompt_text=prompt.prompt_text,
                    model=body.model,
                    region_hint=body.region_hint,
                )
            except GeoProviderError as exc:
                errors.append(f"{prompt.prompt_key or prompt.id} trial {trial}: {exc}")
                continue
            text = sampled.answer[:4000]
            citations = sampled.citations if sampled.web_grounded else []
            if not citations and sampled.web_grounded:
                citations = _extract_urls(text)
            owned = [url for url in citations if _is_owned_url(url, root, [])]
            third_party = [url for url in citations if url not in owned]
            mentioned, brand_hits = _brand_mentioned(text, brand_names)
            evidence_id = f"ev_{run.id[:8]}_{prompt.id[:8]}_{trial}"
            db.add(
                GeoSampleResult(
                    tenant_id=user.tenant_id,
                    run_id=run.id,
                    prompt_id=prompt.id,
                    observation_id=None,
                    evidence_id=evidence_id,
                    trial_index=trial,
                    prompt_type=prompt.prompt_type or "custom",
                    engine=sampled.engine,
                    model=sampled.model,
                    web_grounded="true" if sampled.web_grounded else "false",
                    surface=sampled.surface,
                    prompt_text_hash=_sha256(prompt.prompt_text),
                    answer_text_hash=_sha256(text),
                    answer_excerpt=text[:2000],
                    mentioned=mentioned,
                    citations_json=_dump_list(citations),
                    owned_citations_json=_dump_list(owned),
                    third_party_citations_json=_dump_list(third_party),
                    brand_hits=brand_hits,
                    competitor_hits="",
                    verification_status="pending" if owned else "skipped",
                    verification_note="联网 provider 引用仍需 URL 访问核验。" if sampled.web_grounded else "DeepSeek/LLM 非联网采样；不计入真实 citation。",
                    sampled_at=datetime.now(timezone.utc),
                )
            )
            result_count += 1

    run.status = "done" if result_count else "failed"
    run.finished_at = datetime.now(timezone.utc)
    if errors:
        run.note = f"{run.note}\n失败 {len(errors)} 条：" + "\n".join(errors[:5])
    db.commit()
    refreshed = (
        db.query(GeoSampleRun)
        .options(selectinload(GeoSampleRun.results).selectinload(GeoSampleResult.prompt))
        .filter(GeoSampleRun.id == run.id)
        .one()
    )
    return _run_out(refreshed, include_results=True)


def _ticket_exists(db: Session, tenant_id: str, prompt_id: str, title: str) -> bool:
    return (
        db.query(func.count(GeoTicket.id))
        .filter(GeoTicket.tenant_id == tenant_id, GeoTicket.prompt_id == prompt_id, GeoTicket.title == title)
        .scalar()
        or 0
    ) > 0


def _aggregate_issue_specs(runs: list[GeoSampleRun]) -> list[dict]:
    aggregates = [_sample_aggregate(run) for run in runs if run.results]
    cat_rates: list[float] = []
    branded_rates: list[float] = []
    owned_rates: list[float] = []
    third_party_domains: dict[str, int] = {}
    run_ids: list[str] = []
    for aggregate in aggregates:
        if aggregate.get("run_id"):
            run_ids.append(str(aggregate["run_id"]))
        for row in aggregate.get("byPrompt") or []:
            if int(row.get("trials") or 0) < 3:
                continue
            ptype = row.get("type")
            if ptype == "category":
                cat_rates.append(float(row.get("mention_rate") or 0))
                owned_rates.append(float(row.get("owned_citation_rate") or 0))
            elif ptype == "branded":
                branded_rates.append(float(row.get("mention_rate") or 0))
            if ptype in {"category", "competitor"}:
                for host in row.get("top_third_party_domains") or []:
                    third_party_domains[host] = third_party_domains.get(host, 0) + 1

    specs: list[dict] = []
    if cat_rates:
        category_mean = sum(cat_rates) / len(cat_rates)
        branded_mean = sum(branded_rates) / len(branded_rates) if branded_rates else None
        if category_mean < 0.2:
            specs.append(
                {
                    "title": "GEO-ENT-003 品类问题下品牌关联弱",
                    "diagnosis": "absent",
                    "rationale": (
                        f"按 {PROTOCOL_VERSION} 聚合，category mention 均值 {category_mean:.3f}，"
                        f"低于 0.2 阈值；run={', '.join(run_ids)}。"
                    ),
                    "acceptance": "补品类词与品牌共现、参数/认证/应用页，并以 category prompt trials>=3 复测。",
                    "evidence": {
                        "issue_id": "GEO-ENT-003",
                        "category_mention_mean": round(category_mean, 3),
                        "branded_mention_mean": None if branded_mean is None else round(branded_mean, 3),
                        "threshold": 0.2,
                        "run_ids": run_ids,
                    },
                }
            )
    if third_party_domains:
        owned_mean = sum(owned_rates) / len(owned_rates) if owned_rates else 0.0
        if owned_mean <= 0.15:
            top_domains = sorted(third_party_domains.items(), key=lambda item: item[1], reverse=True)[:10]
            specs.append(
                {
                    "title": "GEO-OFF-001 权威第三方源高频出现但自有引用弱",
                    "diagnosis": "competitor_dominated",
                    "rationale": (
                        f"category/competitor 采样中外域高频出现，自有引用均值 {owned_mean:.3f}；"
                        f"代表域：{', '.join(host for host, _ in top_domains)}。"
                    ),
                    "acceptance": "按源类型完善档案、认证、品类标签和官网规格页链接；复测 third-party domains 与 owned citation。",
                    "evidence": {
                        "issue_id": "GEO-OFF-001",
                        "top_domains": top_domains,
                        "owned_citation_mean": round(owned_mean, 3),
                        "threshold": 0.15,
                        "run_ids": run_ids,
                    },
                }
            )
    return specs


@router.post("/tickets/draft-from-evidence", response_model=GeoTicketDraftOut)
def draft_tickets_from_evidence(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GeoTicketDraftOut:
    prompts = (
        db.query(GeoPrompt)
        .options(selectinload(GeoPrompt.observations))
        .filter(GeoPrompt.tenant_id == user.tenant_id)
        .order_by(GeoPrompt.created_at.desc())
        .all()
    )
    created = skipped = 0
    made: list[GeoTicket] = []
    latest_runs = (
        db.query(GeoSampleRun)
        .options(selectinload(GeoSampleRun.results).selectinload(GeoSampleResult.prompt))
        .filter(GeoSampleRun.tenant_id == user.tenant_id)
        .order_by(GeoSampleRun.started_at.desc())
        .limit(5)
        .all()
    )
    aggregate_specs = _aggregate_issue_specs(latest_runs)
    anchor_prompt = prompts[0] if prompts else None
    for spec in aggregate_specs:
        if anchor_prompt is None:
            continue
        if _ticket_exists(db, user.tenant_id, anchor_prompt.id, spec["title"]):
            skipped += 1
            continue
        ticket = GeoTicket(
            tenant_id=user.tenant_id,
            prompt_id=anchor_prompt.id,
            title=spec["title"],
            diagnosis=spec["diagnosis"],
            rationale=spec["rationale"],
            acceptance_criteria=spec["acceptance"],
            status="open",
            evidence=json.dumps(spec["evidence"], ensure_ascii=False, indent=2),
        )
        db.add(ticket)
        made.append(ticket)
        created += 1
    for prompt in prompts:
        recorded = [o for o in prompt.observations if o.status in RECORDED_OBS]
        if not recorded:
            continue
        tiers = [_evidence_tier(o) for o in recorded]
        competitor_hits = [o for o in recorded if (o.competitor_mentions or "").strip()]
        rules: list[tuple[str, str, str, str]] = []
        if all(t == "none" for t in tiers):
            rules.append((
                "GEO-ENT-003 品类问句未出现客户",
                "absent",
                "已记录的引擎结果均未出现客户品牌或自有引用，属于品类关联弱的初步信号。",
                "补充该问句对应的权威说明页/产品页，文首 400 字写清品类、适用场景、差异化和可引用事实；复测同一问句至少 3 次。",
            ))
        if any(t == "mentioned" for t in tiers) and not any(t in {"cited", "verified"} for t in tiers):
            rules.append((
                "GEO-MEAS-002 仅被提及但没有自有引用",
                "mentioned",
                "AI 回答能提到客户，但没有指向自有域 URL，说明可引用资产或来源信号不足。",
                "为相关页面补可引用小节、FAQ、Schema、来源日期和清晰 canonical；复测 owned citation rate。",
            ))
        if any(t == "cited" for t in tiers) and not any(t == "verified" for t in tiers):
            rules.append((
                "GEO-MEAS-005 引用尚未核验",
                "mentioned",
                "已有 citation 记录，但尚未完成 URL 可访问和内容一致性核验，不能写成已核实引用。",
                "打开 citation URL，记录 HTTP 状态、最终 URL 和页面截图或摘要；通过后标记为引用已核验。",
            ))
        if competitor_hits:
            rules.append((
                "GEO-OFF-001 竞品在回答中占位",
                "competitor_dominated",
                "采样回答出现竞品或替代品牌，需要判断竞品为什么被模型吸收或引用。",
                "整理竞品被提及/引用的页面类型，补客户侧对比页、案例、参数表和第三方入围机会；复测竞品提及率。",
            ))
        if len(recorded) < 3:
            rules.append((
                "GEO-MEAS-003 采样次数不足",
                prompt.diagnosis if prompt.diagnosis != "untested" else "untested",
                "当前记录少于 3 次 trial，不能作为稳定 GEO 结论。",
                "按同一 prompt、同一引擎和同一地区至少记录 3 次；正式报告建议 5 次。",
            ))
        for title, diagnosis, rationale, acceptance in rules:
            if _ticket_exists(db, user.tenant_id, prompt.id, title):
                skipped += 1
                continue
            ticket = GeoTicket(
                tenant_id=user.tenant_id,
                prompt_id=prompt.id,
                title=title,
                diagnosis=diagnosis,
                rationale=rationale,
                acceptance_criteria=acceptance,
                status="open",
                evidence=f"prompt_id={prompt.id}\nrecorded_slots={len(recorded)}\nprotocol={PROTOCOL_VERSION}",
            )
            db.add(ticket)
            made.append(ticket)
            created += 1
    db.commit()
    for ticket in made:
        db.refresh(ticket)
    note = "已按 GEO 规则生成整改工单草稿。" if created else "没有新增工单；可能暂无观测，或相关工单已存在。"
    return GeoTicketDraftOut(created=created, skipped=skipped, note=note, tickets=[_ticket_out(t) for t in made])


@router.get("/report", response_model=GeoReportOut)
def geo_report(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> GeoReportOut:
    tenant = db.get(Tenant, user.tenant_id)
    prompts = (
        db.query(GeoPrompt)
        .options(selectinload(GeoPrompt.observations))
        .filter(GeoPrompt.tenant_id == user.tenant_id)
        .order_by(GeoPrompt.created_at.desc())
        .all()
    )
    runs = (
        db.query(GeoSampleRun)
        .options(selectinload(GeoSampleRun.results))
        .filter(GeoSampleRun.tenant_id == user.tenant_id)
        .order_by(GeoSampleRun.started_at.desc())
        .limit(5)
        .all()
    )
    summary = geo_summary(user, db)
    generated = datetime.now(timezone.utc)
    lines = [
        f"# GEO 可见性诊断报告 - {tenant.name if tenant else ''}",
        "",
        "## 一句话结论",
        "",
        f"本次共有 {summary.prompts} 个采样问句，已记录 {summary.recorded} 个引擎结果，未测 {summary.untested} 个。品牌提及率 {summary.mention_rate}，官网引用率 {summary.cite_rate}，已核验引用率 {summary.verified_citation_rate}。",
        "",
        "## 口径说明",
        "",
        "- 引用率：AI 答案明确给出客户官网或客户内容作为 citation/source 的比例。",
        "- 已核验引用率：人工确认 citation URL 可访问，且确属客户官网或客户可控资产。",
        "- 吸收率：AI 答案提及客户品牌、产品或引用客户内容的比例；吸收不等于引用。",
        "- 竞品提及：答案中出现竞品或替代品牌，需要人工判断是否进入内容/PR/外链任务。",
        "- 未测项不会按 0 计算，不编造 AI 可见性。",
        "",
        "## 总览",
        "",
        f"- 问句数：{summary.prompts}",
        f"- 已记录采样：{summary.recorded}",
        f"- 未测槽位：{summary.untested}",
        f"- 品牌提及率：{summary.mention_rate}",
        f"- 引用率：{summary.cite_rate}",
        f"- 已核验引用率：{summary.verified_citation_rate}",
        f"- 吸收率：{summary.absorption_rate}",
        f"- 竞品提及率：{summary.competitor_rate}",
        f"- 竞品提及槽位：{summary.competitor_mentions}",
        f"- 证据运行：{summary.sample_runs}",
        f"- 证据条目：{summary.evidence_results}",
        "",
        "## 证据运行",
        "",
    ]
    if not runs:
        lines += [
            "- 暂无证据运行。当前报告只能作为内部草稿，建议先点击“生成证据运行”。",
            "",
        ]
    for run in runs:
        run_out = _run_out(run, include_results=False)
        lines += [
            f"### Run {run.id}",
            "",
            f"- 协议：{run.protocol_version}",
            f"- config_hash：{run.config_hash}",
            f"- 域名：{run.domain or '未设置'}",
            f"- 引擎：{', '.join(run_out.engines) or '未记录'}",
            f"- 结果数：{run_out.results_count}",
            f"- 提及率：{run_out.mention_rate}",
            f"- 自有引用率：{run_out.cite_rate}",
            f"- 已核验引用率：{run_out.verified_citation_rate}",
            f"- 备注：{run.note or '无'}",
            "",
        ]
        for result in run.results[:8]:
            lines.append(
                f"- {result.evidence_id} · {ENGINE_LABELS.get(result.engine, result.engine)} · owned citations: {', '.join(_json_list(result.owned_citations_json)) or '无'} · verification: {result.verification_status}"
            )
        lines.append("")
    lines += [
        "## 问句明细",
        "",
    ]
    if not prompts:
        lines.append("- 暂无 GEO 问句。")
    for prompt in prompts:
        rates = _prompt_rates(prompt.observations)
        lines += [
            f"### {prompt.prompt_key or prompt.id} · {prompt.prompt_type or 'custom'} · {prompt.prompt_text}",
            "",
            f"- 语言/市场：{prompt.locale}",
            f"- Prompt 包：{prompt.prompt_pack_id or 'custom'}",
            f"- 诊断层：{DIAGNOSES.get(prompt.diagnosis, prompt.diagnosis)}",
            f"- 品牌提及率：{rates['mention_rate']}",
            f"- 官网引用率：{rates['cite_rate']}",
            f"- 已核验引用率：{rates['verified_citation_rate']}",
            f"- 竞品提及率：{rates['competitor_rate']}",
            "",
        ]
        for obs in prompt.observations:
            if obs.status == "untested":
                continue
            evidence = obs.response_excerpt or obs.notes or "已记录，无回答摘录。"
            lines.append(
                f"- {ENGINE_LABELS.get(obs.engine, obs.engine)}：{obs.status} / {EVIDENCE_LABELS.get(_evidence_tier(obs), '无证据')}；引用：{obs.citation_urls or '无'}；品牌提及：{obs.brand_mentions or '无'}；竞品：{obs.competitor_mentions or '无'}；证据：{evidence[:260]}"
            )
        lines.append("")
    lines += [
        "## 下一步建议",
        "",
        "1. 优先补测未测槽位，保持同一问句、同一地区和同一表面类型。",
        "2. 对竞品主导问句，回到 SEO 页面补充可引用结论、案例、参数和权威来源。",
        "3. 对被提及但未引用的问句，检查页面是否有清晰来源、作者、日期、结构化数据和可引用段落。",
        "4. 每轮内容上线后重新采样，形成 GEO 复测记录。",
    ]
    return GeoReportOut(title=f"GEO 可见性诊断报告 - {tenant.name if tenant else ''}", markdown="\n".join(lines), generated_at=generated)


@router.get("/report-table", response_model=GeoReportTableOut)
def geo_report_table(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> GeoReportTableOut:
    prompts = (
        db.query(GeoPrompt)
        .options(selectinload(GeoPrompt.observations))
        .filter(GeoPrompt.tenant_id == user.tenant_id)
        .order_by(GeoPrompt.created_at.desc())
        .all()
    )
    sample_results = (
        db.query(GeoSampleResult)
        .join(GeoSampleRun, GeoSampleRun.id == GeoSampleResult.run_id)
        .filter(GeoSampleResult.tenant_id == user.tenant_id)
        .order_by(GeoSampleResult.sampled_at.desc())
        .all()
    )
    generated = datetime.now(timezone.utc)
    out = StringIO()
    writer = csv.writer(out)
    writer.writerow([
        "问句",
        "Prompt ID",
        "Prompt 类型",
        "Prompt 包",
        "语言",
        "诊断层",
        "引擎",
        "地区",
        "表面类型",
        "采样方式",
        "状态",
        "证据层级",
        "证据说明",
        "引用URL",
        "品牌提及",
        "竞品提及",
        "回答摘录",
        "解释备注",
        "采样时间",
        "run_id",
        "evidence_id",
        "prompt_hash",
        "answer_hash",
        "自有引用",
        "第三方引用",
        "核验状态",
    ])
    result_by_obs = {r.observation_id: r for r in sample_results if r.observation_id}
    for prompt in prompts:
        for obs in prompt.observations:
            result = result_by_obs.get(obs.id)
            writer.writerow([
                prompt.prompt_text,
                prompt.prompt_key or prompt.id,
                prompt.prompt_type or "custom",
                prompt.prompt_pack_id or "custom",
                prompt.locale,
                DIAGNOSES.get(prompt.diagnosis, prompt.diagnosis),
                ENGINE_LABELS.get(obs.engine, obs.engine),
                engine_region(obs.engine),
                obs.surface or "manual_ai_answer",
                obs.sample_type or "manual",
                obs.status,
                _evidence_tier(obs),
                EVIDENCE_LABELS.get(_evidence_tier(obs), "无证据"),
                obs.citation_urls or "",
                obs.brand_mentions or "",
                obs.competitor_mentions or "",
                (obs.response_excerpt or "").replace("\n", " ")[:500],
                obs.interpretation_note or obs.notes or "",
                obs.observed_at.isoformat() if obs.observed_at else "",
                result.run_id if result else "",
                result.evidence_id if result else "",
                result.prompt_text_hash if result else "",
                result.answer_text_hash if result else "",
                "; ".join(_json_list(result.owned_citations_json)) if result else "",
                "; ".join(_json_list(result.third_party_citations_json)) if result else "",
                result.verification_status if result else "",
            ])
    return GeoReportTableOut(filename=f"geo采样证据表-{generated.date().isoformat()}.csv", csv=out.getvalue(), generated_at=generated)


@router.get("/tickets", response_model=list[GeoTicketOut])
def list_tickets(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[GeoTicketOut]:
    rows = (
        db.query(GeoTicket)
        .filter(GeoTicket.tenant_id == user.tenant_id)
        .order_by(GeoTicket.created_at.desc())
        .all()
    )
    return [_ticket_out(r) for r in rows]


@router.post("/tickets", response_model=GeoTicketOut, status_code=201)
def create_ticket(
    body: GeoTicketCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GeoTicketOut:
    prompt = db.get(GeoPrompt, body.prompt_id)
    if prompt is None or prompt.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="问句不存在")
    if body.diagnosis not in DIAGNOSES:
        raise HTTPException(status_code=400, detail="无效诊断层")
    row = GeoTicket(
        tenant_id=user.tenant_id,
        prompt_id=prompt.id,
        title=body.title,
        diagnosis=body.diagnosis,
        rationale=body.rationale,
        acceptance_criteria=body.acceptance_criteria,
        status="open",
    )
    db.add(row)
    if prompt.diagnosis == "untested" and body.diagnosis != "untested":
        prompt.diagnosis = body.diagnosis
    db.commit()
    db.refresh(row)
    return _ticket_out(row)


@router.post("/tickets/{ticket_id}/verify", response_model=GeoTicketOut)
def verify_ticket(
    ticket_id: str,
    body: GeoTicketVerifyIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GeoTicketOut:
    require_confirm(body.confirmed, action="验收 GEO 工单")
    row = db.get(GeoTicket, ticket_id)
    if row is None or row.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="工单不存在")
    row.status = "done"
    row.verified_note = body.note or "客户经理已按验收标准人工复核。"
    db.commit()
    db.refresh(row)
    return _ticket_out(row)


@router.post("/tickets/{ticket_id}/reopen", response_model=GeoTicketOut)
def reopen_ticket(
    ticket_id: str,
    body: GeoTicketVerifyIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GeoTicketOut:
    row = db.get(GeoTicket, ticket_id)
    if row is None or row.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="工单不存在")
    if row.status not in TICKET_STATUSES:
        raise HTTPException(status_code=400, detail="无效工单状态")
    row.status = "reopened"
    if body.note:
        row.verified_note = body.note
    db.commit()
    db.refresh(row)
    return _ticket_out(row)


@router.get("/assets", response_model=list[GeoAssetOut])
def list_assets(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[GeoAsset]:
    return db.query(GeoAsset).filter(GeoAsset.tenant_id == user.tenant_id).all()


@router.post("/assets/llms.txt/generate", response_model=GeoAssetOut)
def generate_llms_txt(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> GeoAsset:
    tenant = db.get(Tenant, user.tenant_id)
    pages = db.query(SeoPage).filter(SeoPage.tenant_id == user.tenant_id).all()
    body = build_llms_txt(tenant, pages) if tenant else ""
    asset = db.query(GeoAsset).filter(GeoAsset.tenant_id == user.tenant_id, GeoAsset.kind == "llms_txt").first()
    if asset is None:
        asset = GeoAsset(tenant_id=user.tenant_id, kind="llms_txt", title="llms.txt 草稿")
        db.add(asset)
    asset.body = body
    asset.status = "draft"
    asset.updated_by = user.id
    db.commit()
    db.refresh(asset)
    return asset


@router.patch("/assets/{asset_id}", response_model=GeoAssetOut)
def update_asset(
    asset_id: str,
    body: GeoAssetUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GeoAsset:
    asset = db.get(GeoAsset, asset_id)
    if asset is None or asset.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="资产不存在")
    asset.body = body.body
    asset.status = "draft"
    asset.updated_by = user.id
    db.commit()
    db.refresh(asset)
    return asset


@router.post("/assets/{asset_id}/mark-ready", response_model=GeoAssetOut)
def mark_asset_ready(
    asset_id: str,
    body: ConfirmReadyIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GeoAsset:
    if not body.confirmed:
        raise HTTPException(status_code=400, detail="需要客户经理人工确认后才能标记可交付")
    asset = db.get(GeoAsset, asset_id)
    if asset is None or asset.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="资产不存在")
    if not asset.body.strip():
        raise HTTPException(status_code=400, detail="正文为空，不能标记可交付")
    asset.status = "ready"
    asset.updated_by = user.id
    db.commit()
    db.refresh(asset)
    return asset


@router.post("/checklists/ensure", response_model=list[GeoChecklistItemOut])
def ensure_checklist(
    seo_page_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[GeoChecklistItem]:
    page = db.get(SeoPage, seo_page_id)
    if page is None or page.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="选题不存在")
    existing = {
        i.item_key: i
        for i in db.query(GeoChecklistItem).filter(GeoChecklistItem.seo_page_id == seo_page_id).all()
    }
    for key, label in CHECKLIST_DEFS:
        if key not in existing:
            db.add(
                GeoChecklistItem(
                    tenant_id=user.tenant_id,
                    seo_page_id=seo_page_id,
                    item_key=key,
                    label=label,
                    status="untested",
                )
            )
    db.commit()
    return (
        db.query(GeoChecklistItem)
        .filter(GeoChecklistItem.seo_page_id == seo_page_id)
        .order_by(GeoChecklistItem.item_key)
        .all()
    )


@router.patch("/checklist-items/{item_id}", response_model=GeoChecklistItemOut)
def update_checklist_item(
    item_id: str,
    body: GeoChecklistItemUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GeoChecklistItem:
    if body.status not in CHECK_STATUSES:
        raise HTTPException(status_code=400, detail="无效清单状态")
    row = db.get(GeoChecklistItem, item_id)
    if row is None or row.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="清单项不存在")
    row.status = body.status
    row.notes = body.notes
    db.commit()
    db.refresh(row)
    return row


@router.post("/from-demand-signal/{signal_id}", response_model=GeoPromptOut, status_code=201)
def prompt_from_signal(
    signal_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GeoPromptOut:
    signal = db.get(DemandSignal, signal_id)
    if signal is None or signal.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="需求信号不存在")
    row = GeoPrompt(
        tenant_id=user.tenant_id,
        market_id=signal.market_id,
        demand_signal_id=signal.id,
        prompt_text=signal.theme,
        locale=signal.locale,
        diagnosis="untested",
    )
    db.add(row)
    db.flush()
    _create_untested_slots(db, user, row)
    db.commit()
    return _prompt_out(_load_prompt(db, row.id))


@router.post("/prompts/{prompt_id}/ai", response_model=AiAssistOut)
def ai_prompt(
    prompt_id: str,
    body: AiStepIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AiAssistOut:
    row = (
        db.query(GeoPrompt)
        .options(selectinload(GeoPrompt.observations))
        .filter(GeoPrompt.id == prompt_id, GeoPrompt.tenant_id == user.tenant_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="问句不存在")
    payload = assist_geo_prompt(db, row, step=body.step)
    db.commit()
    return AiAssistOut(**payload)


@router.post("/tickets/{ticket_id}/ai", response_model=AiAssistOut)
def ai_ticket(
    ticket_id: str,
    body: AiStepIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AiAssistOut:
    row = db.get(GeoTicket, ticket_id)
    if row is None or row.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="工单不存在")
    payload = assist_geo_ticket(db, row, step=body.step or "review")
    db.commit()
    return AiAssistOut(**payload)


@router.post("/assets/{asset_id}/ai", response_model=AiAssistOut)
def ai_asset(
    asset_id: str,
    body: AiStepIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AiAssistOut:
    row = db.get(GeoAsset, asset_id)
    if row is None or row.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="资产不存在")
    payload = assist_geo_asset(db, row, step=body.step or "content")
    db.commit()
    return AiAssistOut(**payload)
