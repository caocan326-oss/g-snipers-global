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
    assert workbench["weekly_onsite"][0]["id"] == issue.id
    assert workbench["weekly_onsite"][0]["status"] == "待发给客户"
    assert any(item["id"] == "weekly-three" for item in workbench["next_actions"])


def test_workbench_weekly_three_follows_pin_and_sent(client: TestClient, demo_user, db) -> None:
    tenant = db.get(Tenant, demo_user.tenant_id)
    tenant.site_origin = "https://www.snipers.com.cn"
    tenant.name = "SNIPERS"
    pages = [
        SitePage(tenant_id=demo_user.tenant_id, path="/a", locale="zh-CN", title="A", crawl_status="ok"),
        SitePage(tenant_id=demo_user.tenant_id, path="/b", locale="zh-CN", title="B", crawl_status="ok"),
        SitePage(tenant_id=demo_user.tenant_id, path="/c", locale="zh-CN", title="C", crawl_status="ok"),
    ]
    db.add_all(pages)
    db.flush()
    db.add_all(
        [
            OnsiteIssue(
                tenant_id=demo_user.tenant_id,
                page_id=page.id,
                category="tdk",
                title="首页标题过长",
                status="open",
                severity="high",
                risk="high",
            )
            for page in pages
        ]
    )
    db.commit()

    headers = auth_header(client)
    empty_note = client.get("/api/dashboard/workbench?days=28", headers=headers).json()
    assert len(empty_note["weekly_onsite"]) == 3
    assert empty_note["weekly_pinned"] is False
    assert {item["subtitle"] for item in empty_note["weekly_onsite"]} == {"/a", "/b", "/c"}
    assert all(item["status"] == "待发给客户" for item in empty_note["weekly_onsite"])
    assert all(item["href"] == "/onsite" for item in empty_note["weekly_onsite"])
    assert all(item["meta"] for item in empty_note["weekly_onsite"])
    action = next(item for item in empty_note["next_actions"] if item["id"] == "weekly-three")
    assert action["title"] == "这周给客户改三处"
    assert action["status"] == "待钉住"
    assert action["href"] == "/onsite"

    pinned = client.post("/api/onsite/weekly/pin", headers=headers).json()
    first_id = pinned["this_week"][0]["id"]
    sent = client.post(f"/api/onsite/issues/{first_id}/sent-to-customer", headers=headers)
    assert sent.status_code == 200, sent.text

    after = client.get("/api/dashboard/workbench?days=28", headers=headers).json()
    assert after["weekly_pinned"] is True
    assert after["weekly_onsite"][0]["id"] == first_id
    assert after["weekly_onsite"][0]["status"] == "已发给客户"
    assert after["weekly_onsite"][0]["tone"] == "blue"
    pinned_action = next(item for item in after["next_actions"] if item["id"] == "weekly-three")
    assert pinned_action["status"] == "已钉住"


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
    assert keys == ["findability", "buyer_kpi", "this_week", "retest", "inquiries"]
    assert "这个月记到" in body["markdown"]
    buyer_kpi = next(section for section in body["sections"] if section["key"] == "buyer_kpi")
    assert any("还没有买家原句" in item for item in buyer_kpi["items"])
    assert any("不会编" in item for item in buyer_kpi["items"])


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
        json={"prompt_text": "best industrial fastener exporter", "locale": "en-US"},
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
    assert [section["key"] for section in brief["sections"]] == ["findability", "buyer_kpi", "this_week", "retest", "inquiries"]
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
        prompt_text="best industrial fastener exporter for construction",
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
        prompt_text="best industrial fastener exporter for construction",
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
    assert "Buyers are asking:" in body["paste_text"]
    assert "https://www.ugreen.com/products/usa-65585" in body["paste_text"]
    assert "我们不代发" in body["paste_text"]
    assert any("Buyers are asking:" in item for item in body["this_week"])


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


