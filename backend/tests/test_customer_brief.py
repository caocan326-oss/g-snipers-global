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
    assert workbench["summary"]["this_week_onsite"] == 1
    assert workbench["summary"]["this_week_open"] == 1
    assert any(item["id"] == "weekly-three" for item in workbench["next_actions"])
    send = next(item for item in workbench["next_actions"] if item["id"] == "weekly-send")
    assert send["title"] == "把这周三处发给客户"
    assert "不代发" in send["subtitle"]
    assert send["href"] == "/home"


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
    send = next(item for item in empty_note["next_actions"] if item["id"] == "weekly-send")
    assert send["title"] == "把这周三处发给客户"
    assert send["status"] == "还没发"

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
    assert any(item["id"] == "weekly-send" for item in after["next_actions"])


def test_weekly_claimed_after_sent_without_opening(client: TestClient, demo_user, db) -> None:
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
    first_id = client.post("/api/onsite/weekly/pin", headers=headers).json()["this_week"][0]["id"]
    sent = client.post(f"/api/onsite/issues/{first_id}/sent-to-customer", headers=headers)
    assert sent.status_code == 200, sent.text
    claimed = client.post(f"/api/onsite/issues/{first_id}/weekly-claimed", headers=headers)
    assert claimed.status_code == 200, claimed.text
    assert claimed.json()["note"].startswith("已记下客户说改完了")
    assert "还要打开核对" in claimed.json()["note"]
    assert "不是官网已改" in claimed.json()["note"]
    workbench = client.get("/api/dashboard/workbench?days=28", headers=headers).json()
    card = next(item for item in workbench["weekly_onsite"] if item["id"] == first_id)
    assert card["status"] == "已发给客户"
    assert card.get("sent") is True
    assert card.get("claimed") is True
    ready = next(item for item in workbench["next_actions"] if item["id"] == "weekly-verdict")
    assert ready["title"] == "客户说改完了，去打开核对"
    assert "客户说了不算官网已改" in ready["subtitle"]


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
    assert keys == ["findability", "buyer_kpi", "cite_assets", "trust_map", "this_week", "verdicts", "retest", "inquiries"]
    assert "这个月记到" in body["markdown"]
    buyer_kpi = next(section for section in body["sections"] if section["key"] == "buyer_kpi")
    assert any("还没有买家原句" in item for item in buyer_kpi["items"])
    assert any("不会编" in item for item in buyer_kpi["items"])
    trust_map = next(section for section in body["sections"] if section["key"] == "trust_map")
    assert any("没有信任源地图" in item for item in trust_map["items"])
    assert any("不会编来源" in item for item in trust_map["items"])


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
    assert [section["key"] for section in brief["sections"]] == ["findability", "buyer_kpi", "cite_assets", "trust_map", "this_week", "verdicts", "retest", "inquiries"]
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
    assert "https://www.ugreen.com/products/usa-65585" in body["paste_text"]
    assert "不代发" in body["paste_text"]
    assert "LinkedIn" not in body["paste_text"]


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
    assert created.json()["watch_due"] is True
    assert listed[0]["watch_due"] is True
    assert workbench["summary"]["geo_watch_due"] >= 1
    assert any(item["id"] == "geo-watch-due" for item in workbench["next_actions"])
    assert any("到期该复测" in item for item in kpi["items"])


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
    assert row["page_draft"] == "没有 Fact Pack（已批英文说明 + 官网）不能出对外草稿。不要编规格。"
    assert row["faq_draft"] == ""
    assert row["llms_txt"] == ""
    assert "NEED_INPUT" not in row["page_draft"]
    assert "Do not invent specs" not in row["page_draft"]

    brief = client.get("/api/dashboard/customer-brief", headers=headers).json()
    kpi = next(section for section in brief["sections"] if section["key"] == "buyer_kpi")
    assert "2 轮" in "".join(kpi["items"])
    assets = next(section for section in brief["sections"] if section["key"] == "cite_assets")
    assert any("不能出对外草稿" in item for item in assets["items"])
    workbench = client.get("/api/dashboard/workbench?days=28", headers=headers).json()
    assert "2 轮" in (workbench["geo_questions"][0].get("trend") or "")
    assert row["watch_due"] is False
    assert "常驻监控中" in row["watch_note"]
    assert row["cite_stage"] == "draft"
    assert "还没把这段发给客户" in row["cite_stage_label"]
    assert row["cite_paste"] == row["page_draft"]
    assert workbench["summary"]["fact_pack_ready"] is False
    assert workbench["next_actions"][0]["id"] == "fact-pack"
    assert workbench["next_actions"][0]["href"] == "/offsite?tab=content"
    assert all(item["id"] != "cite-fact-pack" for item in workbench["next_actions"])


