"""Idempotent demo tenant + account manager + insight/SEO sample data."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import hash_password
from app.config import settings
from app.content_templates import generate_draft, generate_meta, generate_outline
from app.database import SessionLocal
from app.models import (
    Competitor,
    DemandSignal,
    Inquiry,
    InsightBrief,
    Market,
    SeoPage,
    Tenant,
    User,
    WorkOrder,
)


def seed(db: Session) -> None:
    tenant = db.scalar(select(Tenant).where(Tenant.name == "演示客户 · 智能门锁出海"))
    if tenant is None:
        tenant = Tenant(name="演示客户 · 智能门锁出海", industry="智能家居")
        db.add(tenant)
        db.flush()

    email = settings.demo_am_email.lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(
            tenant_id=tenant.id,
            email=email,
            hashed_password=hash_password(settings.demo_am_password),
            name="林安（客户经理）",
            role="account_manager",
        )
        db.add(user)
        db.flush()

    if db.scalar(select(Market).where(Market.tenant_id == tenant.id)) is not None:
        db.commit()
        return

    us = Market(
        tenant_id=tenant.id,
        name="美国",
        region="北美",
        country_code="US",
        primary_locale="en-US",
        status="priority",
        opportunity_score=82,
        notes="租赁房改造与 DIY 安装内容需求高，适合先做英文指南页。",
    )
    de = Market(
        tenant_id=tenant.id,
        name="德国",
        region="欧洲",
        country_code="DE",
        primary_locale="de-DE",
        status="watching",
        opportunity_score=64,
        notes="认证与数据隐私表述要本地化，不宜直接翻译英文页。",
    )
    jp = Market(
        tenant_id=tenant.id,
        name="日本",
        region="亚太",
        country_code="JP",
        primary_locale="ja-JP",
        status="priority",
        opportunity_score=71,
        notes="公寓管理组合规是决策点，内容应写给住户+管理组合。",
    )
    db.add_all([us, de, jp])
    db.flush()

    db.add_all(
        [
            Competitor(
                tenant_id=tenant.id,
                market_id=us.id,
                name="Level Lock",
                website="https://level.co",
                positioning="极简外观，主打苹果生态",
            ),
            Competitor(
                tenant_id=tenant.id,
                market_id=us.id,
                name="August Home",
                website="https://august.com",
                positioning="租赁场景与远程授权",
            ),
            Competitor(
                tenant_id=tenant.id,
                market_id=jp.id,
                name="Qrio",
                website="https://qrio.me",
                positioning="日本本土安装与支持",
            ),
        ]
    )

    us_signal = DemandSignal(
        tenant_id=tenant.id,
        market_id=us.id,
        theme="smart lock installation for renters",
        locale="en-US",
        intensity=5,
        intent="informational",
        source="manual",
        notes="客户经理根据公开搜索建议与销售访谈录入，非实时 SERP API。",
    )
    jp_signal = DemandSignal(
        tenant_id=tenant.id,
        market_id=jp.id,
        theme="賃貸 スマートロック 許可",
        locale="ja-JP",
        intensity=4,
        intent="commercial",
        source="manual",
    )
    de_signal = DemandSignal(
        tenant_id=tenant.id,
        market_id=de.id,
        theme="Smart Lock DSGVO",
        locale="de-DE",
        intensity=3,
        intent="informational",
        source="manual",
    )
    db.add_all([us_signal, jp_signal, de_signal])
    db.flush()

    db.add_all(
        [
            InsightBrief(
                tenant_id=tenant.id,
                market_id=us.id,
                updated_by=user.id,
                summary="美国优先做「租客可安装」叙事，避开全屋改造。",
                opportunities="指南页 + 对照表能承接中高意向搜索，再转询盘。",
                risks="亚马逊评价里安装失败故事多，正文必须写兼容门型。",
                recommended_actions="先产出 en-US 安装指南大纲与 Meta，再开日语选题。",
            ),
            InsightBrief(
                tenant_id=tenant.id,
                market_id=jp.id,
                updated_by=user.id,
                summary="日本市场关键是管理组合沟通话术，而不是功能参数堆砌。",
                opportunities="许可申请模板类内容可形成自然询盘。",
                risks="直译英文页会被认为不了解公寓规则。",
                recommended_actions="日语页从需求信号开选题，大纲用本地疑问句。",
            ),
        ]
    )

    us_outline = generate_outline(us_signal.theme, "en-US")
    us_draft = generate_draft(us_signal.theme, "en-US", us_outline)
    us_meta_t, us_meta_d = generate_meta(us_signal.theme, "en-US", us_signal.theme)
    us_page = SeoPage(
        tenant_id=tenant.id,
        market_id=us.id,
        demand_signal_id=us_signal.id,
        title="Smart lock installation for renters",
        target_keyword=us_signal.theme,
        locale="en-US",
        status="review",
        outline=us_outline,
        draft_body=us_draft,
        meta_title=us_meta_t,
        meta_description=us_meta_d,
        created_by=user.id,
    )
    jp_page = SeoPage(
        tenant_id=tenant.id,
        market_id=jp.id,
        demand_signal_id=jp_signal.id,
        title="賃貸スマートロックの許可",
        target_keyword=jp_signal.theme,
        locale="ja-JP",
        status="idea",
        created_by=user.id,
    )
    de_page = SeoPage(
        tenant_id=tenant.id,
        market_id=de.id,
        title="Smart Lock und DSGVO",
        target_keyword=de_signal.theme,
        locale="de-DE",
        status="outline",
        outline=generate_outline(de_signal.theme, "de-DE"),
        created_by=user.id,
    )
    db.add_all([us_page, jp_page, de_page])
    db.flush()

    db.add_all(
        [
            WorkOrder(
                tenant_id=tenant.id,
                title="改写美国租客安装指南语气",
                type="seo_draft",
                status="claimed",
                assignee_id=user.id,
                seo_page_id=us_page.id,
                market_id=us.id,
                acceptance_criteria="大纲、正文、Meta 齐全；提交审核。",
            ),
            WorkOrder(
                tenant_id=tenant.id,
                title="日本许可页先出大纲",
                type="seo_outline",
                status="open",
                seo_page_id=jp_page.id,
                market_id=jp.id,
                acceptance_criteria="日语大纲覆盖管理组合沟通。",
            ),
        ]
    )
    db.add(
        Inquiry(
            tenant_id=tenant.id,
            source="organic_en",
            contact="alex@example.com / 加州物业经理",
            quality="qualified",
            related_seo_page_id=us_page.id,
            related_market_id=us.id,
            notes="询问多门锁批量安装，来自英文指南预览页（演示）。",
        )
    )
    db.commit()


def main() -> None:
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