def test_record_buyer_question_shows_kpi_on_brief_and_home(client: TestClient, demo_user, db) -> None:
    tenant = db.get(Tenant, demo_user.tenant_id)
    tenant.site_origin = "https://www.snipers.com.cn"
    tenant.name = "SNIPERS"
    db.commit()
    headers = auth_header(client)

    rejected = client.post(
        "/api/geo/prompts",
        headers=headers,
        json={"prompt_text": "fastener", "locale": "en-US"},
    )
    assert rejected.status_code == 400
    assert "不要编" in rejected.json()["detail"]

    lock = client.post(
        "/api/geo/prompts",
        headers=headers,
        json={"prompt_text": "best smart lock for renters in apartments", "locale": "en-US", "recorded_from": "sales"},
    )
    assert lock.status_code == 400
    assert "门锁" in lock.json()["detail"]

    created = client.post(
        "/api/geo/prompts",
        headers=headers,
        json={
            "prompt_text": "Which factory can export industrial fasteners to the US?",
            "locale": "en-US",
            "recorded_from": "sales",
            "source_note": "展会后销售转述",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["recorded_from"] == "sales"
    assert created.json()["recorded_from_label"] == "销售听到的"
    assert created.json()["sample_compare_note"] == "" or created.json()["sample_compare_note"]

    listed = client.get("/api/geo/prompts", headers=headers).json()
    assert listed[0]["sample_compare_note"] == "还没联网抽查。"

    brief = client.get("/api/dashboard/customer-brief", headers=headers).json()
    kpi = next(section for section in brief["sections"] if section["key"] == "buyer_kpi")
    assert any("Which factory can export industrial fasteners to the US?" in item for item in kpi["items"])
    assert any("还没联网抽查" in item for item in kpi["items"])
    assert any("不保证这次被提到" in item for item in kpi["items"])

    workbench = client.get("/api/dashboard/workbench?days=28", headers=headers).json()
    assert workbench["geo_questions"][0]["title"].startswith("Which factory")
    assert workbench["geo_questions"][0]["status"] == "还没抽查"
    assert "销售听到的" in workbench["geo_questions"][0]["subtitle"]
    assert "还没有抽查记录" in (workbench["geo_questions"][0].get("trend") or "")


def test_geo_war_room_has_trend_and_cite_pack(client: TestClient, demo_user, db) -> None:
    from datetime import datetime, timedelta, timezone

    from app.models import GeoPrompt, GeoSampleResult, GeoSampleRun

    tenant = db.get(Tenant, demo_user.tenant_id)
    tenant.site_origin = "https://www.snipers.com.cn"
    tenant.name = "SNIPERS"
    prompt = GeoPrompt(
        tenant_id=demo_user.tenant_id,
        prompt_text="Which factory can export industrial fasteners to the US?",
        locale="en-US",
        recorded_from="exhibition",
    )
    db.add(prompt)
    db.flush()
    older = datetime.now(timezone.utc) - timedelta(days=4)
    newer = datetime.now(timezone.utc)
    for evidence_id, started_at, mentioned in (("ev_trend_old", older, False), ("ev_trend_new", newer, True)):
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
                engine="tavily",
                web_grounded="true",
                prompt_text_hash="c" * 64,
                answer_text_hash="d" * 64,
                answer_excerpt="A factory list.",
                mentioned=mentioned,
                citations_json='["https://other.example/fastener"]',
                owned_citations_json="[]",
                third_party_citations_json='["https://other.example/fastener"]',
                competitor_hits="Other Factory",
            )
        )
    db.commit()

    headers = auth_header(client)
    listed = client.get("/api/geo/prompts", headers=headers).json()
    row = next(item for item in listed if item["id"] == prompt.id)
    assert len(row["sample_trend"]) == 2
    assert row["sample_trend"][0]["mentioned"] is False
    assert row["sample_trend"][1]["mentioned"] is True
    assert "2 轮" in row["trend_note"]
    assert "没提到" in row["trend_note"] and "提到了" in row["trend_note"]
    assert "other.example" in " ".join(row["cited_others"])
    assert "Other Factory" in row["competitor_note"]
    assert "Which factory can export industrial fasteners to the US?" in row["page_draft"]
    assert "[NEED_INPUT" in row["page_draft"]
    assert "Do not invent specs" in row["page_draft"]
    assert row["faq_draft"].startswith("Q:")
    assert "# SNIPERS" in row["llms_txt"] or "# SNIPERS" in row["llms_txt"].upper() or "SNIPERS" in row["llms_txt"]
    assert "we do not edit the live site" in row["page_draft"].lower()

    brief = client.get("/api/dashboard/customer-brief", headers=headers).json()
    kpi = next(section for section in brief["sections"] if section["key"] == "buyer_kpi")
    assert "2 轮" in "".join(kpi["items"])
    workbench = client.get("/api/dashboard/workbench?days=28", headers=headers).json()
    assert "2 轮" in (workbench["geo_questions"][0].get("trend") or "")
