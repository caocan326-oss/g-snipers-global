from fastapi.testclient import TestClient

from app.llm import LlmResult, OK, UNCONFIGURED
from app.models import OnsiteIssue, SitePage
from tests.conftest import auth_header


def test_onsite_guide_starts_at_setup(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    res = client.get("/api/onsite/guide", headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["current"] == "setup"
    assert body["action_key"] == "save_origin"
    assert body["ai_status"] == UNCONFIGURED
    assert body["steps"][0]["status"] == "current"
    assert "官网" in body["narrative"]
    assert "不会写成已有结论" in body["narrative"]


def test_onsite_guide_collect_then_diagnose_then_confirm(client: TestClient, demo_user, db) -> None:
    headers = auth_header(client)
    saved = client.patch("/api/onsite/settings", headers=headers, json={"site_origin": "https://www.example.com"})
    assert saved.status_code == 200, saved.text

    collect = client.get("/api/onsite/guide", headers=headers).json()
    assert collect["current"] == "collect"
    assert collect["action_key"] == "fetch_site"

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
            title="Title 过长",
            status="open",
            severity="high",
            risk="high",
        )
    )
    db.commit()

    diagnose = client.get("/api/onsite/guide", headers=headers).json()
    assert diagnose["current"] == "diagnose"
    assert diagnose["action_key"] == "generate_drafts"
    assert diagnose["needs_draft"] == 1
    assert diagnose["open_high"] == 1

    issue = db.query(OnsiteIssue).filter(OnsiteIssue.tenant_id == demo_user.tenant_id).one()
    issue.proposed_change = "缩短 title"
    issue.status = "drafted"
    db.commit()

    confirm = client.get("/api/onsite/guide", headers=headers).json()
    assert confirm["current"] == "confirm"
    assert confirm["action_key"] == "review_drafts"
    assert confirm["filter_key"] == "ready_to_execute"

    issue.status = "confirmed"
    db.commit()
    retest = client.get("/api/onsite/guide", headers=headers).json()
    assert retest["current"] == "retest"
    assert retest["action_key"] == "retest_queue"

    issue.status = "verified"
    db.commit()
    done = client.get("/api/onsite/guide", headers=headers).json()
    assert done["complete"] is True
    assert done["action_key"] == "export_report"
    assert all(step["status"] == "done" for step in done["steps"])


def test_onsite_guide_voice_uses_template_when_unconfigured(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    res = client.post("/api/onsite/guide/voice", headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["ai_status"] == UNCONFIGURED
    assert body["narrative"]
    assert "ChatGPT" not in body["narrative"]


def test_onsite_guide_voice_rephrases_counts_only(client: TestClient, demo_user, monkeypatch) -> None:
    headers = auth_header(client)

    def fake_complete(*, system: str, user: str) -> LlmResult:
        assert "未查看的不要写成已有结论" in system
        assert "待改稿:0" in user
        return LlmResult(True, OK, "先登记官网，再抓页。", "")

    monkeypatch.setattr("app.onsite_guide.complete", fake_complete)
    monkeypatch.setattr("app.onsite_guide.configured", lambda: True)
    res = client.post("/api/onsite/guide/voice", headers=headers)
    assert res.status_code == 200, res.text
    assert res.json()["narrative"] == "先登记官网，再抓页。"
    assert res.json()["ai_status"] == OK
