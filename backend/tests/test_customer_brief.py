from fastapi.testclient import TestClient

from app.models import OnsiteIssue, SitePage, Tenant
from tests.conftest import auth_header


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
    assert "这周技术改哪三处" in markdown
    assert "改完你再看一次" in markdown
    assert "这个月有几个老外来问过" in markdown
    assert any("首页标题过长" in item for item in body["this_week"])
    assert any("尚未检查" in item for item in body["untested"])

    workbench = client.get("/api/dashboard/workbench?days=28", headers=headers).json()
    assert workbench["summary"]["onsite_open_critical"] == 1
    assert workbench["summary"]["onsite_open_high"] == 0
    geo_act = next(item for item in workbench["next_actions"] if item["id"] == "geo-sampling")
    assert "8 条检查" in geo_act["subtitle"]
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
    assert "16 条检查" in geo_act["subtitle"]
    assert "16 个买家问题" not in geo_act["subtitle"]
    assert "采样" not in brief["markdown"]
    assert "英文安装问题：先记下 AI 怎么回答，再补说明页" in brief["markdown"]
