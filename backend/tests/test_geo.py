from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.geo_providers import _bailian_answer, _bailian_urls
from tests.conftest import auth_header


def test_bailian_reads_native_search_info() -> None:
    data = {
        "output": {
            "choices": [{"message": {"content": "Answer without raw links."}}],
            "search_info": {
                "search_results": [
                    {"index": 1, "url": "https://www.sulzer.com/en"},
                    {"index": 2, "url": "https://industry.example/report"},
                ]
            },
        }
    }
    assert _bailian_answer(data) == "Answer without raw links."
    assert _bailian_urls(data) == ["https://industry.example/report", "https://www.sulzer.com/en"]


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
    assert "AI 搜索说明" in markdown
    assert "引用率" in markdown
    assert "吸收率" in markdown
    assert "Competitor Pump" in markdown

    table = client.get("/api/geo/report-table", headers=headers)
    assert table.status_code == 200
    csv_text = table.json()["csv"]
    assert "问句,Prompt ID,Prompt 类型,Prompt 包,语言,诊断层,引擎" in csv_text
    assert "证据层级,证据说明" in csv_text
    assert "consumer_scrape" in csv_text
    assert "https://example.com/pumps" in csv_text
    assert prompt["prompt_pack_id"] == "export-b2b-observation-v1"
    assert prompt["prompt_type"] in {"branded", "category", "competitor", "task"}


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
    assert result["prompt_type"] == "custom"
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
    assert summary["latest_run_at"]

    report = client.get("/api/geo/report", headers=headers).json()["markdown"]
    assert "证据运行" in report
    assert run["config_hash"] in report
    assert result["evidence_id"] in report

    table = client.get("/api/geo/report-table", headers=headers).json()["csv"]
    assert "run_id,evidence_id,prompt_hash,answer_hash" in table
    assert result["evidence_id"] in table


