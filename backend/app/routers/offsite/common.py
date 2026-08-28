import re

from app.models import BacklinkGap, ContentAsset, FactPack, PlatformAccount, PlatformConnector, SourcePlatform
from app.official_apis import official_api_for
from app.schemas import (
    BacklinkGapOut,
    ContentAssetOut,
    FactPackOut,
    OutreachOut,
    PlatformAccountOut,
    PlatformConnectorOut,
    SourcePlatformOut,
)


def _platform_out(row: SourcePlatform) -> SourcePlatformOut:
    spec = official_api_for(row.platform_key)
    return SourcePlatformOut(
        id=row.id,
        platform_key=row.platform_key,
        name=row.name,
        domain=row.domain,
        source_type=row.source_type,
        regions=row.regions,
        industry_tags=row.industry_tags,
        base_url=row.base_url,
        listing_model=row.listing_model,
        submission_mode=row.submission_mode,
        has_official_api=row.has_official_api or bool(spec),
        risk_level=row.risk_level,
        status=row.status,
        notes=row.notes,
        accounts_count=len(row.accounts),
        connectors_count=len(row.connectors),
        compose_url=spec.compose_url if spec else "",
        docs_url=spec.docs_url if spec else "",
        api_endpoint=spec.api_endpoint if spec else "",
        api_auth_mode=spec.auth_mode if spec else "",
        profile_url=row.profile_url or "",
        profile_http_status=row.profile_http_status,
        profile_is_live=bool(row.profile_is_live),
        profile_site_found=bool(row.profile_site_found),
        profile_checked_at=row.profile_checked_at,
        profile_note=row.profile_note or "",
        profile_missing_page="该渠道还没有可核的公开档案" in (row.profile_note or ""),
    )


def _account_out(row: PlatformAccount) -> PlatformAccountOut:
    return PlatformAccountOut(
        id=row.id,
        platform_id=row.platform_id,
        platform_name=row.platform.name if row.platform else "",
        label=row.label,
        login_identifier=row.login_identifier,
        auth_method=row.auth_method,
        vault_ref=row.vault_ref,
        owner_hint=row.owner_hint,
        scope=row.scope,
        status=row.status,
        risk_level=row.risk_level,
        regions_allowed=row.regions_allowed,
        notes=row.notes,
        last_verified_at=row.last_verified_at,
        last_used_at=row.last_used_at,
    )


def _connector_out(row: PlatformConnector) -> PlatformConnectorOut:
    return PlatformConnectorOut(
        id=row.id,
        platform_id=row.platform_id,
        platform_name=row.platform.name if row.platform else "",
        provider_key=row.provider_key,
        auth_mode=row.auth_mode,
        capabilities=row.capabilities,
        status=row.status,
        env_var=row.env_var,
        notes=row.notes,
        last_verified_at=row.last_verified_at,
    )


