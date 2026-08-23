from fastapi.testclient import TestClient

from app.models import OnsiteIssue, SitePage, Tenant
from tests.conftest import auth_header


def test_workbench_lists_same_openish_issues_as_summary(client: TestClient, demo_user, db) -> None:
    tenant = db.get(Tenant, demo_user.tenant_id)
    tenant.site_origin = "https://www.example.com"
    page = SitePage(
        tenant_id=demo_user.tenant_id,
        path="/applied",
        locale="en-US",
        title="Applied",
        crawl_status="ok",
    )
    db.add(page)
    db.flush()
    issue = OnsiteIssue(
        tenant_id=demo_user.tenant_id,
        page_id=page.id,
        category="tdk",
        title="首页标题过长",
        status="draft_applied",
        severity="critical",
        risk="high",
    )
    db.add(issue)
    db.commit()

    headers = auth_header(client)
    workbench = client.get("/api/dashboard/workbench?days=28", headers=headers).json()
    assert workbench["summary"]["onsite_open_critical"] == 1
    assert any(item["id"] == issue.id for item in workbench["seo_items"])


def test_customer_brief_empty_tenant_stays_untested(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    res = client.get("/api/dashboard/customer-brief", headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert "本周客户说明" in body["title"]
    assert "测试租户" in body["title"]
    assert body["headline"]
    assert "登记" in body["headline"]
    assert any("官网" in item for item in body["untested"])
    assert "尚未检查" in body["markdown"]
    assert "已被 AI 稳定推荐" not in body["markdown"]
    assert "0%" not in body["markdown"]
    keys = [section["key"] for section in body["sections"]]
    assert keys == ["findability", "this_week", "retest", "inquiries"]
    assert "这个月记到" in body["markdown"]


def test_customer_brief_merges_onsite_and_geo(client: TestClient, demo_user, db) -> None:
    tenant = db.get(Tenant, demo_user.tenant_id)
    tenant.site_origin = "https://www.example.com"
    page = SitePage(
        tenant_id=demo_user.tenant_id,
        path="/",
        locale="en-US",
        title="Home",
        crawl_status="ok",
    )
    db.add(page)
    db.flush()
    db.add(
        OnsiteIssue(
            tenant_id=demo_user.tenant_id,
            page_id=page.id,
            category="tdk",
            title="首页标题过长",
            status="open",
            severity="critical",
            risk="high",
        )
    )
    db.commit()

    headers = auth_header(client)
    prompt = client.post(
        "/api/geo/prompts",
        headers=headers,
        json={"prompt_text": "best smart lock for renters", "locale": "en-US"},
    )
    assert prompt.status_code == 201, prompt.text

    res = client.get("/api/dashboard/customer-brief", headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()
    markdown = body["markdown"]
    assert "这一周先处理 1 个紧急网站问题" in body["headline"]
    assert "首页标题过长" in markdown
    assert "哪些地方让老外搜不到我" in markdown
    assert "这周带给客户改的三处" in markdown
    assert "客户改完你再看一次" in markdown
    assert "这个月有几个老外来问过" in markdown
    assert any("首页标题过长" in item for item in body["this_week"])
    assert any("请改这一页" in item and "首页标题过长" in item for item in body["this_week"])
    assert any("紧急" in item for item in body["this_week"])
    assert any(("尚未检查" in item or "还没联网抽查" in item) for item in body["untested"])

    workbench = client.get("/api/dashboard/workbench?days=28", headers=headers).json()
    assert workbench["summary"]["onsite_open_critical"] == 1
    assert workbench["summary"]["onsite_open_high"] == 0
    geo_act = next(item for item in workbench["next_actions"] if item["id"] == "geo-sampling")
    assert "1 个买家问题还没抽查" in geo_act["subtitle"]
    assert "8 条检查" not in geo_act["subtitle"]
    assert "8 个买家问题尚未检查" not in geo_act["subtitle"]


def test_seeded_demo_counts_align_across_surfaces(client: TestClient, db) -> None:
    from app.seed import seed

    seed(db)
    headers = auth_header(client)
    workbench = client.get("/api/dashboard/workbench?days=28", headers=headers).json()
    brief = client.get("/api/dashboard/customer-brief", headers=headers).json()
    guide = client.get("/api/onsite/guide", headers=headers).json()
    geo = client.get("/api/geo/summary", headers=headers).json()
    summary = workbench["summary"]

    assert summary["tenant_name"] == "演示客户 · 智能门锁出海"
    assert summary["onsite_pages"] == 5
    assert summary["onsite_open_critical"] == 5
    assert summary["onsite_open_high"] == 1
    assert summary["onsite_open_low"] == 3
    assert summary["onsite_open_critical"] + summary["onsite_open_high"] + summary["onsite_open_low"] == 9
    assert summary["geo_prompts"] == geo["prompts"] == 2
    assert summary["geo_untested"] == geo["untested"] == 16
    assert summary["geo_tickets_open"] == 2
    assert [section["key"] for section in brief["sections"]] == ["findability", "this_week", "retest", "inquiries"]
    assert any("紧急" in item for item in brief["this_week"])
    assert "这个月记到" in brief["markdown"]
    assert guide["open_high"] == 6
    assert guide["current"] != "collect"
    assert any(item["id"] == "seo-critical" for item in workbench["next_actions"])
    geo_act = next(item for item in workbench["next_actions"] if item["id"] == "geo-sampling")
    assert "2 个买家问题还没抽查" in geo_act["subtitle"]
    assert "16 条检查" not in geo_act["subtitle"]
    assert "16 个买家问题" not in geo_act["subtitle"]
    assert "采样" not in brief["markdown"]
    # Seed creates two GEO tickets; brief keeps one GEO slot (ordered by updated_at).
    assert any("许可问题" in item or "安装问题" in item for item in brief["this_week"])
    assert "16 条尚未检查" not in brief["headline"]
    assert "16 条尚未检查" not in brief["markdown"]


def test_customer_brief_uses_sample_run_not_engine_slots(client: TestClient, demo_user, db) -> None:
    from datetime import datetime, timezone

    from app.models import GeoPrompt, GeoSampleResult, GeoSampleRun

    tenant = db.get(Tenant, demo_user.tenant_id)
    tenant.site_origin = "https://www.snipers.com.cn"
    db.add(
        SitePage(
            tenant_id=demo_user.tenant_id,
            path="/",
            locale="en-US",
            title="Home",
            crawl_status="ok",
        )
    )
    prompt = GeoPrompt(
        tenant_id=demo_user.tenant_id,
        prompt_text="How do renters install a smart lock without replacing the whole door?",
        locale="en-US",
    )
    db.add(prompt)
    db.flush()
    run = GeoSampleRun(
        tenant_id=demo_user.tenant_id,
        config_hash="brief-test",
        status="done",
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    db.flush()
    db.add(
        GeoSampleResult(
            tenant_id=demo_user.tenant_id,
            run_id=run.id,
            prompt_id=prompt.id,
            evidence_id="ev_brief_bocha_1",
            engine="bocha",
            web_grounded="true",
            prompt_text_hash="a" * 64,
            answer_text_hash="b" * 64,
            answer_excerpt="Third-party installation tips.",
            mentioned=False,
            citations_json='["https://other.example/lock"]',
            owned_citations_json="[]",
            third_party_citations_json='["https://other.example/lock"]',
        )
    )
    db.commit()

    headers = auth_header(client)
    body = client.get("/api/dashboard/customer-brief", headers=headers).json()
    assert "16 条" not in body["headline"]
    assert "8 条" not in body["headline"]
    assert "都没有提到我们" in body["headline"]
    assert "没有给出官网" in body["headline"]
    findability = next(section for section in body["sections"] if section["key"] == "findability")
    assert any("外来网址" in item for item in findability["items"])
    workbench = client.get("/api/dashboard/workbench?days=28", headers=headers).json()
    geo_act = next(item for item in workbench["next_actions"] if item["id"] == "geo-sampling")
    assert geo_act["status"] == "已抽查"
    assert "没有提到我们" in geo_act["subtitle"]


def test_customer_brief_retest_only_records_sample_change(client: TestClient, demo_user, db) -> None:
    from datetime import datetime, timedelta, timezone

    from app.models import GeoPrompt, GeoSampleResult, GeoSampleRun

    tenant = db.get(Tenant, demo_user.tenant_id)
    tenant.site_origin = "https://www.snipers.com.cn"
    db.add(SitePage(tenant_id=demo_user.tenant_id, path="/", locale="en-US", title="Home", crawl_status="ok"))
    prompt = GeoPrompt(
        tenant_id=demo_user.tenant_id,
        prompt_text="best smart lock for apartment doors",
        locale="en-US",
    )
    db.add(prompt)
    db.flush()
    older = datetime.now(timezone.utc) - timedelta(days=3)
    newer = datetime.now(timezone.utc)
    for evidence_id, started_at in (("ev_brief_old", older), ("ev_brief_new", newer)):
        run = GeoSampleRun(
            tenant_id=demo_user.tenant_id,
            config_hash=evidence_id,
            status="done",
            started_at=started_at,
        )
        db.add(run)
        db.flush()
        db.add(
            GeoSampleResult(
                tenant_id=demo_user.tenant_id,
                run_id=run.id,
                prompt_id=prompt.id,
                evidence_id=evidence_id,
                engine="bocha",
                web_grounded="true",
                prompt_text_hash="a" * 64,
                answer_text_hash="b" * 64,
                answer_excerpt="No brand.",
                mentioned=False,
                citations_json="[]",
                owned_citations_json="[]",
                third_party_citations_json="[]",
            )
        )
    db.commit()

    headers = auth_header(client)
    body = client.get("/api/dashboard/customer-brief", headers=headers).json()
    retest = next(section for section in body["sections"] if section["key"] == "retest")
    assert any("仍没提到" in item for item in retest["items"])
    assert all("必须提到" not in item for item in retest["items"])
    assert all("已稳定推荐" not in item for item in retest["items"])
    assert "仍没提到就写仍没提到" in body["markdown"]


def test_customer_brief_keeps_geo_ticket_in_this_week_when_onsite_is_full(client: TestClient, demo_user, db) -> None:
    from app.models import GeoPrompt, GeoTicket

    tenant = db.get(Tenant, demo_user.tenant_id)
    tenant.site_origin = "https://www.ugreen.com"
    page = SitePage(
        tenant_id=demo_user.tenant_id,
        path="/products/usa-65585",
        locale="en-US",
        title="UGREEN Nexode 100W Charger",
        crawl_status="ok",
    )
    db.add(page)
    db.flush()
    for title in ("页面缺少给搜索看的说明", "标准网址没写清楚", "产品页缺少 Product schema"):
        db.add(
            OnsiteIssue(
                tenant_id=demo_user.tenant_id,
                page_id=page.id,
                category="tdk",
                title=title,
                status="open",
                severity="critical",
                risk="high",
            )
        )
    prompt = GeoPrompt(
        tenant_id=demo_user.tenant_id,
        prompt_text="Which brand makes the best 100W USB-C charger for laptops?",
        locale="en-US",
    )
    db.add(prompt)
    db.flush()
    db.add(
        GeoTicket(
            tenant_id=demo_user.tenant_id,
            prompt_id=prompt.id,
            title="买家问「Which brand makes the best 100W USB-C charger for laptops?」时提到了品牌，但没给出官网",
            diagnosis="mentioned",
            status="open",
            recommended_action="请客户改这一页：UGREEN Nexode 100W Charger https://www.ugreen.com/products/usa-65585",
        )
    )
    db.commit()

    headers = auth_header(client)
    body = client.get("/api/dashboard/customer-brief", headers=headers).json()
    assert any("100W USB-C" in item and "请改这一页" in item for item in body["this_week"])
    assert sum(1 for item in body["this_week"] if "紧急" in item) <= 2
    assert "这周请改这几处" in body["paste_text"]
    assert "1." in body["paste_text"]
    assert "工作台打勾" not in body["paste_text"]
    assert "发给客户的短稿" in body["markdown"]


def test_customer_brief_hides_internal_issue_codes(client: TestClient, demo_user, db) -> None:
    from app.routers.onsite.common import _plain_title

    assert _plain_title("GEO-ENT-002 缺少 Organization / WebSite schema") == "首页缺少公司介绍说明"
    assert "schema" not in _plain_title("产品页缺少 Product schema").lower()

    tenant = db.get(Tenant, demo_user.tenant_id)
    tenant.site_origin = "https://www.ugreen.com"
    page = SitePage(
        tenant_id=demo_user.tenant_id,
        path="/",
        locale="en-US",
        title="Home",
        crawl_status="ok",
    )
    db.add(page)
    db.flush()
    db.add(
        OnsiteIssue(
            tenant_id=demo_user.tenant_id,
            page_id=page.id,
            category="schema",
            title="GEO-ENT-002 缺少 Organization / WebSite schema",
            status="open",
            severity="critical",
            risk="high",
        )
    )
    db.commit()

    body = client.get("/api/dashboard/customer-brief", headers=auth_header(client)).json()
    blob = body["markdown"] + body["paste_text"] + "".join(body["this_week"])
    assert "GEO-ENT-002" not in blob
    assert "schema" not in blob.lower()
    assert "首页缺少公司介绍说明" in blob