def test_geo_b2b_prompt_pack_keeps_prompt_ids_and_types(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    market = client.post(
        "/api/markets",
        headers=headers,
        json={"name": "United States", "region": "North America", "country_code": "US", "primary_locale": "en-US"},
    ).json()
    client.post(
        f"/api/markets/{market['id']}/competitors",
        headers=headers,
        json={"name": "ApexFlow", "website": "https://apex.example"},
    )
    client.post(
        "/api/seo-pages",
        headers=headers,
        json={
            "title": "Ball Valve Guide",
            "target_keyword": "industrial ball valves",
            "locale": "en-US",
            "market_id": market["id"],
        },
    )

    seeded = client.post("/api/geo/prompt-panel/seed", headers=headers).json()
    assert seeded["created"] >= 8
    prompts = client.get("/api/geo/prompts", headers=headers).json()
    keys = {p["prompt_key"] for p in prompts}
    types = {p["prompt_type"] for p in prompts}
    assert "EX-EN-B01" in keys
    assert "EX-EN-C01" in keys
    assert "EX-EN-P01" in keys
    assert {"branded", "category", "competitor", "task"} <= types
    assert all(p["prompt_pack_id"] == "export-b2b-observation-v1" for p in prompts)


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
    assert body["created"] >= 1
    titles = {ticket["title"] for ticket in body["tickets"]}
    assert any("没给出官网" in title or "先推了别人" in title for title in titles)
    assert all("采样次数不足" not in title for title in titles)
    assert all("不要求这次必须提到" in (ticket["acceptance_criteria"] or "") for ticket in body["tickets"])
    assert all("再抽查" in (ticket["acceptance_criteria"] or "") for ticket in body["tickets"])

    second = client.post("/api/geo/tickets/draft-from-evidence", headers=headers).json()
    assert second["created"] == 0
    assert second["skipped"] >= 1


def test_geo_auto_sampling_aggregate_creates_ent_off_tickets(client: TestClient, demo_user, monkeypatch) -> None:
    headers = auth_header(client)
    client.put(
        "/api/project-targets",
        headers=headers,
        json={"site_origin": "https://example.com", "markets": []},
    )
    prompt = client.post(
        "/api/geo/prompts",
        headers=headers,
        json={
            "prompt_text": "Best industrial valve manufacturers for export to the United States",
            "locale": "en-US",
            "prompt_pack_id": "export-b2b-observation-v1",
            "prompt_key": "EX-EN-C01",
            "prompt_type": "category",
        },
    ).json()

    monkeypatch.setattr(
        "app.routers.geo.sample_with_provider",
        lambda *args, **kwargs: SimpleNamespace(
            provider="perplexity",
            engine="perplexity",
            model="fake-grounded",
            answer="Buyers often compare suppliers listed at https://www.thomasnet.com and https://www.globalspec.com.",
            citations=["https://www.thomasnet.com", "https://www.globalspec.com"],
            web_grounded=True,
            surface="api_search",
        ),
    )

    run = client.post(
        "/api/geo/sample-runs/auto",
        headers=headers,
        json={"prompt_ids": [prompt["id"]], "trials": 3, "limit": 1, "provider": "perplexity", "engine": "perplexity", "web_grounded": "true"},
    )
    assert run.status_code == 201, run.text
    body = run.json()
    assert body["results_count"] == 3
    assert body["aggregate"]["byPrompt"][0]["type"] == "category"
    assert body["aggregate"]["byPrompt"][0]["trials"] == 3
    assert body["aggregate"]["byPrompt"][0]["mention_rate"] == 0
    assert "thomasnet.com" in body["aggregate"]["byPrompt"][0]["top_third_party_domains"]

    drafted = client.post("/api/geo/tickets/draft-from-evidence", headers=headers)
    assert drafted.status_code == 200, drafted.text
    tickets = drafted.json()["tickets"]
    titles = {ticket["title"] for ticket in tickets}
    assert any("没提到我们" in title for title in titles)
    assert any("对应页" in (ticket["rationale"] or "") for ticket in tickets)
    assert any("渠道" in (ticket["rationale"] or "") for ticket in tickets)
    assert all("不要求这次必须提到" in (ticket["acceptance_criteria"] or "") for ticket in tickets)
    assert all("trials>=" not in (ticket["acceptance_criteria"] or "") for ticket in tickets)


def test_geo_provider_status_and_deepseek_non_grounded_does_not_count_citations(client: TestClient, demo_user, monkeypatch) -> None:
    headers = auth_header(client)
    prompt = client.post(
        "/api/geo/prompts",
        headers=headers,
        json={
            "prompt_text": "Best industrial valve suppliers",
            "locale": "en-US",
            "prompt_type": "category",
        },
    ).json()
    status = client.get("/api/geo/providers/status", headers=headers)
    assert status.status_code == 200
    providers = {row["key"]: row for row in status.json()["providers"]}
    assert providers["deepseek"]["web_grounded"] is False
    assert providers["tavily"]["web_grounded"] is True

    monkeypatch.setattr(
        "app.routers.geo.sample_with_provider",
        lambda *args, **kwargs: SimpleNamespace(
            provider="deepseek",
            engine="deepseek",
            model="fake-llm",
            answer="Example is mentioned with a possible URL https://example.com/pumps, but this is non-grounded text.",
            citations=["https://example.com/pumps"],
            web_grounded=False,
            surface="llm_api_non_grounded",
        ),
    )
    run = client.post(
        "/api/geo/sample-runs/auto",
        headers=headers,
        json={"prompt_ids": [prompt["id"]], "trials": 1, "limit": 1, "provider": "deepseek"},
    )
    assert run.status_code == 201, run.text
    body = run.json()
    assert body["results_count"] == 1
    assert body["cite_rate"] == "0.0%"
    result = body["results"][0]
    assert result["web_grounded"] == "false"
    assert result["owned_citations"] == []
    assert "非联网" in result["verification_note"]


def test_geo_bocha_and_bailian_provider_adapters(client: TestClient, demo_user, monkeypatch) -> None:
    headers = auth_header(client)
    client.put(
        "/api/project-targets",
        headers=headers,
        json={"site_origin": "https://sulzer.com", "markets": []},
    )
    prompt = client.post(
        "/api/geo/prompts",
        headers=headers,
        json={"prompt_text": "Sulzer alternatives for industrial pumps", "locale": "en-US", "prompt_type": "competitor"},
    ).json()

    from app import geo_providers

    monkeypatch.setattr(geo_providers.settings, "bocha_api_key", "test-bocha")
    monkeypatch.setattr(geo_providers.settings, "dashscope_api_key", "test-dashscope")
    monkeypatch.setattr(geo_providers.settings, "tavily_api_key", "test-tavily")

    status = client.get("/api/geo/providers/status", headers=headers).json()
    providers = {row["key"]: row for row in status["providers"]}
    assert providers["bocha"]["role"] == "search"
    assert providers["bocha"]["configured"] is True
    assert providers["bailian"]["role"] == "grounded_answer"
    assert providers["bailian"]["configured"] is True
    assert providers["tavily"]["configured"] is True

    class FakeResponse:
        def __init__(self, status_code: int, data: dict):
            self.status_code = status_code
            self._data = data
            self.text = "ok"

        def json(self):
            return self._data

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url: str, headers: dict, json: dict):
            if "tavily.com" in url:
                return FakeResponse(
                    200,
                    {
                        "answer": "Sulzer is a pump brand.",
                        "results": [
                            {"title": "Sulzer official", "url": "https://www.sulzer.com/en", "content": "Official site"},
                            {"title": "Industry report", "url": "https://industry.example/report", "content": "Third party"},
                        ],
                    },
                )
            if "bochaai" in url:
                return FakeResponse(
                    200,
                    {
                        "data": {
                            "webPages": {
                                "value": [
                                    {
                                        "name": "Sulzer on GlobalSpec",
                                        "url": "https://www.globalspec.com/supplier/sulzer",
                                        "snippet": "Sulzer pump supplier profile",
                                    },
                                    {
                                        "name": "Sulzer official",
                                        "url": "https://www.sulzer.com/en",
                                        "summary": "Official Sulzer site",
                                    },
                                ]
                            }
                        }
                    },
                )
            return FakeResponse(
                200,
                {
                    "output": {
                        "choices": [
                            {
                                "message": {
                                    "content": "Sulzer is often compared with Flowserve and Alfa Laval."
                                }
                            }
                        ],
                        "search_info": {
                            "search_results": [
                                {"index": 1, "title": "Sulzer", "url": "https://www.sulzer.com/en"},
                                {"index": 2, "title": "Industry report", "url": "https://industry.example/report"},
                            ]
                        },
                    }
                },
            )

    monkeypatch.setattr(geo_providers.httpx, "Client", FakeClient)

    bocha_run = client.post(
        "/api/geo/sample-runs/auto",
        headers=headers,
        json={"prompt_ids": [prompt["id"]], "trials": 1, "limit": 1, "provider": "bocha"},
    )
    assert bocha_run.status_code == 201, bocha_run.text
    bocha_result = bocha_run.json()["results"][0]
    assert bocha_result["web_grounded"] == "true"
    assert "https://www.sulzer.com/en" in bocha_result["owned_citations"]
    assert "https://www.globalspec.com/supplier/sulzer" in bocha_result["third_party_citations"]

    bailian_run = client.post(
        "/api/geo/sample-runs/auto",
        headers=headers,
        json={"prompt_ids": [prompt["id"]], "trials": 1, "limit": 1, "provider": "bailian"},
    )
    assert bailian_run.status_code == 201, bailian_run.text
    bailian_result = bailian_run.json()["results"][0]
    assert bailian_result["engine"] == "bailian"
    assert "https://www.sulzer.com/en" in bailian_result["owned_citations"]
    assert "https://industry.example/report" in bailian_result["third_party_citations"]

    tavily_run = client.post(
        "/api/geo/sample-runs/auto",
        headers=headers,
        json={"prompt_ids": [prompt["id"]], "trials": 1, "limit": 1, "provider": "tavily"},
    )
    assert tavily_run.status_code == 201, tavily_run.text
    tavily_result = tavily_run.json()["results"][0]
    assert tavily_result["engine"] == "tavily"
    assert "https://www.sulzer.com/en" in tavily_result["owned_citations"]
    assert "https://industry.example/report" in tavily_result["third_party_citations"]