def test_cite_pack_english_when_fact_pack_ready(client: TestClient, demo_user, db) -> None:
    from app.models import FactPack

    tenant = db.get(Tenant, demo_user.tenant_id)
    tenant.site_origin = "https://www.snipers.com.cn"
    tenant.name = "SNIPERS"
    db.add(
        FactPack(
            tenant_id=demo_user.tenant_id,
            website="https://www.snipers.com.cn",
            approved_boilerplate_en="SNIPERS supplies industrial fasteners for export buyers.",
            product_categories_en="industrial fasteners",
            status="approved",
        )
    )
    db.commit()
    headers = auth_header(client)
    created = client.post(
        "/api/geo/prompts",
        headers=headers,
        json={
            "prompt_text": "Which factory can export industrial fasteners to the US?",
            "locale": "en-US",
            "recorded_from": "sales",
        },
    )
    assert created.status_code == 201, created.text
    row = created.json()
    assert "Which factory can export industrial fasteners to the US?" in row["page_draft"]
    assert "SNIPERS supplies industrial fasteners" in row["page_draft"]
    assert "NEED_INPUT" not in row["page_draft"]
    assert "不能出对外草稿" not in row["page_draft"]
    assert row["faq_draft"].startswith("Q:")
    assert "www.snipers.com.cn" in row["llms_txt"]
    assert "we do not edit the live site" in row["page_draft"].lower()
    assert "我们不代改" in row["cite_paste"]
    workbench = client.get("/api/dashboard/workbench?days=28", headers=headers).json()
    assert any(item["id"] == "cite-send" for item in workbench["next_actions"])


def test_cite_pack_loop_send_publish_retest(client: TestClient, demo_user, db, monkeypatch) -> None:
    from types import SimpleNamespace

    from app import geo_providers
    from app.models import GeoPrompt

    tenant = db.get(Tenant, demo_user.tenant_id)
    tenant.site_origin = "https://www.snipers.com.cn"
    tenant.name = "SNIPERS"
    db.commit()
    headers = auth_header(client)
    created = client.post(
        "/api/geo/prompts",
        headers=headers,
        json={
            "prompt_text": "Which factory can export industrial fasteners to the US?",
            "locale": "en-US",
            "recorded_from": "sales",
        },
    )
    assert created.status_code == 201, created.text
    prompt_id = created.json()["id"]
    assert created.json()["cite_stage"] == "draft"
    assert "不能出对外草稿" in created.json()["page_draft"]

    sent = client.post(f"/api/geo/prompts/{prompt_id}/cite-stage", headers=headers, json={"stage": "sent"})
    assert sent.status_code == 200, sent.text
    assert sent.json()["cite_stage"] == "sent"
    assert "已把这段发给客户" in sent.json()["cite_stage_label"]

    missing = client.post(
        f"/api/geo/prompts/{prompt_id}/cite-stage",
        headers=headers,
        json={"stage": "published"},
    )
    assert missing.status_code == 400
    assert "页地址" in missing.json()["detail"]

    early = client.post(f"/api/geo/prompts/{prompt_id}/cite-retest", headers=headers)
    assert early.status_code == 400
    assert "还没说已贴上" in early.json()["detail"]

    live = client.post(
        f"/api/geo/prompts/{prompt_id}/cite-stage",
        headers=headers,
        json={"stage": "published", "published_url": "https://www.snipers.com.cn/snipers/article/articlelist/cat_id/3.html"},
    )
    assert live.status_code == 200, live.text
    assert live.json()["cite_stage"] == "published"
    assert live.json()["cite_published_url"].endswith("cat_id/3.html")

    brief = client.get("/api/dashboard/customer-brief", headers=headers).json()
    assets = next(section for section in brief["sections"] if section["key"] == "cite_assets")
    assert any("客户说已贴上" in item for item in assets["items"])
    workbench = client.get("/api/dashboard/workbench?days=28", headers=headers).json()
    assert workbench["geo_questions"][0]["status"] == "客户已贴，可再测"
    assert any(item["id"] == "cite-retest" for item in workbench["next_actions"])

    monkeypatch.setattr(geo_providers.settings, "bocha_api_key", "")
    monkeypatch.setattr(geo_providers.settings, "dashscope_api_key", "")
    monkeypatch.setattr(geo_providers.settings, "tavily_api_key", "test-tavily")

    def fake_sample(provider, prompt_text, **kwargs):
        return SimpleNamespace(
            provider=provider,
            engine=provider,
            model="fake",
            answer="https://other.example/fastener",
            citations=["https://other.example/fastener"],
            web_grounded=True,
            surface="api_search",
        )

    monkeypatch.setattr("app.routers.geo.sample_with_provider", fake_sample)
    retest = client.post(f"/api/geo/prompts/{prompt_id}/cite-retest", headers=headers)
    assert retest.status_code == 200, retest.text
    assert retest.json()["results_count"] >= 1


