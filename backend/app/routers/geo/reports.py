import csv
from datetime import datetime, timezone
from io import StringIO

from fastapi import Depends
from sqlalchemy.orm import Session, selectinload

from app.auth import get_current_user
from app.database import get_db
from app.geo_helpers import DIAGNOSES, ENGINE_LABELS, engine_region
from app.models import GeoPrompt, GeoSampleResult, GeoSampleRun, Tenant, User
from app.schemas import GeoReportOut, GeoReportTableOut

from . import router
from .common import _evidence_tier, _json_list, _prompt_rates, _run_out
from .constants import EVIDENCE_LABELS
from .prompts import geo_summary


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
        f"# AI 搜索说明 - {tenant.name if tenant else ''}",
        "",
        "## 一句话结论",
        "",
        f"本次用 {summary.prompts} 个买家问题做测试，已记录 {summary.recorded} 条结果，尚未检查 {summary.untested} 条。品牌被提到的比例 {summary.mention_rate}，答案里给出官网的比例 {summary.cite_rate}，人工核验通过的比例 {summary.verified_citation_rate}。",
        "",
        "## 口径说明",
        "",
        "- 引用率：答案里明确给出客户官网或客户内容作为来源的比例。",
        "- 已核验引用率：人工确认来源网址能打开，且确属客户官网或客户可控资产。",
        "- 吸收率：答案提到客户品牌、产品或客户内容的比例；提到不等于给出官网。",
        "- 竞品提及：答案中出现竞品或替代品牌，需人工判断是否跟进内容或外部曝光。",
        "- 尚未检查的项目不按 0 计算，不编造“已被 AI 推荐”。",
        "",
        "## 总览",
        "",
        f"- 买家问题：{summary.prompts}",
        f"- 已有记录：{summary.recorded}",
        f"- 尚未检查：{summary.untested}",
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
        "1. 优先补齐尚未检查的条目，同一买家问题、同一地区保持同一套问法。",
        "2. 如果主要在推竞品，回到网站补对照说明、案例、参数和可核对来源。",
        "3. 如果只被提到、没有给出官网，检查页面是否有清楚来源、作者、日期和可供摘取的结论。",
        "4. 改完后再查同一批问题，记下有没有被提到、有没有给出官网。",
    ]
    return GeoReportOut(title=f"AI 搜索说明 - {tenant.name if tenant else ''}", markdown="\n".join(lines), generated_at=generated)


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