def test_geo_grounded_batch_runs_each_configured_source(client: TestClient, demo_user, monkeypatch) -> None:
    from app import geo_providers

    headers = auth_header(client)
    prompt = client.post(
        "/api/geo/prompts",
        headers=headers,
        json={"prompt_text": "How do renters install a smart lock?", "locale": "en-US"},
    ).json()
    monkeypatch.setattr(geo_providers.settings, "bocha_api_key", "test-bocha")
    monkeypatch.setattr(geo_providers.settings, "dashscope_api_key", "test-dashscope")
    monkeypatch.setattr(geo_providers.settings, "tavily_api_key", "test-tavily")

    def fake_sample(provider, prompt_text, **kwargs):
        return SimpleNamespace(
            provider=provider,
            engine=provider,
            model="fake",
            answer=f"{provider} found https://other.example/{provider}",
            citations=[f"https://other.example/{provider}"],
            web_grounded=True,
            surface="api_search",
        )

    monkeypatch.setattr("app.routers.geo.sample_with_provider", fake_sample)
    batch = client.post(
        "/api/geo/sample-runs/auto-grounded",
        headers=headers,
        json={"prompt_ids": [prompt["id"]], "trials": 1, "limit": 1},
    )
    assert batch.status_code == 201, batch.text
    body = batch.json()
    assert set(body["providers"]) == {"bocha", "tavily"}
    assert body["results_count"] == 2
    assert body["failed"] == []
    assert "DeepSeek" in body["note"]
    engines = {run["engines"][0] for run in body["runs"]}
    assert engines == {"bocha", "tavily"}
    summary = client.get("/api/geo/summary", headers=headers).json()
    assert summary["latest_sampled"] == 2
    assert summary["latest_mentioned"] == 0
    assert summary["latest_owned"] == 0
    assert summary["latest_third_party"] == 2