def test_geo_watch_due_only_samples_recorded_prompts(client: TestClient, demo_user, db, monkeypatch) -> None:
    from datetime import datetime, timedelta, timezone
    from types import SimpleNamespace

    from app import geo_providers
    from app.models import GeoPrompt, GeoSampleResult, GeoSampleRun

    tenant = db.get(Tenant, demo_user.tenant_id)
    tenant.site_origin = "https://www.snipers.com.cn"
    tenant.name = "SNIPERS"
    db.commit()
    headers = auth_header(client)
    client.get("/api/geo/prompts", headers=headers)

    fresh = GeoPrompt(
        tenant_id=demo_user.tenant_id,
        prompt_text="Which factory can export industrial fasteners to the US?",
        locale="en-US",
        recorded_from="sales",
    )
    stale = GeoPrompt(
        tenant_id=demo_user.tenant_id,
        prompt_text="Do you have ISO documents for export fasteners?",
        locale="en-US",
        recorded_from="inquiry",
    )
    db.add_all([fresh, stale])
    db.flush()
    now = datetime.now(timezone.utc)
    for prompt, sampled_at, evidence_id in (
        (fresh, now, "ev_watch_fresh"),
        (stale, now - timedelta(days=8), "ev_watch_stale"),
    ):
        run = GeoSampleRun(
            tenant_id=demo_user.tenant_id,
            config_hash=evidence_id,
            status="done",
            started_at=sampled_at,
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
                mentioned=False,
                sampled_at=sampled_at,
            )
        )
    db.commit()

    watches = client.get("/api/geo/watches", headers=headers).json()
    due_ids = {item["prompt_id"] for item in watches["items"] if item["due"]}
    assert stale.id in due_ids
    assert fresh.id not in due_ids
    assert watches["due"] >= 1
    listed = {row["id"]: row for row in client.get("/api/geo/prompts", headers=headers).json()}
    assert listed[stale.id]["watch_due"] is True
    assert listed[fresh.id]["watch_due"] is False
    workbench = client.get("/api/dashboard/workbench?days=28", headers=headers).json()
    assert workbench["summary"]["geo_watch_due"] >= 1
    stale_card = next(item for item in workbench["geo_questions"] if item["id"] == stale.id)
    assert stale_card["status"] == "到期该复测"

    monkeypatch.setattr(geo_providers.settings, "bocha_api_key", "")
    monkeypatch.setattr(geo_providers.settings, "dashscope_api_key", "")
    monkeypatch.setattr(geo_providers.settings, "tavily_api_key", "test-tavily")
    sampled: list[str] = []

    def fake_sample(provider, prompt_text, **kwargs):
        sampled.append(prompt_text)
        return SimpleNamespace(
            provider=provider,
            engine=provider,
            model="fake",
            answer="https://other.example/fastener",
            citations=["https://other.example/fastener"],
            web_grounded=True,
            surface="api_search",
        )

    monkeypatch.setattr("app.routers.geo.sample_with_provider", fake_sample)
    ran = client.post("/api/geo/watches/run-due", headers=headers)
    assert ran.status_code == 200, ran.text
    body = ran.json()
    assert stale.id in body["prompt_ids"]
    assert fresh.id not in body["prompt_ids"]
    assert "Which factory can export industrial fasteners to the US?" not in sampled
    assert "Do you have ISO documents for export fasteners?" in sampled
    assert "不编问句" in body["note"] or "没有原句不会编" in body["note"]
    after = client.get("/api/geo/watches", headers=headers).json()
    assert stale.id not in {item["prompt_id"] for item in after["items"] if item["due"]}