def _fact_pack_out(row: FactPack) -> FactPackOut:
    return FactPackOut(
        id=row.id,
        name=row.name,
        legal_name=row.legal_name,
        brand_names=row.brand_names,
        website=row.website,
        product_categories_en=row.product_categories_en,
        certifications=row.certifications,
        key_specs=row.key_specs,
        banned_claims=row.banned_claims,
        contact_public=row.contact_public,
        approved_boilerplate_en=row.approved_boilerplate_en,
        status=row.status,
        version=row.version,
        approved_by=row.approved_by,
        approved_at=row.approved_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _asset_out(row: ContentAsset) -> ContentAssetOut:
    return ContentAssetOut(
        id=row.id,
        fact_pack_id=row.fact_pack_id,
        fact_pack_name=row.fact_pack.name if row.fact_pack else "",
        asset_type=row.asset_type,
        title=row.title,
        body_md=row.body_md,
        locale=row.locale,
        keywords=row.keywords,
        entities=row.entities,
        status=row.status,
        ai_review_status=row.ai_review_status,
        ai_review=row.ai_review,
        human_review_note=row.human_review_note,
        approved_by=row.approved_by,
        approved_at=row.approved_at,
        version=row.version,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _split_terms(value: str) -> list[str]:
    return [part.strip() for part in value.replace("\n", ",").split(",") if part.strip()]


def _pack_text(value: str | None) -> str:
    return (value or "").strip()


def _generate_asset_body(fact: FactPack, asset_type: str) -> str:
    brand = (_split_terms(fact.brand_names) or [fact.legal_name or "[NEED_INPUT: brand name]"])[0]
    categories = _pack_text(fact.product_categories_en) or "[NEED_INPUT: product categories]"
    website = _pack_text(fact.website) or "[NEED_INPUT: website]"
    certifications = _pack_text(fact.certifications)
    contact = _pack_text(fact.contact_public)
    specs = _pack_text(fact.key_specs)
    boilerplate = _pack_text(fact.approved_boilerplate_en)
    if asset_type == "profile_fields":
        lines = [
            f"Company name: {fact.legal_name or brand}",
            f"Brand: {brand}",
            f"Website: {website}",
            f"Categories: {categories}",
        ]
        if certifications:
            lines.append(f"Certifications: {certifications}")
        if contact:
            lines.append(f"Public contact: {contact}")
        lines.append(f"Company description: {boilerplate or '[NEED_INPUT: approved English boilerplate]'}")
        return "\n".join(lines)
    if asset_type == "social_snippet":
        lines = [
            f"{brand} | {categories}",
            boilerplate or "[NEED_INPUT: approved English boilerplate]",
            f"Learn more: {website}",
        ]
        if contact:
            lines.append(f"Contact: {contact}")
        lines.append(f"Keywords: {categories}.")
        return "\n".join(lines)
    if asset_type == "listicle_pitch":
        facts = [f"website {website}"]
        if certifications:
            facts.append(f"certifications/qualifications: {certifications}")
        if specs:
            facts.append(f"key specs: {specs}")
        if contact:
            facts.append(f"public contact: {contact}")
        return (
            f"Hi [EDITOR_NAME],\n\n"
            f"I am sharing {brand} for consideration in your supplier roundup about {categories}. "
            f"Public facts we can verify: {'; '.join(facts)}.\n\n"
            f"Short description:\n{boilerplate or '[NEED_INPUT: approved English boilerplate]'}\n\n"
            f"Please let us know if you need images, specs, or a formal media kit.\n"
        )
    parts = [
        f"{brand} is a supplier focused on {categories}.",
        boilerplate or "Its public company description still needs customer approval. [NEED_INPUT: approved English boilerplate]",
        f"Website: {website}.",
    ]
    if certifications:
        parts.append(f"Public certifications or qualifications: {certifications}.")
    if contact:
        parts.append(f"Public contact: {contact}.")
    return " ".join(parts)


def _review_asset(row: ContentAsset, fact: FactPack | None) -> tuple[str, list[str]]:
    findings: list[str] = []
    body = row.body_md or ""
    lower = body.lower()
    if "[need_input" in lower:
        findings.append("存在 [NEED_INPUT]，需要补齐事实后才能批准。")
    if fact:
        brands = _split_terms(fact.brand_names) or ([fact.legal_name] if fact.legal_name else [])
        if brands and not any(brand.lower() in lower for brand in brands if brand):
            findings.append("正文未出现客户基础资料中的品牌名。")
        for claim in _split_terms(fact.banned_claims):
            if claim.lower() in lower:
                findings.append(f"命中禁用宣传语：{claim}")
        certs = _split_terms(fact.certifications)
        cert_words = ["iso", "ce", "ul", "fda", "rohs", "reach"]
        mentioned = [word.upper() for word in cert_words if re.search(rf"\b{re.escape(word)}\b", lower)]
        allowed = " ".join(certs).lower()
        for word in mentioned:
            if word.lower() not in allowed:
                findings.append(f"出现认证/合规词 {word}，但客户基础资料未确认。")
    else:
        findings.append("未绑定客户基础资料，不能进入人工批准。")
    words = [part.strip(".,;:!?()[]{}").lower() for part in body.split()]
    for keyword in _split_terms(row.keywords):
        count = sum(1 for word in words if word == keyword.lower())
        if count >= 5:
            findings.append(f"关键词可能堆砌：{keyword} 出现 {count} 次。")
    status = "pass" if not findings else "fail"
    return status, findings


def _gap_out(row: BacklinkGap) -> BacklinkGapOut:
    return BacklinkGapOut(
        id=row.id,
        title=row.title or "",
        issue_type=row.issue_type or "competitor_gap",
        source=row.source or "manual",
        source_platform_id=row.source_platform_id or "",
        competitor_name=row.competitor_name,
        referring_domain=row.referring_domain,
        competitor_url=row.competitor_url,
        link_url=row.link_url,
        kind=row.kind or "competitor",
        priority=row.priority or "P2",
        verify_status=row.verify_status or "unverified",
        market_id=row.market_id,
        our_presence=row.our_presence,
        domain_metric=row.domain_metric,
        status=row.status,
        owner_hint=row.owner_hint or "",
        acceptance_criteria=row.acceptance_criteria or "",
        recommended_action=row.recommended_action or "",
        retest_method=row.retest_method or "",
        retest_result=row.retest_result or "",
        result_url=row.result_url or "",
        blocked_reason=row.blocked_reason or "",
        notes=row.notes,
        ai_status=row.ai_status or "untested",
        ai_review=row.ai_review or "",
        evidence=row.evidence or "",
        last_checked_at=row.last_checked_at,
        closed_at=row.closed_at,
        outreach=[OutreachOut.model_validate(o, from_attributes=True) for o in row.outreach],
    )
