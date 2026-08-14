"""Idempotent demo tenant + account manager + insight/SEO sample data."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import hash_password
from app.config import settings
from app.content_templates import generate_draft, generate_meta, generate_outline
from app.database import SessionLocal
from app.geo_helpers import CHECKLIST_DEFS, ENGINES, build_llms_txt
from app.models import (
    BacklinkGap,
    Competitor,
    DemandSignal,
    DistributionJob,
    GeoAsset,
    GeoChecklistItem,
    GeoObservation,
    GeoPrompt,
    Inquiry,
    InsightBrief,
    Market,
    OnsiteIssue,
    OutreachItem,
    SeoPage,
    SitePage,
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
        _seed_geo(db, tenant, user)
        _seed_onsite_offsite_dist(db, tenant, user)
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
    _seed_geo(db, tenant, user)
    _seed_onsite_offsite_dist(db, tenant, user)
    db.commit()


def _seed_geo(db: Session, tenant: Tenant, user: User) -> None:
    if db.scalar(select(GeoPrompt).where(GeoPrompt.tenant_id == tenant.id)) is not None:
        return

    us = db.scalar(select(Market).where(Market.tenant_id == tenant.id, Market.country_code == "US"))
    jp = db.scalar(select(Market).where(Market.tenant_id == tenant.id, Market.country_code == "JP"))
    us_signal = db.scalar(select(DemandSignal).where(DemandSignal.tenant_id == tenant.id, DemandSignal.locale == "en-US"))
    us_page = db.scalar(select(SeoPage).where(SeoPage.tenant_id == tenant.id, SeoPage.locale == "en-US"))
    jp_page = db.scalar(select(SeoPage).where(SeoPage.tenant_id == tenant.id, SeoPage.locale == "ja-JP"))

    us_prompt = GeoPrompt(
        tenant_id=tenant.id,
        market_id=us.id if us else None,
        seo_page_id=us_page.id if us_page else None,
        demand_signal_id=us_signal.id if us_signal else None,
        prompt_text="How do renters install a smart lock without replacing the whole door?",
        locale="en-US",
    )
    jp_prompt = GeoPrompt(
        tenant_id=tenant.id,
        market_id=jp.id if jp else None,
        seo_page_id=jp_page.id if jp_page else None,
        prompt_text="賃貸でスマートロックを付けるには管理組合の許可が必要ですか？",
        locale="ja-JP",
    )
    db.add_all([us_prompt, jp_prompt])
    db.flush()

    for prompt in (us_prompt, jp_prompt):
        for engine in ENGINES:
            db.add(
                GeoObservation(
                    tenant_id=tenant.id,
                    prompt_id=prompt.id,
                    engine=engine,
                    status="untested",
                )
            )

    pages = db.query(SeoPage).filter(SeoPage.tenant_id == tenant.id).all()
    db.add(
        GeoAsset(
            tenant_id=tenant.id,
            kind="llms_txt",
            title="llms.txt 草稿",
            body=build_llms_txt(tenant, pages),
            status="draft",
            updated_by=user.id,
        )
    )

    if us_page:
        for key, label in CHECKLIST_DEFS:
            db.add(
                GeoChecklistItem(
                    tenant_id=tenant.id,
                    seo_page_id=us_page.id,
                    item_key=key,
                    label=label,
                    status="untested",
                )
            )

    db.add(
        WorkOrder(
            tenant_id=tenant.id,
            title="抽查英文安装问句（先标未测，有记录再改）",
            type="geo_monitor",
            status="open",
            seo_page_id=us_page.id if us_page else None,
            market_id=us.id if us else None,
            acceptance_criteria="只记录实际抽查；未抽查保持未测，禁止填 0%。",
        )
    )


def _seed_onsite_offsite_dist(db: Session, tenant: Tenant, user: User) -> None:
    if db.scalar(select(SitePage).where(SitePage.tenant_id == tenant.id)) is not None:
        return

    us = db.scalar(select(Market).where(Market.tenant_id == tenant.id, Market.country_code == "US"))
    jp = db.scalar(select(Market).where(Market.tenant_id == tenant.id, Market.country_code == "JP"))
    de = db.scalar(select(Market).where(Market.tenant_id == tenant.id, Market.country_code == "DE"))
    us_seo = db.scalar(select(SeoPage).where(SeoPage.tenant_id == tenant.id, SeoPage.locale == "en-US"))
    jp_seo = db.scalar(select(SeoPage).where(SeoPage.tenant_id == tenant.id, SeoPage.locale == "ja-JP"))
    de_seo = db.scalar(select(SeoPage).where(SeoPage.tenant_id == tenant.id, SeoPage.locale == "de-DE"))

    p1 = SitePage(
        tenant_id=tenant.id,
        market_id=us.id if us else None,
        seo_page_id=us_seo.id if us_seo else None,
        path="/en-us/smart-lock-installation-renters",
        locale="en-US",
        title="Smart lock installation for renters",
        meta_title="Smart lock installation for renters",
        meta_description="Short draft — AM to expand.",
        headings="H1 Installation\nH2 Tools",
        internal_links="/en-us/compatibility",
        structured_data="",
        index_status="untested",
        crawl_status="untested",
        notes="演示页。收录/抓取未接 GSC，保持未测。",
    )
    p2 = SitePage(
        tenant_id=tenant.id,
        market_id=us.id if us else None,
        path="/en-us/smart-lock-compatibility",
        locale="en-US",
        title="Smart lock compatibility",
        meta_title="",
        meta_description="",
        headings="",
        internal_links="",
        structured_data="",
        index_status="untested",
        crawl_status="untested",
    )
    p3 = SitePage(
        tenant_id=tenant.id,
        market_id=jp.id if jp else None,
        seo_page_id=jp_seo.id if jp_seo else None,
        path="/ja-jp/chintai-smart-lock",
        locale="ja-JP",
        title="賃貸スマートロックの許可",
        meta_title="賃貸 スマートロック 許可",
        meta_description="管理組合向け説明（草稿）",
        headings="H1 許可\nH2 申請",
        internal_links="",
        structured_data="",
        index_status="untested",
        crawl_status="untested",
    )
    p4 = SitePage(
        tenant_id=tenant.id,
        market_id=de.id if de else None,
        seo_page_id=de_seo.id if de_seo else None,
        path="/de-de/smart-lock-dsgvo",
        locale="de-DE",
        title="Smart Lock und DSGVO",
        meta_title="Smart Lock DSGVO",
        meta_description="",
        headings="H1 Datenschutz",
        internal_links="/de-de/home",
        structured_data="",
        index_status="untested",
        crawl_status="untested",
    )
    p5 = SitePage(
        tenant_id=tenant.id,
        market_id=us.id if us else None,
        path="/en-us/",
        locale="en-US",
        title="Home",
        meta_title="Demo lock brand",
        meta_description="Homepage draft",
        headings="H1 Welcome",
        internal_links="/en-us/smart-lock-installation-renters",
        structured_data="",
        index_status="untested",
        crawl_status="untested",
    )
    db.add_all([p1, p2, p3, p4, p5])
    db.flush()

    issues = [
        OnsiteIssue(
            tenant_id=tenant.id,
            page_id=p1.id,
            category="tdk",
            title="Meta 描述过短",
            detail="工作区草稿，未接 Search Console。",
            proposed_change="补到 140–160 字符，含 renter / installation。",
            risk="low",
            status="open",
            metric_status="untested",
        ),
        OnsiteIssue(
            tenant_id=tenant.id,
            page_id=p1.id,
            category="schema",
            title="缺少 HowTo / FAQ 结构化数据",
            detail="上线会改 HTML，属高风险。",
            proposed_change="先出 JSON-LD 方案，确认后再给站点。",
            risk="high",
            status="open",
            metric_status="untested",
        ),
        OnsiteIssue(
            tenant_id=tenant.id,
            page_id=p1.id,
            category="index",
            title="收录状态未知",
            detail="无 GSC，不能填已收录或 0 页。",
            proposed_change="有 Search Console 后再测。",
            risk="high",
            status="open",
            metric_status="untested",
        ),
        OnsiteIssue(
            tenant_id=tenant.id,
            page_id=p2.id,
            category="heading",
            title="缺少 H1",
            detail="兼容页还没有标题层级。",
            proposed_change="补 H1 Compatibility + H2 门型。",
            risk="low",
            status="open",
            metric_status="untested",
        ),
        OnsiteIssue(
            tenant_id=tenant.id,
            page_id=p2.id,
            category="internal_link",
            title="未链到安装指南",
            detail="监测到的内链缺口。",
            proposed_change="正文加入 /en-us/smart-lock-installation-renters",
            risk="low",
            status="draft_applied",
            metric_status="untested",
        ),
        OnsiteIssue(
            tenant_id=tenant.id,
            page_id=p3.id,
            category="crawl",
            title="抓取状态未测",
            detail="未接爬虫日志 / GSC。",
            proposed_change="有数据源后再标。",
            risk="high",
            status="open",
            metric_status="untested",
        ),
        OnsiteIssue(
            tenant_id=tenant.id,
            page_id=p4.id,
            category="tdk",
            title="德文 Description 为空",
            proposed_change="用本地化隐私表述补描述。",
            risk="low",
            status="open",
            metric_status="untested",
        ),
        OnsiteIssue(
            tenant_id=tenant.id,
            page_id=p5.id,
            category="schema",
            title="首页 Organization 标记缺失",
            proposed_change="方案先写在工作区，确认后才改线上。",
            risk="high",
            status="open",
            metric_status="untested",
        ),
    ]
    db.add_all(issues)

    g1 = BacklinkGap(
        tenant_id=tenant.id,
        market_id=us.id if us else None,
        competitor_name="August Home",
        referring_domain="reddit.com",
        competitor_url="https://www.reddit.com/r/smarthome/",
        our_presence="none",
        domain_metric="untested",
        status="outreach",
        notes="客户经理从公开讨论记下的缺口。域名权重未测，不是 Ahrefs 数字。",
    )
    g2 = BacklinkGap(
        tenant_id=tenant.id,
        market_id=us.id if us else None,
        competitor_name="Level Lock",
        referring_domain="theverge.com",
        competitor_url=None,
        our_presence="untested",
        domain_metric="untested",
        status="identified",
        notes="是否真有稿件未核实，保持未测。",
    )
    g3 = BacklinkGap(
        tenant_id=tenant.id,
        market_id=jp.id if jp else None,
        competitor_name="Qrio",
        referring_domain="kakaku.com",
        our_presence="none",
        domain_metric="untested",
        status="identified",
    )
    g4 = BacklinkGap(
        tenant_id=tenant.id,
        market_id=us.id if us else None,
        competitor_name="August Home",
        referring_domain="wirecutter.com",
        our_presence="none",
        domain_metric="untested",
        status="skipped",
        notes="评测周期长，本季不外联。",
    )
    g5 = BacklinkGap(
        tenant_id=tenant.id,
        market_id=de.id if de else None,
        competitor_name="Nuki",
        referring_domain="heise.de",
        our_presence="none",
        domain_metric="untested",
        status="identified",
    )
    g6 = BacklinkGap(
        tenant_id=tenant.id,
        market_id=us.id if us else None,
        competitor_name="Level Lock",
        referring_domain="houzz.com",
        our_presence="none",
        domain_metric="untested",
        status="replied",
    )
    db.add_all([g1, g2, g3, g4, g5, g6])
    db.flush()

    db.add_all(
        [
            OutreachItem(
                tenant_id=tenant.id,
                gap_id=g1.id,
                contact="r/smarthome 版主（公开版规）",
                channel="forum",
                status="todo",
                notes="只做跟进清单，禁止群发。",
            ),
            OutreachItem(
                tenant_id=tenant.id,
                gap_id=g2.id,
                contact="tips@example.com",
                channel="email",
                status="todo",
            ),
            OutreachItem(
                tenant_id=tenant.id,
                gap_id=g6.id,
                contact="houzz 商家页",
                channel="form",
                status="sent_manual",
                notes="客户经理手发，系统未代发。",
            ),
            OutreachItem(
                tenant_id=tenant.id,
                gap_id=g3.id,
                contact="価格.com 登录页",
                channel="form",
                status="todo",
            ),
        ]
    )

    db.add_all(
        [
            DistributionJob(
                tenant_id=tenant.id,
                title="提交英文安装指南到目录",
                target_url="/en-us/smart-lock-installation-renters",
                provider_key="directory",
                payload_summary="标题 + 摘要。渠道未配置，确认后也不会真发。",
                status="draft",
                last_result="未发送",
            ),
            DistributionJob(
                tenant_id=tenant.id,
                title="客座网络排队（日语许可页）",
                target_url="/ja-jp/chintai-smart-lock",
                provider_key="guest_network",
                payload_summary="待人工确认。",
                status="draft",
                last_result="未发送",
            ),
            DistributionJob(
                tenant_id=tenant.id,
                title="聚合渠道草稿",
                target_url="/de-de/smart-lock-dsgvo",
                provider_key="syndication",
                payload_summary="未配置 API。",
                status="draft",
                last_result="未发送",
            ),
        ]
    )

    db.add_all(
        [
            WorkOrder(
                tenant_id=tenant.id,
                title="英文安装页补 TDK 草稿",
                type="onsite",
                status="open",
                market_id=us.id if us else None,
                acceptance_criteria="低风险可落工作区草稿；改线上 schema/收录必须确认。",
            ),
            WorkOrder(
                tenant_id=tenant.id,
                title="跟进 reddit 外链缺口",
                type="offsite",
                status="claimed",
                assignee_id=user.id,
                market_id=us.id if us else None,
                acceptance_criteria="只做外联清单，不代买、不群发。",
            ),
            WorkOrder(
                tenant_id=tenant.id,
                title="分发台：等客户提供渠道 Key",
                type="distribution",
                status="blocked",
                acceptance_criteria="未配置则不得发送。",
            ),
        ]
    )


def main() -> None:
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
