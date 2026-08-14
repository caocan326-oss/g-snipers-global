"""AI engine for the three chains: 分析 / 内容 / 审核 / 论证.

Never invent GSC ranks, cite rates, or live-site success.
Human confirm stays only for live apply, distribution send, and 可交付.
"""

from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy.orm import Session

from app.geo_helpers import apply_proposed_change
from app.llm import ERROR, OK, UNCONFIGURED, UNTESTED, LlmResult, complete, configured
from app.models import AiRun, BacklinkGap, GeoAsset, GeoPrompt, GeoTicket, OnsiteIssue, SitePage
from app.risk import needs_confirm

SYSTEM = (
    "你是出海站内/GEO/外链交付引擎。只根据给定观察作答。"
    "没有观察的指标必须写未测。禁止编造排名、GSC 收录数、Ahrefs/Semrush、brand.com 引用率。"
    "引用不等于吸收。不要声称已让 ChatGPT 引用。"
    "只输出一个 JSON 对象，键：diagnosis, draft, review, verdict, why, observed, untested。"
    "verdict 只能是 pass / fail / untested。"
)


def _parse(text: str) -> dict[str, str]:
    if not text.strip():
        return {}
    blob = text.strip()
    match = re.search(r"\{.*\}", blob, re.S)
    if match:
        blob = match.group(0)
    try:
        data = json.loads(blob)
    except json.JSONDecodeError:
        return {}
    out: dict[str, str] = {}
    for key in ("diagnosis", "draft", "review", "verdict", "why", "observed", "untested"):
        val = data.get(key)
        if val is not None:
            out[key] = str(val).strip()
    return out


def _evidence(*, why: str, observed: str, untested: str, llm_status: str) -> str:
    return (
        f"为何改：{why or '未测'}\n"
        f"已观察：{observed or '未测'}\n"
        f"未测：{untested or '未测'}\n"
        f"LLM：{llm_status}"
    )


def _record(
    db: Session,
    *,
    tenant_id: str,
    chain: str,
    step: str,
    target_type: str,
    target_id: str,
    result: LlmResult,
    evidence: str,
    output: str = "",
) -> None:
    db.add(
        AiRun(
            tenant_id=tenant_id,
            chain=chain,
            step=step,
            target_type=target_type,
            target_id=target_id,
            status=result.status,
            output=output or result.text,
            evidence=evidence,
            detail=result.detail,
        )
    )


def _payload(
    *,
    status: str,
    step: str,
    applied_draft: bool = False,
    diagnosis: str = "",
    draft: str = "",
    review: str = "",
    review_verdict: str = UNTESTED,
    evidence: str = "",
    detail: str = "",
) -> dict[str, Any]:
    return {
        "status": status,
        "step": step,
        "applied_draft": applied_draft,
        "diagnosis": diagnosis,
        "draft": draft,
        "review": review,
        "review_verdict": review_verdict,
        "evidence": evidence,
        "detail": detail,
    }


def observe_onsite(page: SitePage, issue: OnsiteIssue) -> str:
    return (
        f"path={page.path}; title={page.title}; meta_title={page.meta_title or '（空）'}; "
        f"meta_description={page.meta_description or '（空）'}; headings={page.headings or '（空）'}; "
        f"internal_links={page.internal_links or '（空）'}; schema={page.structured_data or '（空）'}; "
        f"canonical={page.canonical or '（空）'}; index={page.index_status}; "
        f"issue={issue.category}/{issue.title}; severity={issue.severity}"
    )


def assist_onsite_issue(db: Session, issue: OnsiteIssue, page: SitePage, *, step: str = "all") -> dict[str, Any]:
    observed = observe_onsite(page, issue)
    untested = "收录/Canonical 选择/GSC 展示；无 Search Console 一律未测。"
    if not configured():
        evidence = _evidence(
            why="工作区可见缺口，待 LLM 配置后再生成诊断与改稿。",
            observed=observed,
            untested=untested,
            llm_status=UNCONFIGURED,
        )
        issue.ai_status = UNCONFIGURED
        issue.evidence = evidence
        issue.ai_diagnosis = ""
        issue.ai_review = ""
        issue.ai_review_verdict = UNTESTED
        _record(
            db,
            tenant_id=issue.tenant_id,
            chain="onsite",
            step=step,
            target_type="onsite_issue",
            target_id=issue.id,
            result=LlmResult(False, UNCONFIGURED, "", "未配置 LLM_API_KEY。"),
            evidence=evidence,
        )
        return _payload(
            status=UNCONFIGURED,
            step=step,
            evidence=evidence,
            detail="未配置 LLM_API_KEY。未编造分析或草稿。",
        )

    user = (
        f"步骤={step}。观察：{observed}。{untested}\n"
        "若步骤含内容，draft 写可落入工作区的改稿；高风险不要假装已上线。"
        "审核要给理由。论证写清为何改、看到了什么、哪些未测。"
    )
    result = complete(system=SYSTEM, user=user)
    parsed = _parse(result.text) if result.status == OK else {}
    evidence = _evidence(
        why=parsed.get("why", ""),
        observed=parsed.get("observed", observed),
        untested=parsed.get("untested", untested),
        llm_status=result.status,
    )
    issue.ai_status = result.status
    issue.evidence = evidence
    if parsed.get("diagnosis"):
        issue.ai_diagnosis = parsed["diagnosis"]
        issue.detail = parsed["diagnosis"]
    if parsed.get("review"):
        issue.ai_review = parsed["review"]
    verdict = parsed.get("verdict", UNTESTED)
    issue.ai_review_verdict = verdict if verdict in {"pass", "fail", UNTESTED, "untested"} else UNTESTED
    applied = False
    if step in {"content", "all"} and parsed.get("draft"):
        issue.proposed_change = parsed["draft"]
        if issue.status == "open":
            issue.status = "drafted"
        if not needs_confirm(issue.severity, issue.risk):
            apply_proposed_change(page, issue)
            issue.status = "draft_applied"
            applied = True
    _record(
        db,
        tenant_id=issue.tenant_id,
        chain="onsite",
        step=step,
        target_type="onsite_issue",
        target_id=issue.id,
        result=result,
        evidence=evidence,
        output=result.text,
    )
    return _payload(
        status=result.status,
        step=step,
        applied_draft=applied,
        diagnosis=issue.ai_diagnosis or "",
        draft=issue.proposed_change,
        review=issue.ai_review or "",
        review_verdict=issue.ai_review_verdict,
        evidence=evidence,
        detail=result.detail,
    )


