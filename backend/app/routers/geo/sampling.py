import json
from datetime import datetime, timezone

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.auth import get_current_user
from app.database import get_db
from app.geo_loop import apply_loop_spec, kinds_from_sample_rows, loop_ticket_spec, pick_sample_batches, write_ticket_retest
from app.geo_providers import GeoProviderError, configured_implemented_grounded
from app.models import (
    GeoObservation,
    GeoPrompt,
    GeoSampleResult,
    GeoSampleRun,
    GeoTicket,
    Tenant,
    User,
)
from app.schemas import (
    GeoAutoSampleIn,
    GeoGroundedBatchOut,
    GeoSampleRunCreate,
    GeoSampleRunOut,
    GeoTicketDraftOut,
)

import app.routers.geo as _geo_pkg

from . import router
from .common import (
    _brand_mentioned,
    _dump_list,
    _evidence_tier,
    _extract_urls,
    _is_owned_url,
    _json_list,
    _root_domain,
    _run_out,
    _sha256,
    _split_urls,
    _tenant_brand_names,
    _ticket_exists,
    _ticket_out,
)
from .constants import EXPORT_B2B_PACK_ID, PROTOCOL_VERSION, RECORDED_OBS


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


def _load_sample_prompts(db: Session, user: User, body: GeoAutoSampleIn) -> list[GeoPrompt]:
    q = db.query(GeoPrompt).filter(GeoPrompt.tenant_id == user.tenant_id)
    if body.prompt_ids:
        q = q.filter(GeoPrompt.id.in_(body.prompt_ids))
    prompts = q.order_by(GeoPrompt.created_at.desc()).limit(body.limit).all()
    if not prompts:
        raise HTTPException(status_code=400, detail="没有可自动采样的 GEO 问句。")
    return prompts


def _execute_auto_sample(
    *,
    db: Session,
    user: User,
    tenant: Tenant | None,
    prompts: list[GeoPrompt],
    provider_key: str,
    body: GeoAutoSampleIn,
) -> GeoSampleRun:
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

    from app.usage import UsageLimitError, assert_can, meter_for_provider, raise_http

    meter = meter_for_provider(provider_key)
    try:
        assert_can(db, user.tenant_id, meter, len(prompts) * max(1, body.trials))
    except UsageLimitError as exc:
        raise_http(exc)

    result_count = 0
    errors: list[str] = []
    for prompt in prompts:
        for trial in range(1, body.trials + 1):
            try:
                sampled = _geo_pkg.sample_with_provider(
                    provider_key,
                    prompt_text=prompt.prompt_text,
                    model=body.model,
                    region_hint=body.region_hint,
                )
            except UsageLimitError as exc:
                raise_http(exc)
            except GeoProviderError as exc:
                errors.append(f"{provider_key} {prompt.prompt_key or prompt.id} trial {trial}: {exc}")
                continue
            text = sampled.answer[:4000]
            citations = sampled.citations if sampled.web_grounded else []
            if not citations and sampled.web_grounded:
                citations = _extract_urls(text)
            owned = [url for url in citations if _is_owned_url(url, root, [])]
            third_party = [url for url in citations if url not in owned]
            mentioned, brand_hits = _brand_mentioned(text, brand_names)
            evidence_id = f"ev_{run.id[:8]}_{prompt.id[:8]}_{sampled.engine}_{trial}"
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
    return (
        db.query(GeoSampleRun)
        .options(selectinload(GeoSampleRun.results).selectinload(GeoSampleResult.prompt))
        .filter(GeoSampleRun.id == run.id)
        .one()
    )


def _latest_sample_run(db: Session, tenant_id: str) -> GeoSampleRun | None:
    return (
        db.query(GeoSampleRun)
        .options(selectinload(GeoSampleRun.results))
        .filter(GeoSampleRun.tenant_id == tenant_id)
        .order_by(GeoSampleRun.started_at.desc())
        .first()
    )


def _record_retest(
    db: Session,
    tenant_id: str,
    latest: GeoSampleRun | list[GeoSampleRun] | None,
    previous: GeoSampleRun | list[GeoSampleRun] | None,
) -> None:
    if write_ticket_retest(db, tenant_id, latest, previous):
        db.commit()