def test_tavily_country_ignores_provider_labels() -> None:
    from app.geo_providers import _tavily_country

    assert _tavily_country("Tavily") == ""
    assert _tavily_country("API") == ""
    assert _tavily_country("博查") == ""
    assert _tavily_country("US") == "united states"
    assert _tavily_country("de") == "germany"


def test_geo_summary_does_not_compare_two_providers_in_the_same_click(client: TestClient, demo_user, db) -> None:
    from datetime import datetime, timedelta, timezone

    from app.models import GeoPrompt, GeoSampleResult, GeoSampleRun

    tenant_id = demo_user.tenant_id
    prompt = GeoPrompt(tenant_id=tenant_id, prompt_text="best 100W USB-C charger", locale="en-US")
    db.add(prompt)
    db.flush()
    older = datetime.now(timezone.utc) - timedelta(hours=2)
    now = datetime.now(timezone.utc)
    first = GeoSampleRun(tenant_id=tenant_id, config_hash="old", status="done", started_at=older)
    db.add(first)
    db.flush()
    db.add(
        GeoSampleResult(
            tenant_id=tenant_id,
            run_id=first.id,
            prompt_id=prompt.id,
            evidence_id="ev_old_bocha",
            engine="bocha",
            web_grounded="true",
            prompt_text_hash="a" * 64,
            answer_text_hash="b" * 64,
            mentioned=False,
            citations_json="[]",
            owned_citations_json="[]",
            third_party_citations_json='["https://other.example"]',
        )
    )
    bocha = GeoSampleRun(tenant_id=tenant_id, config_hash="batch-b", status="done", started_at=now)
    tavily = GeoSampleRun(
        tenant_id=tenant_id,
        config_hash="batch-t",
        status="done",
        started_at=now + timedelta(seconds=20),
    )
    db.add_all([bocha, tavily])
    db.flush()
    db.add(
        GeoSampleResult(
            tenant_id=tenant_id,
            run_id=bocha.id,
            prompt_id=prompt.id,
            evidence_id="ev_new_bocha",
            engine="bocha",
            web_grounded="true",
            prompt_text_hash="a" * 64,
            answer_text_hash="c" * 64,
            mentioned=True,
            brand_hits="ugreen",
            citations_json="[]",
            owned_citations_json="[]",
            third_party_citations_json='["https://anker.example"]',
        )
    )
    db.add(
        GeoSampleResult(
            tenant_id=tenant_id,
            run_id=tavily.id,
            prompt_id=prompt.id,
            evidence_id="ev_new_tavily",
            engine="tavily",
            web_grounded="true",
            prompt_text_hash="a" * 64,
            answer_text_hash="d" * 64,
            mentioned=False,
            citations_json="[]",
            owned_citations_json="[]",
            third_party_citations_json="[]",
        )
    )
    db.commit()

    headers = auth_header(client)
    summary = client.get("/api/geo/summary", headers=headers).json()
    assert summary["latest_sampled"] == 2
    assert summary["latest_mentioned"] == 1
    assert "上次抽查都没提到" in summary["compare_note"]
    assert "这次有 1 问提到了" in summary["compare_note"]
    prompts = client.get("/api/geo/prompts", headers=headers).json()
    card = next(row for row in prompts if row["id"] == prompt.id)
    assert "提到了品牌，没有给出官网" in card["sample_verdict"]
    assert "bocha 提到" in card["sample_verdict"]
    assert "tavily 未提到" in card["sample_verdict"]
    assert card["mention_rate"] == "50.0%"
    assert "100W USB-C" in summary["latest_mention_split"] or "bocha 提到" in summary["latest_mention_split"]