def assist_geo_prompt(db: Session, prompt: GeoPrompt, *, step: str = "all") -> dict[str, Any]:
    slots = [f"{o.engine}={o.status}" for o in prompt.observations]
    recorded = [o for o in prompt.observations if o.status != "untested"]
    observed = f"问句={prompt.prompt_text}; 槽位={', '.join(slots)}"
    untested = "未人工记录的引擎槽；brand.com 引用率；吸收率。"
    if not recorded:
        evidence = _evidence(
            why="尚无人工采样，不能诊断为已出现或已引用。",
            observed=observed,
            untested=untested,
            llm_status=UNTESTED if configured() else UNCONFIGURED,
        )
        prompt.diagnosis = "untested"
        prompt.ai_status = UNTESTED if configured() else UNCONFIGURED
        prompt.evidence = evidence
        status = UNTESTED if configured() else UNCONFIGURED
        _record(
            db,
            tenant_id=prompt.tenant_id,
            chain="geo",
            step=step,
            target_type="geo_prompt",
            target_id=prompt.id,
            result=LlmResult(configured(), status, "", "无采样记录，保持未测。"),
            evidence=evidence,
        )
        return _payload(status=status, step=step, evidence=evidence, detail="无采样记录，不编造诊断。")

    if not configured():
        evidence = _evidence(
            why="已有人工槽位记录，待 LLM 配置后出诊断。",
            observed=observed,
            untested=untested,
            llm_status=UNCONFIGURED,
        )
        prompt.ai_status = UNCONFIGURED
        prompt.evidence = evidence
        _record(
            db,
            tenant_id=prompt.tenant_id,
            chain="geo",
            step=step,
            target_type="geo_prompt",
            target_id=prompt.id,
            result=LlmResult(False, UNCONFIGURED, "", "未配置 LLM_API_KEY。"),
            evidence=evidence,
        )
        return _payload(status=UNCONFIGURED, step=step, evidence=evidence, detail="未配置 LLM_API_KEY。")

    result = complete(
        system=SYSTEM,
        user=f"根据采样槽做 GEO 诊断。{observed}。引用不等于吸收。未测槽保持未测。",
    )
    parsed = _parse(result.text) if result.status == OK else {}
    evidence = _evidence(
        why=parsed.get("why", "根据已记录槽位分层。"),
        observed=parsed.get("observed", observed),
        untested=parsed.get("untested", untested),
        llm_status=result.status,
    )
    allowed = {"untested", "absent", "mentioned", "competitor_dominated", "suspected_negative"}
    prompt.ai_status = result.status
    prompt.evidence = evidence
    if parsed.get("diagnosis") in allowed:
        prompt.diagnosis = parsed["diagnosis"]
    _record(
        db,
        tenant_id=prompt.tenant_id,
        chain="geo",
        step=step,
        target_type="geo_prompt",
        target_id=prompt.id,
        result=result,
        evidence=evidence,
        output=result.text,
    )
    return _payload(
        status=result.status,
        step=step,
        diagnosis=prompt.diagnosis,
        review=parsed.get("review", ""),
        evidence=evidence,
        detail=result.detail,
    )