def test_english_boss_report_keeps_closed_retest(client: TestClient, demo_user, db) -> None:
    from datetime import datetime, timezone

    from app.models import GeoPrompt, GeoTicket

    tenant = db.get(Tenant, demo_user.tenant_id)
    tenant.site_origin = "https://www.example.com"
    tenant.name = "Example"
    pages = [
        SitePage(tenant_id=demo_user.tenant_id, path="/one", locale="en-US", title="One", crawl_status="ok"),
        SitePage(tenant_id=demo_user.tenant_id, path="/two", locale="en-US", title="Two", crawl_status="ok"),
        SitePage(tenant_id=demo_user.tenant_id, path="/three", locale="en-US", title="Three", crawl_status="ok"),
    ]
    db.add_all(pages)
    db.flush()
    for page in pages:
        db.add(
            OnsiteIssue(
                tenant_id=demo_user.tenant_id,
                page_id=page.id,
                category="tdk",
                title="首页标题过长",
                status="open",
                severity="high",
                risk="high",
            )
        )
    prompt = GeoPrompt(
        tenant_id=demo_user.tenant_id,
        prompt_text="什么获客软件比较好",
        locale="zh-CN",
        recorded_from="sales",
    )
    db.add(prompt)
    db.flush()
    db.add(
        GeoTicket(
            tenant_id=demo_user.tenant_id,
            prompt_id=prompt.id,
            title="买家问「什么获客软件比较好」时没提到我们",
            diagnosis="absent",
            status="done",
            retest_result="上次没有提到，这次仍没有提到。两次都没有给出官网。贴上了不等于被提到。",
            closed_at=datetime.now(timezone.utc),
        )
    )
    db.commit()

    headers = auth_header(client)
    body = client.get("/api/dashboard/customer-brief", headers=headers).json()
    english = body["english_markdown"]
    paste = body["english_paste"]
    assert body["english_title"].startswith("Weekly report")
    assert "什么获客软件比较好" in english
    assert "not mentioned" in english
    assert "official site not given" in english
    assert "Ticket closed" in english
    assert "0 recorded this month" in english
    assert "ChatGPT recommended" not in english
    assert "ISO" not in english
    assert "TÜV" not in english
    assert "紧急网站问题" not in body["english_headline"]
    assert "site page" in body["english_headline"]
    assert "这周请改这几处" in body["paste_text"]
    assert "什么获客软件比较好" not in body["paste_text"]
    assert "不能出对外草稿" not in paste
    assert "什么获客软件比较好" in paste
    assert any("/one" in item or "/two" in item or "/three" in item for item in body["this_week"])


def test_workbench_this_week_is_not_the_open_board(client: TestClient, demo_user, db) -> None:
    from app.models import GeoPrompt, GeoTicket

    tenant = db.get(Tenant, demo_user.tenant_id)
    tenant.site_origin = "https://www.snipers.com.cn"
    tenant.name = "SNIPERS"
    pages = [
        SitePage(tenant_id=demo_user.tenant_id, path=f"/page-{index}", locale="zh-CN", title=f"P{index}", crawl_status="ok")
        for index in range(8)
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
                severity="critical",
                risk="high",
            )
            for page in pages
        ]
    )
    prompt = GeoPrompt(
        tenant_id=demo_user.tenant_id,
        prompt_text="Which factory can export industrial fasteners to the US?",
        locale="en-US",
        recorded_from="sales",
    )
    db.add(prompt)
    db.flush()
    db.add(
        GeoTicket(
            tenant_id=demo_user.tenant_id,
            prompt_id=prompt.id,
            title="买家问紧固件出口时没提到我们",
            diagnosis="absent",
            status="open",
        )
    )
    db.commit()

    headers = auth_header(client)
    workbench = client.get("/api/dashboard/workbench?days=28", headers=headers).json()
    board = client.get("/api/execution/items", headers=headers).json()
    summary = workbench["summary"]
    weekly = workbench["weekly_onsite"]

    assert len(weekly) == 3
    assert summary["this_week_onsite"] == 3
    assert summary["geo_tickets_open"] == 1
    assert summary["this_week_open"] == 4
    assert summary["onsite_open_critical"] == 8
    assert board["total_open"] >= 9
    assert summary["this_week_open"] < board["total_open"]
    assert {item["subtitle"] for item in weekly} <= {f"/page-{index}" for index in range(8)}
    assert workbench["geo_questions"][0]["title"].startswith("Which factory")
    assert workbench["geo_questions"][0]["status"] == "还没抽查"
    assert any(item["id"] == "weekly-three" for item in workbench["next_actions"])
    assert any(item["id"] == "geo-sampling" or item["id"] == "geo-ticket" for item in workbench["next_actions"])
    assert all("102" not in item["title"] for item in workbench["next_actions"])


