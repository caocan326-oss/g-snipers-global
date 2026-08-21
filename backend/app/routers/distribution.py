from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import BacklinkGap, ContentAsset, DistributionAttempt, DistributionJob, PlatformAccount, SourcePlatform, User
from app.official_apis import official_api_for, official_api_payload
from app.providers import all_providers, get_provider
from app.risk import require_confirm
from app.schemas import (
    ConfirmReadyIn,
    DistributionJobCreate,
    DistributionGuideOut,
    DistributionJobOut,
    DistributionJobUpdate,
    DistributionSubmitResultIn,
    OfficialPayloadOut,
    PlacementCheckOut,
    ProviderOut,
    SendResultOut,
)

router = APIRouter(prefix="/api/distribution", tags=["distribution"])

JOB_STATUSES = {"draft", "ready", "in_progress", "submitted", "verifying", "done", "blocked", "blocked_unconfigured", "cancelled", "sent"}
VERIFY_STATUSES = {"pending", "live", "failed", "unknown"}
TASK_TYPES = {
    "profile_create",
    "profile_update",
    "brand_fix",
    "product_listing",
    "listicle_pitch",
    "guest_or_pr",
    "distributor_align",
    "link_claim",
    "monitor_only",
    "social_profile_update",
    "social_post_plan",
}

TASK_MATERIALS = {
    "profile_create": ["客户官网 URL", "英文公司简介", "英文品类词", "主营产品/能力", "公开联系人", "认证/资质（仅限已确认）"],
    "profile_update": ["现有档案 URL", "需要修正的字段", "标准英文简介", "官网目标页", "认证/品类确认"],
    "brand_fix": ["错误截图或 URL", "标准品牌名", "官网证明页", "建议替换文案"],
    "product_listing": ["产品英文名", "规格/参数", "产品页 URL", "图片或附件链接", "禁止宣传语检查"],
    "listicle_pitch": ["榜单/文章 URL", "入选理由", "客户事实亮点", "联系人邮箱", "人工终审后的 pitch"],
    "guest_or_pr": ["PR/稿件草稿", "客户基础资料", "客户终审记录", "媒体联系人", "风险说明"],
    "distributor_align": ["分销商页面 URL", "标准品牌名", "目标官网 URL", "统一产品描述", "客户授权说明"],
    "link_claim": ["未链接提及 URL", "建议链接目标页", "联系对象", "礼貌修正口径"],
    "monitor_only": ["监控 URL", "需要观察的品牌/产品词", "复测周期", "变更记录口径"],
    "social_profile_update": ["平台官网主页 URL", "品牌头像/Logo", "英文公司简介", "官网链接", "联系方式", "目标国家/语言", "客户确认的品牌口径"],
    "social_post_plan": ["发布平台", "人工批准的文案", "目标链接", "图片/视频素材链接", "发布时间", "负责人", "评论/私信处理口径"],
}

TASK_CHECKLIST = {
    "profile_create": ["确认平台适合目标国家和品类", "使用客户确认过的英文事实，不编造认证和客户案例", "把品类映射到平台允许的 category", "人工登录或提交表单", "提交后回填 result_url"],
    "profile_update": ["打开现有档案并核对品牌名/官网/品类", "只修改事实错误或缺失字段", "保留提交截图或备注", "提交后回填 result_url"],
    "brand_fix": ["确认第三方页面确实写错", "准备标准品牌名和官网证明", "通过平台、邮件或联系人请求修正", "回填处理线程或结果 URL"],
    "product_listing": ["确认产品资料已通过客户终审", "避免堆砌关键词和夸大参数", "按平台字段填写产品/能力", "回填产品或档案 URL"],
    "listicle_pitch": ["确认榜单主题和客户品类相关", "使用事实型 pitch，不承诺排名或付费结果", "人工发送并记录联系人", "若上线，回填文章 URL"],
    "guest_or_pr": ["客户终审稿件后才能外发", "检查 banned claims 和认证表述", "人工发送或提交", "上线后核验 URL"],
    "distributor_align": ["确认分销商关系真实", "统一品牌名、型号和官网链接", "通过商务/邮件推进修改", "上线后核验页面"],
    "link_claim": ["确认第三方已有真实提及", "建议添加最相关官网 URL", "不要强制要求 dofollow", "回填对方修改后的 URL"],
    "monitor_only": ["确认只做观察不提交", "记录当前页面状态", "定期复查是否删除、改链或改描述"],
    "social_profile_update": ["确认这是客户官方账号或客户授权账号", "统一品牌名、官网链接、简介、联系方式和品类词", "不要编造认证、规模、客户案例", "人工登录修改后回填主页 URL"],
    "social_post_plan": ["确认文案和素材已人工批准", "检查 banned claims 和链接目标页", "由负责人在官方账号发布或排期", "发布后回填帖子 URL 并核验可访问"],
}


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        values = {key.lower(): value or "" for key, value in attrs}
        href = values.get("href", "")
        if href:
            self.links.append((href, values.get("rel", "")))