def test_geo_grounded_batch_requires_a_live_source(client: TestClient, demo_user, monkeypatch) -> None:
    from app import geo_providers

    headers = auth_header(client)
    client.post(
        "/api/geo/prompts",
        headers=headers,
        json={"prompt_text": "smart lock for renters", "locale": "en-US"},
    )
    monkeypatch.setattr(geo_providers.settings, "bocha_api_key", "")
    monkeypatch.setattr(geo_providers.settings, "dashscope_api_key", "")
    monkeypatch.setattr(geo_providers.settings, "tavily_api_key", "")
    res = client.post("/api/geo/sample-runs/auto-grounded", headers=headers, json={"limit": 1, "trials": 1})
    assert res.status_code == 400, res.text
    assert "DeepSeek" in res.json()["detail"]


def _add_sample_run(db, tenant_id: str, prompt_id: str, *, evidence_id: str, mentioned: bool, started_at):
    from app.models import GeoSampleResult, GeoSampleRun

    run = GeoSampleRun(
        tenant_id=tenant_id,
        config_hash=evidence_id,
        status="done",
        started_at=started_at,
    )
    db.add(run)
    db.flush()
    db.add(
        GeoSampleResult(
            tenant_id=tenant_id,
            run_id=run.id,
            prompt_id=prompt_id,
            evidence_id=evidence_id,
            engine="bocha",
            web_grounded="true",
            prompt_text_hash="a" * 64,
            answer_text_hash="b" * 64,
            answer_excerpt="Third-party tips only.",
            mentioned=mentioned,
            citations_json="[]",
            owned_citations_json="[]",
            third_party_citations_json='["https://other.example/lock"]',
        )
    )
    return run