def assist_geo_ticket(db: Session, ticket: GeoTicket, *, step: str = "review") -> dict[str, Any]:
    observed = f"工单={ticket.title}; 诊断={ticket.diagnosis}; 验收={ticket.acceptance_criteria}"
    if not configured():
        evidence = _evidence(
            why="验收仍须客户经理确认。",
            observed=observed,
            untested="复测结果；引用率。",
            llm_status=UNCONFIGURED,
        )
        ticket.ai_status = UNCONFIGURED
        ticket.evidence = evidence
        _record(
            db,
            tenant_id=ticket.tenant_id,
            chain="geo",
            step=step,
            target_type="geo_ticket",
            target_id=ticket.id,
            result=LlmResult(False, UNCONFIGURED, "", "未配置 LLM_API_KEY。"),
            evidence=evidence,
        )
        return _payload(status=UNCONFIGURED, step=step, evidence=evidence, detail="未配置。初审未编造，验收仍须人确认。")

    result = complete(system=SYSTEM, user=f"对 GEO 工单做初审，不要标记可交付。{observed}")
    parsed = _parse(result.text) if result.status == OK else {}
    evidence = _evidence(
        why=parsed.get("why", ticket.rationale),
        observed=parsed.get("observed", observed),
        untested=parsed.get("untested", "复测与引用率未测。"),
        llm_status=result.status,
    )
    ticket.ai_status = result.status
    ticket.ai_review = parsed.get("review", result.text)
    ticket.evidence = evidence
    _record(
        db,
        tenant_id=ticket.tenant_id,
        chain="geo",
        step=step,
        target_type="geo_ticket",
        target_id=ticket.id,
        result=result,
        evidence=evidence,
        output=result.text,
    )
    return _payload(
        status=result.status,
        step=step,
        review=ticket.ai_review or "",
        evidence=evidence,
        detail=result.detail,
    )


def assist_geo_asset(db: Session, asset: GeoAsset, *, step: str = "content") -> dict[str, Any]:
    if not configured():
        evidence = _evidence(
            why="llms.txt / 可引用清单是 GEO 链资产。",
            observed=f"kind={asset.kind}; status={asset.status}; 现有字数={len(asset.body or '')}",
            untested="是否已被任何模型引用。",
            llm_status=UNCONFIGURED,
        )
        asset.ai_status = UNCONFIGURED
        _record(
            db,
            tenant_id=asset.tenant_id,
            chain="geo",
            step=step,
            target_type="geo_asset",
            target_id=asset.id,
            result=LlmResult(False, UNCONFIGURED, "", "未配置 LLM_API_KEY。"),
            evidence=evidence,
        )
        return _payload(status=UNCONFIGURED, step=step, evidence=evidence, detail="未配置，不编造 llms.txt。")

    result = complete(
        system=SYSTEM,
        user=f"改写 GEO 资产草稿，不要声称已发布或已被引用。kind={asset.kind} 原文：{asset.body[:2000]}",
    )
    parsed = _parse(result.text) if result.status == OK else {}
    draft = parsed.get("draft") or result.text
    if result.status == OK and draft.strip():
        asset.body = draft
        asset.status = "draft"
    asset.ai_status = result.status
    evidence = _evidence(
        why=parsed.get("why", "提高可摘取性。"),
        observed=parsed.get("observed", f"kind={asset.kind}"),
        untested="模型引用情况未测。",
        llm_status=result.status,
    )
    _record(
        db,
        tenant_id=asset.tenant_id,
        chain="geo",
        step=step,
        target_type="geo_asset",
        target_id=asset.id,
        result=result,
        evidence=evidence,
        output=result.text,
    )
    return _payload(status=result.status, step=step, draft=asset.body, evidence=evidence, detail=result.detail)


def assist_offsite_gap(db: Session, gap: BacklinkGap, *, step: str = "evidence") -> dict[str, Any]:
    observed = (
        f"url={gap.link_url or gap.competitor_url or '未登记'}; domain={gap.referring_domain}; "
        f"verify={gap.verify_status}; kind={gap.kind}"
    )
    untested = "域名权重 / DR / 外链指数未测。本台不是 Ahrefs。"
    if not configured():
        evidence = _evidence(
            why="逐条核验，不是外链指数。",
            observed=observed,
            untested=untested,
            llm_status=UNCONFIGURED,
        )
        gap.ai_status = UNCONFIGURED
        gap.evidence = evidence
        _record(
            db,
            tenant_id=gap.tenant_id,
            chain="offsite",
            step=step,
            target_type="backlink_gap",
            target_id=gap.id,
            result=LlmResult(False, UNCONFIGURED, "", "未配置 LLM_API_KEY。"),
            evidence=evidence,
        )
        return _payload(status=UNCONFIGURED, step=step, evidence=evidence, detail="未配置。不编造外链指数。")

    result = complete(system=SYSTEM, user=f"为这条链接写核验论证与跟进建议。不要编造 DR。{observed}")
    parsed = _parse(result.text) if result.status == OK else {}
    evidence = _evidence(
        why=parsed.get("why", "人工核验跟进。"),
        observed=parsed.get("observed", observed),
        untested=parsed.get("untested", untested),
        llm_status=result.status,
    )
    gap.ai_status = result.status
    gap.ai_review = parsed.get("review", "")
    gap.evidence = evidence
    _record(
        db,
        tenant_id=gap.tenant_id,
        chain="offsite",
        step=step,
        target_type="backlink_gap",
        target_id=gap.id,
        result=result,
        evidence=evidence,
        output=result.text,
    )
    return _payload(
        status=result.status,
        step=step,
        review=gap.ai_review or "",
        evidence=evidence,
        detail=result.detail,
    )
