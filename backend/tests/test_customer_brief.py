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
    assert keys == ["this_week", "onsite", "geo", "untested"]


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
    assert "标题与摘要" in markdown
    assert "买家问题 1 个" in markdown
    assert "尚未检查 8 条" in markdown
    assert any("紧急网站问题" in item for item in body["this_week"])
    assert any("尚未检查" in item for item in body["untested"])
    assert "网站检查" in markdown
    assert "AI 搜索可见度" in markdown