def _platform_for_job(db: Session, job: DistributionJob) -> SourcePlatform | None:
    return db.get(SourcePlatform, job.platform_id) if job.platform_id else None


def _safe_http_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _host_match(url: str, target_url: str) -> bool:
    parsed_url = urlparse(url)
    parsed_target = urlparse(target_url)
    if not parsed_target.netloc:
        return False
    return parsed_target.netloc.lower() in parsed_url.netloc.lower()


def _job_out(row: DistributionJob) -> DistributionJobOut:
    return DistributionJobOut.model_validate(row, from_attributes=True)


@router.get("/providers", response_model=list[ProviderOut])
def list_providers() -> list[ProviderOut]:
    return [
        ProviderOut(
            key=p.key,
            label=p.label,
            configured=p.configured(),
            status="已配置" if p.configured() else "未配置",
            env_var=p.env_var,
        )
        for p in all_providers()
    ]


@router.get("/jobs", response_model=list[DistributionJobOut])
def list_jobs(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[DistributionJob]:
    return (
        db.query(DistributionJob)
        .filter(DistributionJob.tenant_id == user.tenant_id)
        .order_by(DistributionJob.created_at.desc())
        .all()
    )


@router.post("/jobs", response_model=DistributionJobOut, status_code=201)
def create_job(
    body: DistributionJobCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DistributionJob:
    if get_provider(body.provider_key) is None:
        raise HTTPException(status_code=400, detail="未知分发渠道")
    if body.task_type not in TASK_TYPES:
        raise HTTPException(status_code=400, detail="无效任务类型")
    gap = None
    if body.gap_id:
        gap = db.get(BacklinkGap, body.gap_id)
        if gap is None or gap.tenant_id != user.tenant_id:
            raise HTTPException(status_code=404, detail="站外渠道不存在")
    platform = None
    account = None
    asset = None
    if body.platform_id:
        platform = db.get(SourcePlatform, body.platform_id)
        if platform is None or platform.tenant_id != user.tenant_id:
            raise HTTPException(status_code=404, detail="平台不存在")
    if body.account_id:
        account = db.get(PlatformAccount, body.account_id)
        if account is None or account.tenant_id != user.tenant_id:
            raise HTTPException(status_code=404, detail="账号不存在")
        if body.platform_id and account.platform_id != body.platform_id:
            raise HTTPException(status_code=400, detail="账号不属于所选平台")
        if account.status != "active":
            raise HTTPException(status_code=400, detail="账号不可用，不能进入执行")
    if body.content_asset_id:
        asset = db.get(ContentAsset, body.content_asset_id)
        if asset is None or asset.tenant_id != user.tenant_id:
            raise HTTPException(status_code=404, detail="内容资产不存在")
        if asset.status != "human_approved":
            raise HTTPException(status_code=400, detail="对外材料未人工批准，不能进入执行任务")
        if not body.payload_summary:
            body.payload_summary = asset.body_md[:2000]
    row = DistributionJob(
        tenant_id=user.tenant_id,
        status="draft",
        last_result="未发送",
        **body.model_dump(),
    )
    if platform and platform.submission_mode == "manual_login" and account is None:
        row.status = "blocked"
        row.blocked_reason = "needs_account：该平台需要人工登录账号，请先绑定可用账号。"
        row.last_result = "缺账号"
        row.last_detail = row.blocked_reason
    db.add(row)
    if gap:
        gap.status = "converted_to_task"
        if not gap.owner_hint and body.owner_hint:
            gap.owner_hint = body.owner_hint
        if not gap.recommended_action:
            gap.recommended_action = f"按 {body.task_type} 创建执行任务：{body.title}"
        _sync_gap_from_job(gap, row)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/jobs/{job_id}", response_model=DistributionJobOut)
def update_job(
    job_id: str,
    body: DistributionJobUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DistributionJob:
    job = db.get(DistributionJob, job_id)
    if job is None or job.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="执行任务不存在")
    payload = body.model_dump(exclude_unset=True)
    if "status" in payload and payload["status"]:
        if payload["status"] not in JOB_STATUSES:
            raise HTTPException(status_code=400, detail="无效任务状态")
        job.status = payload["status"]
    if "platform_id" in payload:
        if payload["platform_id"]:
            platform = db.get(SourcePlatform, payload["platform_id"])
            if platform is None or platform.tenant_id != user.tenant_id:
                raise HTTPException(status_code=404, detail="平台不存在")
            job.platform_id = platform.id
        else:
            job.platform_id = None
    if "account_id" in payload:
        if payload["account_id"]:
            account = db.get(PlatformAccount, payload["account_id"])
            if account is None or account.tenant_id != user.tenant_id:
                raise HTTPException(status_code=404, detail="账号不存在")
            if job.platform_id and account.platform_id != job.platform_id:
                raise HTTPException(status_code=400, detail="账号不属于所选平台")
            if account.status != "active":
                raise HTTPException(status_code=400, detail="账号不可用，不能进入执行")
            job.account_id = account.id
        else:
            job.account_id = None
    if "content_asset_id" in payload:
        if payload["content_asset_id"]:
            asset = db.get(ContentAsset, payload["content_asset_id"])
            if asset is None or asset.tenant_id != user.tenant_id:
                raise HTTPException(status_code=404, detail="内容资产不存在")
            if asset.status != "human_approved":
                raise HTTPException(status_code=400, detail="对外材料未人工批准，不能进入执行任务")
            job.content_asset_id = asset.id
            if not job.payload_summary:
                job.payload_summary = asset.body_md[:2000]
        else:
            job.content_asset_id = None
    if "verify_status" in payload and payload["verify_status"]:
        if payload["verify_status"] not in VERIFY_STATUSES:
            raise HTTPException(status_code=400, detail="无效核验状态")
        job.verify_status = payload["verify_status"]
    for field in ("owner_hint", "result_url", "blocked_reason", "payload_summary"):
        if field in payload:
            setattr(job, field, payload[field] or "")
    if job.platform_id:
        platform = db.get(SourcePlatform, job.platform_id)
        if platform and platform.submission_mode == "manual_login" and not job.account_id and job.status in {"ready", "in_progress"}:
            job.status = "blocked"
            job.blocked_reason = "needs_account：该平台需要人工登录账号，请先绑定可用账号。"
    if job.gap_id:
        gap = db.get(BacklinkGap, job.gap_id)
        if gap and gap.tenant_id == user.tenant_id:
            _sync_gap_from_job(gap, job)
    db.commit()
    db.refresh(job)
    return job


@router.post("/jobs/{job_id}/submit-result", response_model=DistributionJobOut)
def submit_result(
    job_id: str,
    body: DistributionSubmitResultIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DistributionJob:
    if body.verify_status not in VERIFY_STATUSES:
        raise HTTPException(status_code=400, detail="无效核验状态")
    job = db.get(DistributionJob, job_id)
    if job is None or job.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="执行任务不存在")
    job.result_url = body.result_url
    job.verify_status = body.verify_status
    job.status = "verifying" if body.verify_status == "pending" else "done" if body.verify_status == "live" else "submitted"
    job.last_result = "已提交结果"
    job.last_detail = body.evidence or f"Result URL: {body.result_url}"
    job.last_checked_at = datetime.now(timezone.utc)
    if job.gap_id:
        gap = db.get(BacklinkGap, job.gap_id)
        if gap and gap.tenant_id == user.tenant_id:
            _sync_gap_from_job(gap, job, evidence=body.evidence)
    db.commit()
    db.refresh(job)
    return job


@router.get("/jobs/{job_id}/guide", response_model=DistributionGuideOut)
def job_guide(
    job_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DistributionGuideOut:
    job = db.get(DistributionJob, job_id)
    if job is None or job.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="执行任务不存在")
    platform = _platform_for_job(db, job)
    mode = platform.submission_mode if platform else "manual"
    risk_notes = [
        "AI 只能生成草稿和检查清单，不能无人审对外发布。",
        "禁止自动登录、绕验证码、自动群发、自动购买付费位或批量注册目录账号。",
    ]
    if platform and platform.risk_level == "high":
        risk_notes.append("该平台标记为高风险，PR、榜单或付费合作必须客户/负责人终审。")
    if mode == "manual_login":
        risk_notes.append("该平台需要人工登录；未绑定可用账号时任务应保持受阻。")
    elif mode == "email_outreach":
        risk_notes.append("系统只生成邮件/投稿草稿，最终发送必须由人工完成。")
    elif mode == "paid_placement":
        risk_notes.append("付费合作不能自动下单，预算和合同需人工确认。")
    return DistributionGuideOut(
        job_id=job.id,
        platform_name=platform.name if platform else "",
        submission_mode=mode,
        task_type=job.task_type,
        materials=TASK_MATERIALS.get(job.task_type, ["客户官网 URL", "标准英文简介", "结果 URL"]),
        checklist=TASK_CHECKLIST.get(job.task_type, ["确认资料真实", "人工执行", "回填 result_url", "复测核验"]),
        risk_notes=risk_notes,
        placement_checks=["result_url 可访问", "页面文本包含品牌/域名线索", "页面存在指向客户目标页或官网的链接", "记录 checked_at 和核验结论"],
    )


@router.post("/jobs/{job_id}/check-placement", response_model=PlacementCheckOut)
def check_placement(
    job_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlacementCheckOut:
    job = db.get(DistributionJob, job_id)
    if job is None or job.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="执行任务不存在")
    result_url = (job.result_url or "").strip()
    if not result_url:
        raise HTTPException(status_code=400, detail="请先填写 result_url")
    if not _safe_http_url(result_url):
        raise HTTPException(status_code=400, detail="result_url 必须是 http/https URL")

    http_status: int | None = None
    is_live = False
    brand_mentioned = False
    target_link_found = False
    link_attr = "unknown"
    note = ""
    try:
        with httpx.Client(timeout=20, follow_redirects=True, headers={"User-Agent": "G-Snipers-PlacementCheck/0.1"}) as client:
            response = client.get(result_url)
        http_status = response.status_code
        is_live = 200 <= response.status_code < 400
        text = response.text[:300000]
        target_host = urlparse(job.target_url).netloc.lower()
        result_text = text.lower()
        brand_mentioned = bool(target_host and target_host in result_text)
        parser = _LinkParser()
        parser.feed(text)
        for href, rel in parser.links:
            if _host_match(href, job.target_url):
                target_link_found = True
                link_attr = rel or "unknown"
                break
        if is_live and (brand_mentioned or target_link_found):
            job.verify_status = "live"
            job.status = "done"
            note = "结果页面已可访问，并发现客户域名或目标链接。"
        elif is_live:
            job.verify_status = "unknown"
            job.status = "verifying"
            note = "URL 可访问，但未在页面文本或链接中确认客户线索，需要人工复核。"
        else:
            job.verify_status = "failed"
            job.status = "submitted"
            note = f"URL 返回 HTTP {response.status_code}，暂未通过存活核验。"
    except httpx.HTTPError as exc:
        job.verify_status = "failed"
        job.status = "submitted"
        note = f"核验请求失败：{str(exc)[:200]}"

    job.last_result = "结果页面核验"
    job.last_detail = note
    job.last_checked_at = datetime.now(timezone.utc)
    if job.gap_id:
        gap = db.get(BacklinkGap, job.gap_id)
        if gap and gap.tenant_id == user.tenant_id:
            evidence = f"结果页面核验：{note}"
            _sync_gap_from_job(gap, job, evidence=evidence)
            gap.retest_result = note
    db.commit()
    return PlacementCheckOut(
        job_id=job.id,
        result_url=result_url,
        target_url=job.target_url,
        http_status=http_status,
        is_live=is_live,
        brand_mentioned=brand_mentioned,
        target_link_found=target_link_found,
        link_attr=link_attr,
        note=note,
    )


@router.get("/jobs/{job_id}/official-payload", response_model=OfficialPayloadOut)
def job_official_payload(
    job_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OfficialPayloadOut:
    job = db.get(DistributionJob, job_id)
    if job is None or job.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="执行任务不存在")
    platform = _platform_for_job(db, job)
    key = platform.platform_key if platform else ""
    spec = official_api_for(key)
    if spec is None:
        raise HTTPException(status_code=400, detail="这个渠道还没有挂官方接口。先去官网发，或登记自己的接口。")
    body = job.payload_summary or ""
    if job.content_asset_id:
        asset = db.get(ContentAsset, job.content_asset_id)
        if asset is not None and asset.tenant_id == user.tenant_id:
            body = asset.body_md or body
    payload = official_api_payload(platform_key=key, title=job.title, body=body, target_url=job.target_url)
    return OfficialPayloadOut(sent=False, **payload)


@router.post("/jobs/{job_id}/send", response_model=SendResultOut)
def send_job(
    job_id: str,
    body: ConfirmReadyIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SendResultOut:
    require_confirm(body.confirmed, action="向外链渠道发送")
    job = db.get(DistributionJob, job_id)
    if job is None or job.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="执行任务不存在")
    provider = get_provider(job.provider_key)
    if provider is None:
        raise HTTPException(status_code=400, detail="未知分发渠道")

    result = provider.send(title=job.title, target_url=job.target_url, payload_summary=job.payload_summary)
    attempt = DistributionAttempt(
        tenant_id=user.tenant_id,
        job_id=job.id,
        confirmed=True,
        sent=result.sent,
        result=result.status,
        detail=result.detail,
    )
    db.add(attempt)
    job.last_result = result.status
    job.last_detail = result.detail
    if result.sent:
        job.status = "sent"
    elif result.status == "未配置":
        job.status = "blocked_unconfigured"
    else:
        job.status = "blocked"
    if job.gap_id:
        gap = db.get(BacklinkGap, job.gap_id)
        if gap and gap.tenant_id == user.tenant_id:
            _sync_gap_from_job(gap, job)
    db.commit()
    db.refresh(job)
    return SendResultOut(
        sent=result.sent,
        provider_status=result.status,
        detail=result.detail,
        job=_job_out(job),
    )


def _sync_gap_from_job(gap: BacklinkGap, job: DistributionJob, *, evidence: str = "") -> None:
    if job.result_url:
        gap.result_url = job.result_url
        gap.link_url = job.result_url
    if job.verify_status == "live":
        gap.verify_status = "valid"
        gap.status = "won"
        gap.closed_at = datetime.now(timezone.utc)
    elif job.verify_status == "failed":
        gap.verify_status = "dead"
        gap.status = "needs_retest"
    elif job.status in {"submitted", "verifying", "sent"}:
        gap.status = "needs_retest"
    elif job.status in {"blocked", "blocked_unconfigured"}:
        gap.status = "blocked"
        gap.blocked_reason = job.blocked_reason or job.last_detail or "执行任务受阻"
    elif job.status in {"ready", "in_progress"}:
        gap.status = "in_progress"
    if job.owner_hint and not gap.owner_hint:
        gap.owner_hint = job.owner_hint
    if job.result_url and not gap.retest_method:
        gap.retest_method = "复查 result_url 是否可访问、是否提及客户、是否链接到目标页。"
    if evidence:
        gap.evidence = "\n".join(part for part in [gap.evidence, evidence] if part)
    gap.last_checked_at = datetime.now(timezone.utc)