def test_geo_summary_compare_note_and_ticket_retest(client: TestClient, demo_user, db) -> None:
    from datetime import datetime, timedelta, timezone

    from app.geo_loop import write_ticket_retest
    from app.models import GeoPrompt, GeoTicket, SitePage, SourcePlatform

    tenant_id = demo_user.tenant_id
    db.add(SitePage(tenant_id=tenant_id, path="/products/smart-lock", locale="en-US", title="Smart Lock", crawl_status="ok"))
    db.add(
        SourcePlatform(
            tenant_id=tenant_id,
            platform_key="linkedin_company",
            name="LinkedIn",
            has_official_api=True,
            status="active",
        )
    )
    prompt = GeoPrompt(tenant_id=tenant_id, prompt_text="How do renters install a smart lock?", locale="en-US")
    db.add(prompt)
    db.flush()
    older = datetime.now(timezone.utc) - timedelta(days=2)
    newer = datetime.now(timezone.utc)
    previous = _add_sample_run(db, tenant_id, prompt.id, evidence_id="ev_loop_old", mentioned=False, started_at=older)
    latest = _add_sample_run(db, tenant_id, prompt.id, evidence_id="ev_loop_new", mentioned=False, started_at=newer)
    ticket = GeoTicket(
        tenant_id=tenant_id,
        prompt_id=prompt.id,
        title="买家问「How do renters install a smart lock?」时没提到我们",
        diagnosis="absent",
        status="open",
        acceptance_criteria="页已上线或帖已发出后，同一问再抽查一次。",
    )
    db.add(ticket)
    db.commit()

    headers = auth_header(client)
    summary = client.get("/api/geo/summary", headers=headers).json()
    assert "仍没提到" in summary["compare_note"]
    assert "不写成已经稳定推荐" in summary["compare_note"]
    assert summary["previous_sampled"] == 1
    assert summary["previous_mentioned"] == 0
    assert summary["latest_mentioned"] == 0

    write_ticket_retest(db, tenant_id, latest, previous)
    db.commit()
    db.refresh(ticket)
    assert "上次没有提到，这次仍没有提到" in ticket.retest_result
    assert "仍没有提到" in ticket.retest_result

    drafted = client.post("/api/geo/tickets/draft-from-evidence", headers=headers).json()
    created = drafted["tickets"]
    if created:
        ticket_out = created[0]
    else:
        ticket_out = client.get("/api/geo/tickets", headers=headers).json()[0]
    assert "对应页" in ticket_out["rationale"]
    assert "Smart Lock" in ticket_out["rationale"] or "LinkedIn" in ticket_out["rationale"] or "渠道" in ticket_out["rationale"]
    assert "不要求这次必须提到" in (ticket_out["acceptance_criteria"] or "") or "再抽查一次" in (ticket_out["acceptance_criteria"] or "")

    board = client.get("/api/execution/items", headers=headers).json()
    geo_item = next(item for item in board["items"] if item["source_module"] == "geo")
    assert "再抽查" in geo_item["acceptance_criteria"] or "再抽查" in geo_item["retest_method"]
    assert "再" in geo_item["retest_method"]
    assert geo_item["href"].startswith("/onsite/") or geo_item["href"] in {"/offsite", "/geo"}


def test_short_prompt_keeps_full_charger_question() -> None:
    from app.geo_loop import short_prompt

    question = "Which brand makes the best 100W USB-C charger for laptops?"
    assert short_prompt(question) == question
    assert "…" not in short_prompt(question)


