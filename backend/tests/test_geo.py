from fastapi.testclient import TestClient

from tests.conftest import auth_header


def test_geo_prompt_slots_are_untested_not_zero(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    created = client.post(
        "/api/geo/prompts",
        headers=headers,
        json={"prompt_text": "best smart lock for renters", "locale": "en-US"},
    )
    assert created.status_code == 201
    observations = created.json()["observations"]
    assert len(observations) == 8
    engines = {o["engine"] for o in observations}
    assert engines == {
        "chatgpt",
        "perplexity",
        "gemini",
        "claude",
        "deepseek",
        "doubao",
        "kimi",
        "tongyi",
    }
    assert all(o["status"] == "untested" for o in observations)
    assert created.json()["cite_rate"] == "未测"
    assert created.json()["absorption_rate"] == "未测"
    assert created.json()["diagnosis"] == "untested"
    assert "share_of_voice" not in created.json()

    summary = client.get("/api/geo/summary", headers=headers)
    assert summary.status_code == 200
    body = summary.json()
    assert body["prompts"] == 1
    assert body["untested"] == 8
    assert body["recorded"] == 0
    assert body["mention_rate"] == "未测"
    assert body["cite_rate"] == "未测"
    assert body["verified_citation_rate"] == "未测"
    assert "percent" not in body


def test_geo_seed_prompt_panel_explains_missing_targets(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    seeded = client.post("/api/geo/prompt-panel/seed", headers=headers)
    assert seeded.status_code == 200
    body = seeded.json()
    assert body["created"] == 0
    assert body["skipped"] == 0
    assert body["prompts"] == 0
    assert "没有可生成问句" in body["note"]


def test_record_observation_and_llms_asset_confirm(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    prompt = client.post(
        "/api/geo/prompts",
        headers=headers,
        json={"prompt_text": "smart lock DSGVO", "locale": "de-DE"},
    ).json()
    obs_id = prompt["observations"][0]["id"]

    recorded = client.patch(
        f"/api/geo/observations/{obs_id}",
        headers=headers,
        json={"status": "mentioned", "notes": "客户经理手工抽查"},
    )
    assert recorded.status_code == 200
    assert recorded.json()["status"] == "mentioned"
    assert recorded.json()["observed_at"]

    summary = client.get("/api/geo/summary", headers=headers).json()
    assert summary["untested"] == 7
    assert summary["recorded"] == 1

    generated = client.post("/api/geo/assets/llms.txt/generate", headers=headers)
    assert generated.status_code == 200
    assert generated.json()["status"] == "draft"
    assert "不是已发布" in generated.json()["body"] or "llms.txt" in generated.json()["title"]

    denied = client.post(
        f"/api/geo/assets/{generated.json()['id']}/mark-ready",
        headers=headers,
        json={"confirmed": False},
    )
    assert denied.status_code == 400

    ready = client.post(
        f"/api/geo/assets/{generated.json()['id']}/mark-ready",
        headers=headers,
        json={"confirmed": True},
    )
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"


def test_checklist_starts_untested(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    page = client.post(
        "/api/seo-pages",
        headers=headers,
        json={"title": "Guide", "target_keyword": "smart lock", "locale": "en-US"},
    ).json()
    items = client.post(
        f"/api/geo/checklists/ensure?seo_page_id={page['id']}",
        headers=headers,
    )
    assert items.status_code == 200
    assert len(items.json()) >= 5
    assert all(i["status"] == "untested" for i in items.json())

    patched = client.patch(
        f"/api/geo/checklist-items/{items.json()[0]['id']}",
        headers=headers,
        json={"status": "pass", "notes": "作者栏已写"},
    )
    assert patched.json()["status"] == "pass"


def test_demand_signal_feeds_geo_prompt(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    market = client.post(
        "/api/markets",
        headers=headers,
        json={"name": "美国", "region": "北美", "country_code": "US", "primary_locale": "en-US"},
    ).json()
    signal = client.post(
        f"/api/markets/{market['id']}/demand-signals",
        headers=headers,
        json={"theme": "renter smart lock", "locale": "en-US"},
    ).json()
    prompt = client.post(f"/api/geo/from-demand-signal/{signal['id']}", headers=headers)
    assert prompt.status_code == 201
    assert prompt.json()["prompt_text"] == "renter smart lock"
    assert len(prompt.json()["observations"]) == 8
    assert all(o["status"] == "untested" for o in prompt.json()["observations"])


def test_geo_ticket_verify_requires_confirm_and_can_reopen(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    prompt = client.post(
        "/api/geo/prompts",
        headers=headers,
        json={"prompt_text": "best lock for apartments", "locale": "en-US"},
    ).json()
    ticket = client.post(
        "/api/geo/tickets",
        headers=headers,
        json={
            "prompt_id": prompt["id"],
            "title": "采样后补对照页",
            "diagnosis": "absent",
            "rationale": "未测不得写成已引用",
            "acceptance_criteria": "人工抽查后再验收",
        },
    )
    assert ticket.status_code == 201
    assert ticket.json()["status"] == "open"
    ticket_id = ticket.json()["id"]

    denied = client.post(
        f"/api/geo/tickets/{ticket_id}/verify",
        headers=headers,
        json={"confirmed": False},
    )
    assert denied.status_code == 400

    verified = client.post(
        f"/api/geo/tickets/{ticket_id}/verify",
        headers=headers,
        json={"confirmed": True, "note": "已按标准复核，仍不声称已被引用"},
    )
    assert verified.status_code == 200
    assert verified.json()["status"] == "done"

    reopened = client.post(
        f"/api/geo/tickets/{ticket_id}/reopen",
        headers=headers,
        json={"note": "复测后仍未出现，重开"},
    )
    assert reopened.json()["status"] == "reopened"

    diagnosis = client.patch(
        f"/api/geo/prompts/{prompt['id']}/diagnosis",
        headers=headers,
        json={"diagnosis": "competitor_dominated"},
    )
    assert diagnosis.json()["diagnosis"] == "competitor_dominated"
    assert diagnosis.json()["cite_rate"] == "未测"


def test_geo_prompt_panel_evidence_rates_and_exports(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    client.post(
        "/api/seo-pages",
        headers=headers,
        json={"title": "Industrial Pump Guide", "target_keyword": "industrial pump supplier", "locale": "en-US"},
    )
    seeded = client.post("/api/geo/prompt-panel/seed", headers=headers)
    assert seeded.status_code == 200
    assert seeded.json()["created"] >= 1

    prompts = client.get("/api/geo/prompts", headers=headers).json()
    prompt = prompts[0]
    obs = prompt["observations"][0]
    recorded = client.patch(
        f"/api/geo/observations/{obs['id']}",
        headers=headers,
        json={
            "status": "cited",
            "surface": "consumer_scrape",
            "response_excerpt": "The answer cites Example Pump Co. as a source.",
            "citation_urls": "https://example.com/pumps",
            "brand_mentions": "Example Pump Co.",
            "competitor_mentions": "Competitor Pump",
            "interpretation_note": "真实前台抽样，不等于稳定排名。",
        },
    )
    assert recorded.status_code == 200
    assert recorded.json()["surface"] == "consumer_scrape"
    assert recorded.json()["evidence_tier"] == "cited"
    assert "example.com" in recorded.json()["citation_urls"]

    refreshed = client.get("/api/geo/prompts", headers=headers).json()[0]
    assert refreshed["cite_rate"] == "100.0%"
    assert refreshed["verified_citation_rate"] == "0.0%"
    assert refreshed["absorption_rate"] == "100.0%"

    summary = client.get("/api/geo/summary", headers=headers).json()
    assert summary["cite_rate"] == "100.0%"
    assert summary["verified_citation_rate"] == "0.0%"
    assert summary["absorption_rate"] == "100.0%"
    assert summary["competitor_mentions"] == 1

    report = client.get("/api/geo/report", headers=headers)
    assert report.status_code == 200
    markdown = report.json()["markdown"]
    assert "GEO 可见性诊断报告" in markdown
    assert "引用率" in markdown
    assert "吸收率" in markdown
    assert "Competitor Pump" in markdown

    table = client.get("/api/geo/report-table", headers=headers)
    assert table.status_code == 200
    csv_text = table.json()["csv"]
    assert "问句,语言,诊断层,引擎" in csv_text
    assert "证据层级,证据说明" in csv_text
    assert "consumer_scrape" in csv_text
    assert "https://example.com/pumps" in csv_text


def test_geo_verified_citation_is_separate_from_plain_citation(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    prompt = client.post(
        "/api/geo/prompts",
        headers=headers,
        json={"prompt_text": "best industrial pump manufacturer", "locale": "en-US"},
    ).json()
    obs = prompt["observations"][0]
    verified = client.patch(
        f"/api/geo/observations/{obs['id']}",
        headers=headers,
        json={
            "status": "verified",
            "surface": "consumer_scrape",
            "sample_type": "manual_incognito",
            "citation_urls": "https://example.com/industrial-pumps",
            "brand_mentions": "Example Pump",
            "response_excerpt": "Example Pump is cited as a source.",
            "interpretation_note": "人工打开 URL 确认可访问且属于客户官网。",
        },
    )
    assert verified.status_code == 200, verified.text
    assert verified.json()["evidence_tier"] == "verified"
    assert verified.json()["evidence_label"] == "引用已核验"

    refreshed = client.get("/api/geo/prompts", headers=headers).json()[0]
    assert refreshed["mention_rate"] == "100.0%"
    assert refreshed["cite_rate"] == "100.0%"
    assert refreshed["verified_citation_rate"] == "100.0%"

    summary = client.get("/api/geo/summary", headers=headers).json()
    assert summary["verified_citation_rate"] == "100.0%"


def test_geo_sample_run_freezes_manual_observations_as_evidence(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    client.put(
        "/api/project-targets",
        headers=headers,
        json={"site_origin": "https://example.com", "markets": []},
    )
    prompt = client.post(
        "/api/geo/prompts",
        headers=headers,
        json={"prompt_text": "best industrial pump supplier", "locale": "en-US"},
    ).json()
    obs = prompt["observations"][0]
    client.patch(
        f"/api/geo/observations/{obs['id']}",
        headers=headers,
        json={
            "status": "verified",
            "surface": "manual_ai_answer",
            "response_excerpt": "Example is listed with https://example.com/pumps as a source.",
            "citation_urls": "https://example.com/pumps https://industry.example.org/list",
            "brand_mentions": "Example",
            "competitor_mentions": "Pump Rival",
            "interpretation_note": "人工核验 URL 可访问。",
        },
    )

    created = client.post(
        "/api/geo/sample-runs/from-observations",
        headers=headers,
        json={"note": "客户测试第一轮"},
    )
    assert created.status_code == 201, created.text
    run = created.json()
    assert run["protocol_version"] == "geo-test-protocol-v1"
    assert run["results_count"] == 1
    assert run["mention_rate"] == "100.0%"
    assert run["cite_rate"] == "100.0%"
    assert run["verified_citation_rate"] == "100.0%"
    result = run["results"][0]
    assert result["evidence_id"].startswith("ev_")
    assert result["owned_citations"] == ["https://example.com/pumps"]
    assert result["third_party_citations"] == ["https://industry.example.org/list"]
    assert result["verification_status"] == "passed"
    assert result["prompt_text_hash"]
    assert result["answer_text_hash"]

    runs = client.get("/api/geo/sample-runs", headers=headers)
    assert runs.status_code == 200
    assert runs.json()[0]["id"] == run["id"]

    summary = client.get("/api/geo/summary", headers=headers).json()
    assert summary["sample_runs"] == 1
    assert summary["evidence_results"] == 1
    assert summary["latest_run_id"] == run["id"]

    report = client.get("/api/geo/report", headers=headers).json()["markdown"]
    assert "证据运行" in report
    assert run["config_hash"] in report
    assert result["evidence_id"] in report

    table = client.get("/api/geo/report-table", headers=headers).json()["csv"]
    assert "run_id,evidence_id,prompt_hash,answer_hash" in table
    assert result["evidence_id"] in table


def test_geo_draft_tickets_from_evidence_rules(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    prompt = client.post(
        "/api/geo/prompts",
        headers=headers,
        json={"prompt_text": "recommended warehouse robot suppliers", "locale": "en-US"},
    ).json()
    obs = prompt["observations"][0]
    client.patch(
        f"/api/geo/observations/{obs['id']}",
        headers=headers,
        json={
            "status": "mentioned",
            "response_excerpt": "The answer mentions Example but recommends RivalBot more often.",
            "brand_mentions": "Example",
            "competitor_mentions": "RivalBot",
        },
    )

    drafted = client.post("/api/geo/tickets/draft-from-evidence", headers=headers)
    assert drafted.status_code == 200, drafted.text
    body = drafted.json()
    assert body["created"] >= 3
    titles = {ticket["title"] for ticket in body["tickets"]}
    assert "GEO-MEAS-002 仅被提及但没有自有引用" in titles
    assert "GEO-OFF-001 竞品在回答中占位" in titles
    assert "GEO-MEAS-003 采样次数不足" in titles

    second = client.post("/api/geo/tickets/draft-from-evidence", headers=headers).json()
    assert second["created"] == 0
    assert second["skipped"] >= 3
