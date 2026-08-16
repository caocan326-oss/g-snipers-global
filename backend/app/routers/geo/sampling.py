import json
from datetime import datetime, timezone

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.auth import get_current_user
from app.database import get_db
from app.geo_providers import GeoProviderError
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
    GeoSampleRunCreate,
    GeoSampleRunOut,
    GeoTicketDraftOut,
)

import app.routers.geo as _geo_pkg

from . import router
from .common import (
    _aggregate_issue_specs,
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
                sampled = _geo_pkg.sample_with_provider(
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
    note = "已按 GEO 规则生成整改项草稿。" if created else "没有新增整改项；可能暂无观测，或相关整改项已存在。"
    return GeoTicketDraftOut(created=created, skipped=skipped, note=note, tickets=[_ticket_out(t) for t in made])