def test_same_question_title_stays_full_and_follows_latest_sample(client: TestClient, demo_user, db) -> None:
    from datetime import datetime, timedelta, timezone

    from app.models import GeoPrompt, GeoSampleResult, GeoSampleRun, GeoTicket, SitePage, Tenant

    question = "Which brand makes the best 100W USB-C charger for laptops?"
    tenant_id = demo_user.tenant_id
    tenant = db.get(Tenant, tenant_id)
    tenant.site_origin = "https://www.ugreen.com"
    db.add(SitePage(tenant_id=tenant_id, path="/", locale="en-US", title="Home", crawl_status="ok"))
    prompt = GeoPrompt(tenant_id=tenant_id, prompt_text=question, locale="en-US")
    db.add(prompt)
    db.flush()
    older = datetime.now(timezone.utc) - timedelta(hours=2)
    now = datetime.now(timezone.utc)
    first = GeoSampleRun(tenant_id=tenant_id, config_hash="old", status="done", started_at=older)
    db.add(first)
    db.flush()
    db.add(
        GeoSampleResult(
            tenant_id=tenant_id,
            run_id=first.id,
            prompt_id=prompt.id,
            evidence_id="ev_old_absent",
            engine="bocha",
            web_grounded="true",
            prompt_text_hash="a" * 64,
            answer_text_hash="b" * 64,
            mentioned=False,
            citations_json="[]",
            owned_citations_json="[]",
            third_party_citations_json="[]",
        )
    )
    bocha = GeoSampleRun(tenant_id=tenant_id, config_hash="batch-b", status="done", started_at=now)
    tavily = GeoSampleRun(tenant_id=tenant_id, config_hash="batch-t", status="done", started_at=now + timedelta(seconds=20))
    db.add_all([bocha, tavily])
    db.flush()
    db.add(
        GeoSampleResult(
            tenant_id=tenant_id,
            run_id=bocha.id,
            prompt_id=prompt.id,
            evidence_id="ev_new_bocha",
            engine="bocha",
            web_grounded="true",
            prompt_text_hash="a" * 64,
            answer_text_hash="c" * 64,
            mentioned=False,
            citations_json="[]",
            owned_citations_json="[]",
            third_party_citations_json='["https://anker.example"]',
        )
    )
    db.add(
        GeoSampleResult(
            tenant_id=tenant_id,
            run_id=tavily.id,
            prompt_id=prompt.id,
            evidence_id="ev_new_tavily",
            engine="tavily",
            web_grounded="true",
            prompt_text_hash="a" * 64,
            answer_text_hash="d" * 64,
            mentioned=True,
            brand_hits="ugreen",
            citations_json="[]",
            owned_citations_json="[]",
            third_party_citations_json="[]",
        )
    )
    ticket = GeoTicket(
        tenant_id=tenant_id,
        prompt_id=prompt.id,
        title="买家问「Which brand makes the best…」时没提到我们",
        diagnosis="absent",
        status="open",
        retest_result="上次提到了，这次也提到了。两次都没有给出官网。",
    )
    db.add(ticket)
    db.commit()

    headers = auth_header(client)
    listed = client.get("/api/geo/tickets", headers=headers).json()
    refreshed = next(row for row in listed if row["id"] == ticket.id)
    assert question in refreshed["title"]
    assert "…" not in refreshed["title"]
    assert "提到了品牌" in refreshed["title"]
    assert "没给出官网" in refreshed["title"]
    assert "没提到我们" not in refreshed["title"]

    summary = client.get("/api/geo/summary", headers=headers).json()
    assert summary["latest_sampled"] == 2
    assert summary["latest_mentioned"] == 1
    assert "tavily 提到" in summary["latest_mention_split"]
    assert "bocha 未提到" in summary["latest_mention_split"]

    prompts = client.get("/api/geo/prompts", headers=headers).json()
    card = next(row for row in prompts if row["id"] == prompt.id)
    assert card["mention_rate"] == "50.0%"
    assert "提到了品牌，没有给出官网" in card["sample_verdict"]

    brief = client.get("/api/dashboard/customer-brief", headers=headers).json()
    this_week = next(section for section in brief["sections"] if section["key"] == "this_week")
    assert any(question in item and "提到了品牌" in item and "没提到我们" not in item for item in this_week["items"])
    assert "其中 1 条提到品牌" in brief["headline"]
    assert "tavily 提到" in brief["markdown"] or "tavily 提到" in brief["headline"]

    board = client.get("/api/execution/items", headers=headers).json()
    geo_item = next(item for item in board["items"] if item["id"] == ticket.id)
    assert question in geo_item["title"]
    assert "提到了品牌" in geo_item["title"]