def test_workbench_open_verify_stays_on_week_and_can_restore(client: TestClient, demo_user, db, monkeypatch) -> None:
    tenant = db.get(Tenant, demo_user.tenant_id)
    tenant.site_origin = "https://www.snipers.com.cn"
    tenant.name = "SNIPERS"
    first = SitePage(tenant_id=demo_user.tenant_id, path="/snipers/article/articlelist/cat_id/3.html", locale="zh-CN", title="知识百科", crawl_status="ok")
    second = SitePage(tenant_id=demo_user.tenant_id, path="/snipers/article/articlelist/cat_id/1.html", locale="zh-CN", title="资讯", crawl_status="ok")
    third = SitePage(tenant_id=demo_user.tenant_id, path="/en/Article/detail/article_id/4.html", locale="en-US", title="SEO", crawl_status="ok")
    filler = SitePage(tenant_id=demo_user.tenant_id, path="/snipers/Article/detail/article_id/5.html", locale="zh-CN", title="第五篇", crawl_status="ok")
    db.add_all([first, second, third, filler])
    db.flush()
    week_rows = [
        OnsiteIssue(tenant_id=demo_user.tenant_id, page_id=first.id, category="schema", title="页面说明和正文对不上", severity="critical", status="open", risk="high"),
        OnsiteIssue(tenant_id=demo_user.tenant_id, page_id=second.id, category="crawl", title="网址层级太深，不好被找到", severity="critical", status="open", risk="high"),
        OnsiteIssue(tenant_id=demo_user.tenant_id, page_id=third.id, category="crawl", title="网址层级太深，不好被找到", severity="critical", status="open", risk="high"),
        OnsiteIssue(tenant_id=demo_user.tenant_id, page_id=filler.id, category="tdk", title="首页标题过长", severity="critical", status="open", risk="high"),
    ]
    db.add_all(week_rows)
    db.commit()

    headers = auth_header(client)
    target_id = client.post("/api/onsite/weekly/pin", headers=headers).json()["this_week"][0]["id"]
    sent = client.post(f"/api/onsite/issues/{target_id}/sent-to-customer", headers=headers)
    assert sent.status_code == 200, sent.text

    class Snap:
        usable = True

    def _pass(tmp_db, user, page, origin):
        issue = tmp_db.get(OnsiteIssue, target_id)
        assert issue is not None
        issue.status = "verified"
        return Snap(), 0, 1

    monkeypatch.setattr("app.routers.onsite.issue_actions._fetch_one_registered", _pass)
    opened = client.post(f"/api/onsite/issues/{target_id}/weekly-recheck", headers=headers)
    assert opened.status_code == 200, opened.text
    workbench = client.get("/api/dashboard/workbench?days=28", headers=headers).json()
    card = next(item for item in workbench["weekly_onsite"] if item["id"] == target_id)
    assert card["status"] == "打开过，还没过"
    assert workbench["weekly_onsite"][0]["id"] == target_id
    assert workbench["weekly_can_restore"] is False
    assert card["subtitle"].startswith("/")

    from app.onsite_loop import save_weekly_pin

    keepers = [item["id"] for item in workbench["weekly_onsite"] if item["id"] != target_id]
    save_weekly_pin(
        db,
        demo_user.tenant_id,
        issue_ids=[*keepers, week_rows[3].id],
        sent_ids=[],
        last_dropped_id=target_id,
        last_dropped_sent=True,
    )
    dropped = db.get(OnsiteIssue, target_id)
    assert dropped is not None
    dropped.status = "verified"
    db.commit()

    after_drop = client.get("/api/dashboard/workbench?days=28", headers=headers).json()
    assert after_drop["weekly_can_restore"] is True
    assert all(item["id"] != target_id for item in after_drop["weekly_onsite"])

    restored = client.post("/api/onsite/weekly/restore-dropped", headers=headers)
    assert restored.status_code == 200, restored.text
    home = client.get("/api/dashboard/workbench?days=28", headers=headers).json()
    assert home["weekly_onsite"][0]["id"] == target_id
    assert home["weekly_onsite"][0]["status"] == "已发给客户"
    assert home["weekly_onsite"][0]["subtitle"].startswith("/")
    assert home["weekly_can_restore"] is False
