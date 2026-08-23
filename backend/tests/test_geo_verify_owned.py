from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.models import GeoPrompt, GeoSampleResult, GeoSampleRun
from tests.conftest import auth_header


def test_verify_sample_result_requires_owned_url(client: TestClient, demo_user, db) -> None:
    headers = auth_header(client)
    tenant_id = demo_user.tenant_id
    prompt = GeoPrompt(tenant_id=tenant_id, prompt_text="best 100W USB-C charger", locale="en-US")
    db.add(prompt)
    db.flush()
    run = GeoSampleRun(tenant_id=tenant_id, config_hash="v1", status="done", started_at=datetime.now(timezone.utc))
    db.add(run)
    db.flush()
    result = GeoSampleResult(
        tenant_id=tenant_id,
        run_id=run.id,
        prompt_id=prompt.id,
        evidence_id="ev_verify_1",
        engine="tavily",
        web_grounded="true",
        prompt_text_hash="a" * 64,
        answer_text_hash="b" * 64,
        mentioned=True,
        citations_json='["https://www.ugreen.com/x","https://item.jd.com/1"]',
        owned_citations_json='["https://www.ugreen.com/x"]',
        third_party_citations_json='["https://item.jd.com/1"]',
        verification_status="pending",
    )
    db.add(result)
    db.commit()

    shop = client.post(
        f"/api/geo/sample-results/{result.id}/verify",
        headers=headers,
        json={"confirmed": True, "checked_url": "https://item.jd.com/1", "passed": True},
    )
    assert shop.status_code == 400
    assert "客户官网" in shop.json()["detail"]

    empty = client.post(
        f"/api/geo/sample-results/{result.id}/verify",
        headers=headers,
        json={"confirmed": True, "checked_url": "", "passed": True},
    )
    assert empty.status_code == 400

    ok = client.post(
        f"/api/geo/sample-results/{result.id}/verify",
        headers=headers,
        json={"confirmed": True, "checked_url": "https://www.ugreen.com/x", "passed": True},
    )
    assert ok.status_code == 200, ok.text
    body = ok.json()
    assert body["verification_status"] == "passed"
    assert "https://www.ugreen.com/x" in body["verification_note"]

    fail = client.post(
        f"/api/geo/sample-results/{result.id}/verify",
        headers=headers,
        json={"confirmed": True, "checked_url": "https://www.ugreen.com/x", "passed": False},
    )
    assert fail.status_code == 200
    assert fail.json()["verification_status"] == "failed"


def test_verify_rejects_result_without_owned(client: TestClient, demo_user, db) -> None:
    headers = auth_header(client)
    tenant_id = demo_user.tenant_id
    prompt = GeoPrompt(tenant_id=tenant_id, prompt_text="best charger", locale="en-US")
    db.add(prompt)
    db.flush()
    run = GeoSampleRun(tenant_id=tenant_id, config_hash="v2", status="done", started_at=datetime.now(timezone.utc))
    db.add(run)
    db.flush()
    result = GeoSampleResult(
        tenant_id=tenant_id,
        run_id=run.id,
        prompt_id=prompt.id,
        evidence_id="ev_verify_2",
        engine="bocha",
        web_grounded="true",
        prompt_text_hash="c" * 64,
        answer_text_hash="d" * 64,
        mentioned=True,
        citations_json='["https://item.jd.com/1"]',
        owned_citations_json="[]",
        third_party_citations_json='["https://item.jd.com/1"]',
        verification_status="skipped",
    )
    db.add(result)
    db.commit()

    res = client.post(
        f"/api/geo/sample-results/{result.id}/verify",
        headers=headers,
        json={"confirmed": True, "checked_url": "https://item.jd.com/1", "passed": True},
    )
    assert res.status_code == 400
    assert "没有客户官网" in res.json()["detail"]