@router.post("/sample-runs/auto", response_model=GeoSampleRunOut, status_code=201)
def create_auto_sample_run(
    body: GeoAutoSampleIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GeoSampleRunOut:
    tenant = db.get(Tenant, user.tenant_id)
    prompts = _load_sample_prompts(db, user, body)
    previous = _latest_sample_run(db, user.tenant_id)
    run = _execute_auto_sample(
        db=db,
        user=user,
        tenant=tenant,
        prompts=prompts,
        provider_key=body.provider or body.engine or "deepseek",
        body=body,
    )
    _record_retest(db, user.tenant_id, run, previous)
    return _run_out(run, include_results=True)


@router.post("/sample-runs/auto-grounded", response_model=GeoGroundedBatchOut, status_code=201)
def create_grounded_batch_runs(
    body: GeoAutoSampleIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GeoGroundedBatchOut:
    ready = configured_implemented_grounded()
    if not ready:
        raise HTTPException(status_code=400, detail="没有已配置、能联网返回网址的数据源。DeepSeek 不算。")
    tenant = db.get(Tenant, user.tenant_id)
    prompts = _load_sample_prompts(db, user, body)
    from app.usage import UsageLimitError, assert_can, meter_for_provider, raise_http

    need = len(prompts) * max(1, body.trials)
    try:
        for provider in ready:
            meter = meter_for_provider(provider.key)
            assert_can(db, user.tenant_id, meter, need)
    except UsageLimitError as exc:
        raise_http(exc)
    previous = _latest_sample_run(db, user.tenant_id)
    runs = []
    made: list[GeoSampleRun] = []
    failed: list[str] = []
    results_count = 0
    for provider in ready:
        grounded_body = body.model_copy(update={"provider": provider.key, "engine": provider.key, "web_grounded": "true"})
        run = _execute_auto_sample(
            db=db,
            user=user,
            tenant=tenant,
            prompts=prompts,
            provider_key=provider.key,
            body=grounded_body,
        )
        made.append(run)
        runs.append(_run_out(run, include_results=True))
        results_count += len(run.results)
        if run.status != "done":
            failed.append(provider.label)
    _record_retest(db, user.tenant_id, made, previous)
    labels = [row.label for row in ready]
    note = f"已对 {len(ready)} 个联网源各抽一轮：{'、'.join(labels)}。DeepSeek 没跑，不算给出官网。"
    if failed:
        note += f" 其中失败：{'、'.join(failed)}。"
    if any(len(run.results) == 0 for run in made):
        note += " 有的源这次没有写出记录，看该批次备注，不要把空批次的「未测」写成结论。"
    return GeoGroundedBatchOut(
        providers=[row.key for row in ready],
        results_count=results_count,
        failed=failed,
        note=note,
        runs=runs,
    )


def _add_loop_ticket(
    db: Session,
    user: User,
    prompt: GeoPrompt,
    kind: str,
    *,
    third_party: bool,
    made: list[GeoTicket],
    sample_rows: list[GeoSampleResult] | None = None,
) -> str:
    spec = loop_ticket_spec(
        db,
        user.tenant_id,
        prompt,
        kind,
        third_party=third_party,
        sample_rows=sample_rows,
    )
    existing = (
        db.query(GeoTicket)
        .filter(
            GeoTicket.tenant_id == user.tenant_id,
            GeoTicket.prompt_id == prompt.id,
            ~GeoTicket.status.in_(["done", "closed", "ignored"]),
        )
        .order_by(GeoTicket.updated_at.desc())
        .first()
    )
    if existing:
        apply_loop_spec(existing, spec, keep_handoff=True)
        db.flush()
        if existing not in made:
            made.append(existing)
        return "updated"
    if _ticket_exists(db, user.tenant_id, prompt.id, spec["title"]):
        return "skipped"
    ticket = GeoTicket(
        tenant_id=user.tenant_id,
        prompt_id=prompt.id,
        title=spec["title"],
        diagnosis=spec["diagnosis"],
        rationale=spec["rationale"],
        acceptance_criteria=spec["acceptance_criteria"],
        priority=spec["priority"],
        owner_hint=spec["owner_hint"],
        recommended_action=spec["recommended_action"],
        retest_method=spec["retest_method"],
        status="open",
        evidence=json.dumps(spec["evidence"], ensure_ascii=False, indent=2),
    )
    db.add(ticket)
    db.flush()
    made.append(ticket)
    return "created"


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
    recent_runs = (
        db.query(GeoSampleRun)
        .options(selectinload(GeoSampleRun.results).selectinload(GeoSampleResult.prompt))
        .filter(GeoSampleRun.tenant_id == user.tenant_id)
        .order_by(GeoSampleRun.started_at.desc())
        .limit(12)
        .all()
    )
    latest_batch, _previous = pick_sample_batches(recent_runs)
    sampled_prompt_ids: set[str] = set()
    if latest_batch:
        by_prompt: dict[str, list[GeoSampleResult]] = {}
        for run in latest_batch:
            for row in run.results:
                by_prompt.setdefault(row.prompt_id, []).append(row)
        prompts_by_id = {prompt.id: prompt for prompt in prompts}
        for prompt_id, rows in by_prompt.items():
            prompt = prompts_by_id.get(prompt_id) or (rows[0].prompt if rows else None)
            if prompt is None:
                continue
            sampled_prompt_ids.add(prompt.id)
            third_party = any(_json_list(row.third_party_citations_json) for row in rows)
            kinds = kinds_from_sample_rows(rows)
            if not kinds:
                continue
            result = _add_loop_ticket(
                db, user, prompt, kinds[0], third_party=third_party, made=made, sample_rows=rows
            )
            if result == "created":
                created += 1
            else:
                skipped += 1
    for prompt in prompts:
        if prompt.id in sampled_prompt_ids:
            continue
        recorded = [o for o in prompt.observations if o.status in RECORDED_OBS]
        if not recorded:
            continue
        tiers = [_evidence_tier(o) for o in recorded]
        kinds: list[str] = []
        if all(tier == "none" for tier in tiers):
            kinds.append("absent")
        if any(tier == "mentioned" for tier in tiers) and not any(tier in {"cited", "verified"} for tier in tiers):
            kinds.append("no_owned")
        if any(tier == "cited" for tier in tiers) and not any(tier == "verified" for tier in tiers):
            kinds.append("unverified")
        if any((o.competitor_mentions or "").strip() for o in recorded):
            kinds.append("competitor")
        for kind in kinds:
            result = _add_loop_ticket(db, user, prompt, kind, third_party=False, made=made)
            if result == "created":
                created += 1
            else:
                skipped += 1
    db.commit()
    for ticket in made:
        db.refresh(ticket)
    note = (
        "已按抽查看没看到、对应页和渠道卡生成待处理项。完成标准是页已上线或帖已发出，并再测同一问；不要求这次必须提到。"
        if created
        else "没有新增待处理项；可能暂无抽查，或相关项已存在。"
    )
    return GeoTicketDraftOut(created=created, skipped=skipped, note=note, tickets=[_ticket_out(t) for t in made])
