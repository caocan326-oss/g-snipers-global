"""Idempotent demo tenant + account manager + insight/SEO sample data."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import hash_password
from app.config import settings
from app.content_templates import generate_draft, generate_meta, generate_outline
from app.database import SessionLocal
from app.geo_helpers import CHECKLIST_DEFS, ENGINES, build_llms_txt
from app.risk import default_severity, severity_to_risk
from app.models import (
    BacklinkGap,
    Competitor,
    DemandSignal,
    DistributionJob,
    GeoAsset,
    GeoChecklistItem,
    GeoObservation,
    GeoPrompt,
    GeoTicket,
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

SNIPERS_TEST_ORIGIN = "https://www.snipers.com.cn"


def seed(db: Session) -> None:
    tenant = db.scalar(select(Tenant).where(Tenant.name == "演示客户 · 智能门锁出海"))
    if tenant is None:
        tenant = Tenant(name="演示客户 · 智能门锁出海", industry="智能家居", site_origin=SNIPERS_TEST_ORIGIN)
        db.add(tenant)
        db.flush()
    elif not tenant.site_origin:
        tenant.site_origin = SNIPERS_TEST_ORIGIN

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
        _seed_three_chains(db, tenant, user)
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
    _seed_three_chains(db, tenant, user)
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
        diagnosis="untested",
    )
    jp_prompt = GeoPrompt(
        tenant_id=tenant.id,
        market_id=jp.id if jp else None,
        seo_page_id=jp_page.id if jp_page else None,
        prompt_text="賃貸でスマートロックを付けるには管理組合の許可が必要ですか？",
        locale="ja-JP",
        diagnosis="untested",
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
    db.add_all(
        [
            GeoAsset(
                tenant_id=tenant.id,
                kind="llms_txt",
                title="llms.txt 草稿",
                body=build_llms_txt(tenant, pages),
                status="draft",
                updated_by=user.id,
            ),
            GeoAsset(
                tenant_id=tenant.id,
                kind="cite_checklist",
                title="可引用性清单",
                body=(
                    "1. 官网有可被引用的事实页（规格、对比、案例），而非只有首页口号。\n"
                    "2. 关键实体名称中英一致，避免同一品牌多种拼写。\n"
                    "3. 对比页写清差异，而不是堆砌形容词。\n"
                    "4. 来源可核验：日期、作者、原始数据出处。\n"
                    "5. 未测引擎不要写成「已覆盖」。引用 ≠ 吸收。不得声称「已让 ChatGPT 引用」。\n"
                ),
                status="draft",
                updated_by=user.id,
            ),
        ]
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
        canonical="",
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
            severity="low",
            risk="low",
            status="drafted",
            metric_status="untested",
        ),
        OnsiteIssue(
            tenant_id=tenant.id,
            page_id=p1.id,
            category="schema",
            title="缺少 HowTo / FAQ 结构化数据",
            detail="上线会改 HTML，属 critical。分析与应用分开。",
            proposed_change="先出 JSON-LD 方案，确认后再给站点。",
            severity="critical",
            risk="high",
            status="drafted",
            metric_status="untested",
        ),
        OnsiteIssue(
            tenant_id=tenant.id,
            page_id=p1.id,
            category="index",
            title="收录状态未知",
            detail="无 GSC，不能填已收录或 0 页。",
            proposed_change="有 Search Console 后再测。",
            severity="critical",
            risk="high",
            status="open",
            metric_status="untested",
        ),
        OnsiteIssue(
            tenant_id=tenant.id,
            page_id=p1.id,
            category="canonical",
            title="Canonical 未登记",
            detail="无 GSC 不判断规范 URL。",
            proposed_change="/en-us/smart-lock-installation-renters",
            severity="critical",
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
            severity="high",
            risk="high",
            status="drafted",
            metric_status="untested",
        ),
        OnsiteIssue(
            tenant_id=tenant.id,
            page_id=p2.id,
            category="internal_link",
            title="未链到安装指南",
            detail="监测到的内链缺口。",
            proposed_change="正文加入 /en-us/smart-lock-installation-renters",
            severity="low",
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
            severity="critical",
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
            severity="low",
            risk="low",
            status="drafted",
            metric_status="untested",
        ),
        OnsiteIssue(
            tenant_id=tenant.id,
            page_id=p5.id,
            category="schema",
            title="首页 Organization 标记缺失",
            proposed_change="方案先写在工作区，确认后才改线上。",
            severity="critical",
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
        link_url="https://www.reddit.com/r/smarthome/",
        kind="competitor",
        verify_status="unverified",
        our_presence="none",
        domain_metric="untested",
        status="outreach",
        notes="客户经理从公开讨论记下的缺口。逐条核验，不是 Ahrefs 数字。",
    )
    g2 = BacklinkGap(
        tenant_id=tenant.id,
        market_id=us.id if us else None,
        competitor_name="Level Lock",
        referring_domain="theverge.com",
        competitor_url=None,
        link_url="https://www.theverge.com/",
        kind="competitor",
        verify_status="unverified",
        our_presence="untested",
        domain_metric="untested",
        status="identified",
        notes="是否真有稿件未核实，保持未核验。",
    )
    g3 = BacklinkGap(
        tenant_id=tenant.id,
        market_id=jp.id if jp else None,
        competitor_name="Qrio",
        referring_domain="kakaku.com",
        link_url="https://kakaku.com/",
        kind="competitor",
        verify_status="valid",
        our_presence="none",
        domain_metric="untested",
        status="identified",
        notes="竞品页人工点开有效；我方无链。",
    )
    g4 = BacklinkGap(
        tenant_id=tenant.id,
        market_id=us.id if us else None,
        competitor_name="August Home",
        referring_domain="wirecutter.com",
        link_url="https://www.nytimes.com/wirecutter/",
        kind="competitor",
        verify_status="unverified",
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
        link_url="https://www.heise.de/",
        kind="competitor",
        verify_status="dead",
        our_presence="none",
        domain_metric="untested",
        status="identified",
        notes="人工复查：旧稿 404。",
    )
    g6 = BacklinkGap(
        tenant_id=tenant.id,
        market_id=us.id if us else None,
        competitor_name="Level Lock",
        referring_domain="houzz.com",
        link_url="https://www.houzz.com/",
        kind="competitor",
        verify_status="spam",
        our_presence="none",
        domain_metric="untested",
        status="replied",
        notes="目录站互链气味重，标垃圾，不跟进购买。",
    )
    inbound_ok = BacklinkGap(
        tenant_id=tenant.id,
        market_id=us.id if us else None,
        competitor_name="—",
        referring_domain="smarthome-weekly.example",
        link_url="https://smarthome-weekly.example/renters-lock",
        kind="inbound",
        verify_status="valid",
        our_presence="present",
        domain_metric="untested",
        status="won",
        notes="我方 inbound：客户经理手点确认存在。权重未测。",
    )
    inbound_dead = BacklinkGap(
        tenant_id=tenant.id,
        market_id=us.id if us else None,
        competitor_name="—",
        referring_domain="old-blog.example",
        link_url="https://old-blog.example/gone",
        kind="inbound",
        verify_status="dead",
        our_presence="none",
        domain_metric="untested",
        status="lost",
        notes="原合作稿已下线，待跟进或放弃。",
    )
    db.add_all([g1, g2, g3, g4, g5, g6, inbound_ok, inbound_dead])
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


def _seed_three_chains(db: Session, tenant: Tenant, user: User) -> None:
    """Backfill China engines, GEO tickets, inbound verify rows on existing demos."""
    prompts = db.query(GeoPrompt).filter(GeoPrompt.tenant_id == tenant.id).all()
    for prompt in prompts:
        existing = {o.engine for o in prompt.observations}
        for engine in ENGINES:
            if engine not in existing:
                db.add(
                    GeoObservation(
                        tenant_id=tenant.id,
                        prompt_id=prompt.id,
                        engine=engine,
                        status="untested",
                    )
                )
        if not prompt.diagnosis:
            prompt.diagnosis = "untested"

    if db.scalar(select(GeoTicket).where(GeoTicket.tenant_id == tenant.id)) is None and prompts:
        first = prompts[0]
        db.add_all(
            [
                GeoTicket(
                    tenant_id=tenant.id,
                    prompt_id=first.id,
                    title="英文安装问句：中西引擎采样后补事实页",
                    diagnosis="untested",
                    rationale="8 个槽位默认未测。先抽查再诊断，禁止把空槽写成已引用。",
                    acceptance_criteria="至少完成一轮人工记录；引用 ≠ 吸收；未测保持未测。客户经理确认后才算验收。",
                    status="open",
                ),
                GeoTicket(
                    tenant_id=tenant.id,
                    prompt_id=prompts[-1].id,
                    title="日语许可问句：若竞品主导则开站内对照页",
                    diagnosis="untested",
                    rationale="诊断层等采样。不得发明 brand.com 引用率。",
                    acceptance_criteria="豆包 / Kimi / 通义 / DeepSeek 可手填或保持未测；验收须确认。",
                    status="in_progress",
                ),
            ]
        )

    if (
        db.scalar(
            select(GeoAsset).where(GeoAsset.tenant_id == tenant.id, GeoAsset.kind == "cite_checklist")
        )
        is None
    ):
        db.add(
            GeoAsset(
                tenant_id=tenant.id,
                kind="cite_checklist",
                title="可引用性清单",
                body=(
                    "1. 官网有可被引用的事实页（规格、对比、案例），而非只有首页口号。\n"
                    "2. 关键实体名称中英一致。\n"
                    "3. 对比页写清差异。\n"
                    "4. 来源可核验。\n"
                    "5. 未测不要写成已覆盖。引用 ≠ 吸收。\n"
                ),
                status="draft",
                updated_by=user.id,
            )
        )

    for issue in db.query(OnsiteIssue).filter(OnsiteIssue.tenant_id == tenant.id).all():
        if not issue.severity or (issue.severity == "low" and issue.category in {"schema", "index", "crawl", "canonical"}):
            issue.severity = default_severity(issue.category)
            issue.risk = severity_to_risk(issue.severity)
    for page in db.query(SitePage).filter(SitePage.tenant_id == tenant.id).all():
        if page.canonical is None:
            page.canonical = ""

    gaps = db.query(BacklinkGap).filter(BacklinkGap.tenant_id == tenant.id).all()
    for gap in gaps:
        if not gap.kind:
            gap.kind = "competitor"
        if not gap.verify_status:
            gap.verify_status = "unverified"
        if not gap.link_url:
            gap.link_url = gap.competitor_url

    if not any(g.kind == "inbound" for g in gaps):
        us = db.scalar(select(Market).where(Market.tenant_id == tenant.id, Market.country_code == "US"))
        db.add_all(
            [
                BacklinkGap(
                    tenant_id=tenant.id,
                    market_id=us.id if us else None,
                    competitor_name="—",
                    referring_domain="smarthome-weekly.example",
                    link_url="https://smarthome-weekly.example/renters-lock",
                    kind="inbound",
                    verify_status="valid",
                    our_presence="present",
                    domain_metric="untested",
                    status="won",
                    notes="我方 inbound：人工点开有效。权重未测。",
                ),
                BacklinkGap(
                    tenant_id=tenant.id,
                    market_id=us.id if us else None,
                    competitor_name="—",
                    referring_domain="old-blog.example",
                    link_url="https://old-blog.example/gone",
                    kind="inbound",
                    verify_status="dead",
                    our_presence="none",
                    domain_metric="untested",
                    status="lost",
                    notes="原合作稿已下线。",
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
