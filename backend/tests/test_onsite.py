import json

from fastapi.testclient import TestClient

from tests.conftest import auth_header


def test_project_targets_seed_customer_context_and_geo_prompts(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    payload = {
        "site_origin": "https://example.com",
        "markets": [
            {
                "name": "United States",
                "region": "North America",
                "country_code": "US",
                "primary_locale": "en-US",
                "status": "priority",
                "opportunity_score": 82,
            }
        ],
        "keywords": [
            {"theme": "industrial pump supplier", "locale": "en-US", "country_code": "US", "intent": "commercial", "intensity": 5},
            {"theme": "industrial pump supplier", "locale": "en-US", "country_code": "US", "intent": "commercial", "intensity": 5},
        ],
        "competitors": [
            {"name": "Pump Rival", "website": "https://rival.example", "country_code": "US"},
            {"name": "Pump Rival Copy", "website": "https://rival.example", "country_code": "US"},
        ],
    }

    saved = client.put("/api/project-targets", headers=headers, json=payload)
    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert body["site_origin"] == "https://example.com"
    assert body["readiness"] == "ready"
    assert body["target_market_count"] == 1
    assert body["keyword_count"] == 1
    assert body["competitor_count"] == 1
    assert body["markets"][0]["demand_signals"][0]["theme"] == "industrial pump supplier"

    again = client.put("/api/project-targets", headers=headers, json=payload)
    assert again.status_code == 200, again.text
    assert again.json()["keyword_count"] == 1
    assert again.json()["competitor_count"] == 1

    seeded = client.post("/api/geo/prompt-panel/seed", headers=headers)
    assert seeded.status_code == 200, seeded.text
    assert seeded.json()["created"] >= 1
    prompts = client.get("/api/geo/prompts", headers=headers).json()
    assert any("industrial pump supplier" in row["prompt_text"] for row in prompts)


def test_project_targets_replace_old_target_setup_when_site_changes(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    first = client.put(
        "/api/project-targets",
        headers=headers,
        json={
            "site_origin": "https://www.snipers.com.cn",
            "markets": [
                {
                    "name": "China",
                    "region": "China",
                    "country_code": "CN",
                    "primary_locale": "zh-CN",
                    "status": "priority",
                    "opportunity_score": 70,
                }
            ],
            "keywords": [
                {"theme": "seo", "locale": "en-US", "country_code": "CN"},
                {"theme": "geo", "locale": "en-US", "country_code": "CN"},
            ],
            "competitors": [{"name": "Old Rival", "website": "https://old.example", "country_code": "CN"}],
        },
    )
    assert first.status_code == 200, first.text
    seeded = client.post("/api/geo/prompt-panel/seed", headers=headers)
    assert seeded.status_code == 200, seeded.text

    second = client.put(
        "/api/project-targets",
        headers=headers,
        json={
            "site_origin": "https://www.sulzer.com/",
            "confirm_site_switch": True,
            "markets": [
                {
                    "name": "United States",
                    "region": "North America",
                    "country_code": "US",
                    "primary_locale": "en-US",
                    "status": "priority",
                    "opportunity_score": 80,
                }
            ],
            "keywords": [{"theme": "化工 泵", "locale": "en-US", "country_code": "US"}],
            "competitors": [],
        },
    )
    assert second.status_code == 200, second.text
    body = second.json()
    assert body["site_origin"] == "https://www.sulzer.com"
    assert body["keyword_count"] == 2
    assert [market["name"] for market in body["markets"]] == ["United States"]
    themes = [signal["theme"] for signal in body["markets"][0]["demand_signals"]]
    assert set(themes) == {"化工", "泵"}
    assert "seo" not in themes
    assert body["competitor_count"] == 0


def test_site_context_archive_restore_switches_seo_geo_and_execution(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    first = client.put(
        "/api/project-targets",
        headers=headers,
        json={
            "site_origin": "https://www.snipers.com.cn",
            "markets": [
                {
                    "name": "United States",
                    "region": "North America",
                    "country_code": "US",
                    "primary_locale": "en-US",
                    "status": "priority",
                    "opportunity_score": 80,
                }
            ],
            "keywords": [{"theme": "industrial pump", "locale": "en-US", "country_code": "US"}],
            "competitors": [{"name": "Old Rival", "website": "https://old.example", "country_code": "US"}],
        },
    )
    assert first.status_code == 200, first.text
    page = client.post(
        "/api/onsite/pages",
        headers=headers,
        json={"path": "/en-us/products", "locale": "en-US", "title": "Products"},
    )
    assert page.status_code == 201, page.text
    issue = client.post(
        f"/api/onsite/pages/{page.json()['id']}/issues",
        headers=headers,
        json={"category": "tdk", "title": "Title 缺少核心词", "priority": "P1"},
    )
    assert issue.status_code == 201, issue.text
    seeded = client.post("/api/geo/prompt-panel/seed", headers=headers)
    assert seeded.status_code == 200, seeded.text
    before_exec = client.get("/api/execution/items", headers=headers).json()
    assert before_exec["total_open"] >= 1

    blocked = client.put(
        "/api/project-targets",
        headers=headers,
        json={"site_origin": "https://example-switch-test.com", "markets": [], "keywords": [], "competitors": []},
    )
    assert blocked.status_code == 400
    assert "确认" in blocked.json()["detail"]

    switched = client.put(
        "/api/project-targets",
        headers=headers,
        json={
            "site_origin": "https://example-switch-test.com",
            "markets": [],
            "keywords": [],
            "competitors": [],
            "confirm_site_switch": True,
        },
    )
    assert switched.status_code == 200, switched.text
    assert switched.json()["site_origin"] == "https://example-switch-test.com"
    assert client.get("/api/onsite/board", headers=headers).json()["pages"] == 0
    assert client.get("/api/geo/summary", headers=headers).json()["prompts"] == 0
    assert client.get("/api/execution/items", headers=headers).json()["total_open"] == 0

    reused = client.put(
        "/api/project-targets",
        headers=headers,
        json={
            "site_origin": "https://www.snipers.com.cn",
            "markets": [],
            "keywords": [],
            "competitors": [],
            "confirm_site_switch": True,
        },
    )
    assert reused.status_code == 200, reused.text
    assert reused.json()["site_origin"] == "https://www.snipers.com.cn"
    assert "已恢复" in reused.json()["note"]
    assert client.get("/api/onsite/board", headers=headers).json()["pages"] == 1
    assert client.get("/api/geo/summary", headers=headers).json()["prompts"] >= 1
    assert client.get("/api/execution/items", headers=headers).json()["total_open"] >= 1

    switched_again = client.put(
        "/api/project-targets",
        headers=headers,
        json={
            "site_origin": "https://example-switch-test.com",
            "markets": [],
            "keywords": [],
            "competitors": [],
            "confirm_site_switch": True,
        },
    )
    assert switched_again.status_code == 200, switched_again.text
    archives = client.get("/api/site-context/archives", headers=headers)
    assert archives.status_code == 200, archives.text
    archive = next(row for row in archives.json() if row["site_origin"] == "https://www.snipers.com.cn")
    restored = client.post(f"/api/site-context/archives/{archive['id']}/restore", headers=headers)
    assert restored.status_code == 200, restored.text
    assert restored.json()["site_origin"] == "https://www.snipers.com.cn"
    assert client.get("/api/onsite/board", headers=headers).json()["pages"] == 1
    assert client.get("/api/geo/summary", headers=headers).json()["prompts"] >= 1
    assert client.get("/api/execution/items", headers=headers).json()["total_open"] >= 1


def test_project_targets_reject_invalid_origin(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    res = client.put(
        "/api/project-targets",
        headers=headers,
        json={"site_origin": "notaurl", "markets": [], "keywords": [], "competitors": []},
    )
    assert res.status_code == 400
    assert "无效" in res.json()["detail"]


def test_onsite_page_and_risk_gates(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    page = client.post(
        "/api/onsite/pages",
        headers=headers,
        json={"path": "/en-us/demo", "locale": "en-US", "title": "Demo page"},
    )
    assert page.status_code == 201
    assert page.json()["index_status"] == "untested"
    assert page.json()["crawl_status"] == "untested"
    page_id = page.json()["id"]

    listed = client.get("/api/onsite/pages", headers=headers)
    assert any(p["id"] == page_id for p in listed.json())

    low = client.post(
        f"/api/onsite/pages/{page_id}/issues",
        headers=headers,
        json={"category": "tdk", "title": "描述过短", "proposed_change": "加长"},
    )
    assert low.status_code == 201
    assert low.json()["risk"] == "low"
    assert low.json()["metric_status"] == "untested"
    assert low.json()["review_required"] is False
    assert low.json()["owner_hint"] == "内容运营 / 客户经理"
    assert "标题" in low.json()["recommended_action"]

    high = client.post(
        f"/api/onsite/pages/{page_id}/issues",
        headers=headers,
        json={"category": "schema", "title": "补 FAQ", "proposed_change": "JSON-LD"},
    )
    assert high.json()["risk"] == "high"
    assert high.json()["review_required"] is True
    assert "JSON-LD" in high.json()["recommended_action"]
    assert high.json()["retest_method"]

    denied_auto = client.post(f"/api/onsite/issues/{high.json()['id']}/apply-draft", headers=headers)
    assert denied_auto.status_code == 400

    drafted = client.post(f"/api/onsite/issues/{low.json()['id']}/apply-draft", headers=headers)
    assert drafted.json()["status"] == "draft_applied"
    workspace = client.get(f"/api/onsite/pages/{page_id}", headers=headers).json()
    assert workspace["meta_description"] == ""
    assert drafted.json()["proposed_change"] == "加长"

    denied_live = client.post(
        f"/api/onsite/issues/{high.json()['id']}/confirm-apply",
        headers=headers,
        json={"confirmed": False},
    )
    assert denied_live.status_code == 400

    confirmed = client.post(
        f"/api/onsite/issues/{high.json()['id']}/confirm-apply",
        headers=headers,
        json={"confirmed": True},
    )
    assert confirmed.json()["status"] in {"confirmed", "verified"}
    after_high = client.get(f"/api/onsite/pages/{page_id}", headers=headers).json()
    assert after_high["structured_data"] == ""
    assert confirmed.json()["proposed_change"] == "JSON-LD"

    reopened = client.post(f"/api/onsite/issues/{high.json()['id']}/reopen", headers=headers)
    assert reopened.status_code == 200
    assert reopened.json()["status"] == "drafted"

    marked = client.post(
        f"/api/onsite/issues/{high.json()['id']}/mark-executed",
        headers=headers,
        json={"confirmed": True, "note": "已在测试站处理"},
    )
    assert marked.status_code == 200
    assert marked.json()["status"] == "confirmed"
    assert "人工执行记录" in marked.json()["evidence"]

    ignored = client.post(
        f"/api/onsite/issues/{low.json()['id']}/wont-fix",
        headers=headers,
        json={"note": "本轮不处理"},
    )
    assert ignored.status_code == 200
    assert ignored.json()["status"] == "wont_fix"
    assert "忽略原因" in ignored.json()["evidence"]


def test_analyze_does_not_apply_and_board_groups_severity(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    page = client.post(
        "/api/onsite/pages",
        headers=headers,
        json={"path": "/en-us/empty", "locale": "en-US", "title": "Empty"},
    ).json()
    page_id = page["id"]
    before = client.get(f"/api/onsite/pages/{page_id}", headers=headers).json()
    assert before["meta_description"] == ""
    assert before["structured_data"] == ""
    assert before["index_status"] == "untested"

    analyzed = client.post(f"/api/onsite/pages/{page_id}/analyze", headers=headers)
    assert analyzed.status_code == 200
    assert analyzed.json()["created"] >= 3
    assert "未改" in analyzed.json()["note"] or analyzed.json()["pages"] == 1

    after_analyze = client.get(f"/api/onsite/pages/{page_id}", headers=headers).json()
    assert after_analyze["meta_description"] == ""
    assert after_analyze["structured_data"] == ""
    assert after_analyze["index_status"] == "untested"
    assert any(i["category"] == "canonical" for i in after_analyze["issues"])
    assert all(i["status"] == "open" for i in after_analyze["issues"])
    assert all(i["proposed_change"] == "" for i in after_analyze["issues"])

    empty_apply = next(i for i in after_analyze["issues"] if i["severity"] == "low")
    denied = client.post(f"/api/onsite/issues/{empty_apply['id']}/apply-draft", headers=headers)
    assert denied.status_code == 400

    drafted = client.patch(
        f"/api/onsite/issues/{empty_apply['id']}/draft",
        headers=headers,
        json={"proposed_change": "工作区描述草稿"},
    )
    assert drafted.json()["status"] == "drafted"
    still = client.get(f"/api/onsite/pages/{page_id}", headers=headers).json()
    assert still["meta_description"] == ""

    applied = client.post(f"/api/onsite/issues/{empty_apply['id']}/apply-draft", headers=headers)
    assert applied.json()["status"] == "draft_applied"
    assert applied.json()["proposed_change"] == "工作区描述草稿"
    assert client.get(f"/api/onsite/pages/{page_id}", headers=headers).json()["meta_description"] == ""

    board = client.get("/api/onsite/board", headers=headers).json()
    assert "critical" in board["groups"]
    assert "status_counts" in board
    assert "workflow_counts" in board
    assert board["counts"]["critical"] + board["counts"]["high"] + board["counts"]["low"] >= 1
    assert all(i["metric_status"] == "untested" for i in board["groups"]["critical"])
    first_issue = (board["groups"]["critical"] + board["groups"]["high"] + board["groups"]["low"])[0]
    assert first_issue["impact"]
    assert first_issue["recommended_action"]
    assert first_issue["retest_method"]

    briefs = client.get("/api/onsite/briefs", headers=headers).json()
    assert isinstance(briefs, list)
    if briefs:
        assert briefs[0]["serp_features"] == "未测"


def test_crawl_or_seed_from_internal_links(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    client.post(
        "/api/onsite/pages",
        headers=headers,
        json={
            "path": "/en-us/home",
            "locale": "en-US",
            "title": "Home",
            "internal_links": "/en-us/new-from-seed\nhttps://example.com/out",
        },
    )
    result = client.post("/api/onsite/crawl-or-seed", headers=headers)
    assert result.status_code == 200
    assert result.json()["seeded"] >= 1
    pages = client.get("/api/onsite/pages", headers=headers).json()
    assert any(p["path"] == "/en-us/new-from-seed" for p in pages)
    seeded = next(p for p in pages if p["path"] == "/en-us/new-from-seed")
    assert seeded["index_status"] == "untested"


def test_seo_report_exports_customer_report_and_execution_table(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    page = client.post(
        "/api/onsite/pages",
        headers=headers,
        json={
            "path": "/products/pump",
            "locale": "en-US",
            "title": "Industrial Pump",
            "crawl_status": "ok",
            "http_status": 200,
            "word_count": 80,
        },
    ).json()
    client.post(
        f"/api/onsite/pages/{page['id']}/issues",
        headers=headers,
        json={
            "category": "b2b",
            "title": "产品页缺少询盘入口",
            "detail": "未发现明显询盘入口。",
            "severity": "high",
            "risk": "high",
        },
    )

    report = client.get("/api/onsite/report", headers=headers)
    assert report.status_code == 200
    markdown = report.json()["markdown"]
    assert "一句话结论" in markdown
    assert "诊断目标" in markdown
    assert "主要风险" in markdown
    assert "需要客户配合" in markdown
    assert "测速状态" in markdown
    assert "产品页缺少询盘入口" in markdown
    assert "page_type" not in markdown

    table = client.get("/api/onsite/report-table", headers=headers)
    assert table.status_code == 200
    data = table.json()
    assert data["filename"].startswith("网站改法执行表-")
    csv_text = data["csv"]
    assert "优先级,严重程度,问题类型,目标国家/地区,关联关键词,页面" in csv_text
    assert "为什么影响获客" in csv_text
    assert "建议改法" in csv_text
    assert "复查方式" in csv_text
    assert "测速状态" in csv_text
    assert "产品页缺少询盘入口" in csv_text
    assert "page_type" not in csv_text
    assert "crawl_status" not in csv_text


def test_seo_performance_csv_feeds_summary_report_and_table(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    page = client.post(
        "/api/onsite/pages",
        headers=headers,
        json={"path": "/products/pump", "locale": "en-US", "title": "Industrial Pump"},
    ).json()
    client.post(
        f"/api/onsite/pages/{page['id']}/issues",
        headers=headers,
        json={"category": "tdk", "title": "标题缺少核心产品词", "severity": "high"},
    )

    csv_text = "\n".join(
        [
            "Query,Page,Country,Device,Clicks,Impressions,CTR,Position",
            "industrial pump,https://example.com/products/pump,United States,desktop,12,300,4%,8.5",
            "pump supplier,https://example.com/products/pump,Germany,mobile,3,120,2.5%,14",
        ]
    )
    imported = client.post(
        "/api/onsite/performance/import-csv",
        headers=headers,
        json={"source": "gsc_csv", "filename": "gsc.csv", "csv_text": csv_text},
    )
    assert imported.status_code == 201
    assert imported.json()["rows_imported"] == 2

    summary = client.get("/api/onsite/performance", headers=headers)
    assert summary.status_code == 200
    body = summary.json()
    assert body["gsc_status"] == "已导入"
    assert body["total_impressions"] == 420
    assert body["total_clicks"] == 15
    assert body["by_country"][0]["key"] == "United States"
    assert any(item["key"] == "industrial pump" for item in body["by_query"])

    report = client.get("/api/onsite/report", headers=headers).json()["markdown"]
    assert "搜索表现" in report
    assert "总展示：420" in report
    assert "industrial pump" in report

    table = client.get("/api/onsite/report-table", headers=headers).json()["csv"]
    assert "曝光,点击,CTR,平均排名" in table
    assert "420" in table or "300" in table


def test_gsc_oauth_connect_and_sync_feeds_performance(client: TestClient, demo_user, monkeypatch) -> None:
    import httpx

    import app.routers.onsite as onsite_router
    from app.config import settings

    headers = auth_header(client)
    status = client.get("/api/onsite/gsc/status", headers=headers)
    assert status.status_code == 200
    assert status.json()["configured"] is False

    monkeypatch.setattr(settings, "gsc_oauth_client_id", "client-id")
    monkeypatch.setattr(settings, "gsc_oauth_client_secret", "client-secret")
    monkeypatch.setattr(settings, "gsc_oauth_redirect_uri", "http://localhost:3000/onsite")
    monkeypatch.setattr(
        onsite_router,
        "_exchange_gsc_code",
        lambda db, user, code: {
            "access_token": "access-1",
            "refresh_token": "refresh-1",
            "expires_in": 3600,
            "scope": "https://www.googleapis.com/auth/webmasters.readonly",
        },
    )

    connected = client.post(
        "/api/onsite/gsc/connect",
        headers=headers,
        json={"code": "oauth-code", "site_url": "https://example.com/"},
    )
    assert connected.status_code == 200, connected.text
    assert connected.json()["connected"] is True
    assert connected.json()["site_url"] == "https://example.com/"

    monkeypatch.setattr(onsite_router, "_refresh_gsc_token", lambda db, conn: "access-2")

    class FakeGscClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def post(self, url, headers=None, json=None, data=None):
            assert "searchAnalytics/query" in url
            assert headers["Authorization"] == "Bearer access-2"
            assert json["dimensions"] == ["date", "query", "page", "country", "device"]
            return httpx.Response(
                200,
                json={
                    "rows": [
                        {
                            "keys": ["2026-08-01", "industrial pump", "https://example.com/products/pump", "usa", "DESKTOP"],
                            "clicks": 4,
                            "impressions": 100,
                            "ctr": 0.04,
                            "position": 8.2,
                        }
                    ]
                },
            )

    monkeypatch.setattr(onsite_router.httpx, "Client", FakeGscClient)
    synced = client.post("/api/onsite/gsc/sync", headers=headers, json={"days": 28, "row_limit": 100})
    assert synced.status_code == 200, synced.text
    assert synced.json()["rows_imported"] == 1

    performance = client.get("/api/onsite/performance", headers=headers)
    assert performance.status_code == 200
    body = performance.json()
    assert body["gsc_status"] == "已导入"
    assert body["total_impressions"] == 100
    assert body["total_clicks"] == 4
    assert body["by_query"][0]["key"] == "industrial pump"

    runs = client.get("/api/onsite/data-sync/status", headers=headers)
    assert runs.status_code == 200
    assert runs.json()["runs"][0]["source"] == "gsc"
    assert runs.json()["runs"][0]["rows_imported"] == 1


def test_integration_settings_can_be_saved_from_console(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    initial = client.get("/api/onsite/integrations", headers=headers)
    assert initial.status_code == 200
    assert initial.json()["gsc_configured"] is False

    saved = client.patch(
        "/api/onsite/integrations",
        headers=headers,
        json={
            "gsc_oauth_client_id": "client-id-from-ui",
            "gsc_oauth_client_secret": "client-secret-from-ui",
            "gsc_oauth_redirect_uri": "http://localhost:3000/onsite",
            "brightdata_dataset_api_key": "brightdata-key-from-ui",
            "brightdata_serp_dataset_id": "gd_mfz5x93lmsjjjylob",
        },
    )
    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert body["gsc_configured"] is True
    assert body["brightdata_serp_configured"] is True
    assert "client-secret-from-ui" not in json.dumps(body)
    assert any(field["source"] == "database" for field in body["fields"])

    gsc = client.get("/api/onsite/gsc/status", headers=headers).json()
    assert gsc["configured"] is True

    replaced = client.patch(
        "/api/onsite/integrations",
        headers=headers,
        json={"gsc_oauth_client_id": "client-id-replaced"},
    )
    assert replaced.status_code == 200, replaced.text
    replaced_body = replaced.json()
    assert replaced_body["gsc_configured"] is True
    client_id_field = next(field for field in replaced_body["fields"] if field["key"] == "gsc_oauth_client_id")
    assert client_id_field["masked_value"].startswith("clie")
    assert "client-id-replaced" not in json.dumps(replaced_body)

    cleared = client.patch(
        "/api/onsite/integrations",
        headers=headers,
        json={"clear_keys": ["gsc_oauth_client_id", "gsc_oauth_client_secret", "gsc_oauth_redirect_uri"]},
    )
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["gsc_configured"] is False


def test_data_sync_run_due_executes_gsc_once(client: TestClient, demo_user, monkeypatch) -> None:
    import httpx

    import app.routers.onsite as onsite_router
    from app.config import settings

    headers = auth_header(client)
    monkeypatch.setattr(settings, "gsc_oauth_client_id", "client-id")
    monkeypatch.setattr(settings, "gsc_oauth_client_secret", "client-secret")
    monkeypatch.setattr(settings, "gsc_oauth_redirect_uri", "http://localhost:3000/onsite")
    monkeypatch.setattr(settings, "gsc_auto_sync_days", 28)
    monkeypatch.setattr(settings, "gsc_auto_sync_min_interval_hours", 24)
    monkeypatch.setattr(
        onsite_router,
        "_exchange_gsc_code",
        lambda db, user, code: {
            "access_token": "access-1",
            "refresh_token": "refresh-1",
            "expires_in": 3600,
            "scope": "https://www.googleapis.com/auth/webmasters.readonly",
        },
    )
    connected = client.post(
        "/api/onsite/gsc/connect",
        headers=headers,
        json={"code": "oauth-code", "site_url": "https://example.com/"},
    )
    assert connected.status_code == 200, connected.text
    monkeypatch.setattr(onsite_router, "_refresh_gsc_token", lambda db, conn: "access-2")

    calls = {"count": 0}

    class FakeGscClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def post(self, url, headers=None, json=None, data=None):
            calls["count"] += 1
            assert "searchAnalytics/query" in url
            assert json["rowLimit"] == 25000
            return httpx.Response(
                200,
                json={
                    "rows": [
                        {
                            "keys": ["2026-08-01", "industrial pump exporter", "https://example.com/products/pump", "usa", "MOBILE"],
                            "clicks": 6,
                            "impressions": 180,
                            "ctr": 0.0333,
                            "position": 11.4,
                        }
                    ]
                },
            )

    monkeypatch.setattr(onsite_router.httpx, "Client", FakeGscClient)
    due = client.post("/api/onsite/data-sync/run-due", headers=headers, json={"force": False, "sources": ["gsc"]})
    assert due.status_code == 200, due.text
    assert due.json()["status"] == "ok"
    assert due.json()["ran"] == 1
    assert due.json()["runs"][0]["mode"] == "scheduled"
    assert due.json()["runs"][0]["rows_imported"] == 1
    assert calls["count"] == 1

    performance = client.get("/api/onsite/performance", headers=headers).json()
    assert performance["total_impressions"] == 180
    assert performance["by_query"][0]["key"] == "industrial pump exporter"

    skipped = client.post("/api/onsite/data-sync/run-due", headers=headers, json={"force": False, "sources": ["gsc"]})
    assert skipped.status_code == 200, skipped.text
    assert skipped.json()["status"] == "skipped"
    assert skipped.json()["skipped"] == 1
    assert calls["count"] == 1


def test_bing_status_and_indexnow_submission(client: TestClient, demo_user, monkeypatch) -> None:
    import httpx

    import app.routers.onsite as onsite_router
    from app.config import settings

    headers = auth_header(client)
    client.patch("/api/onsite/settings", headers=headers, json={"site_origin": "https://example.com"})
    bing = client.get("/api/onsite/bing/status", headers=headers)
    assert bing.status_code == 200
    assert bing.json()["configured"] is False

    monkeypatch.setattr(settings, "bing_webmaster_api_key", "bing-key")
    monkeypatch.setattr(settings, "indexnow_key", "index-key")
    monkeypatch.setattr(settings, "indexnow_key_location", "https://example.com/index-key.txt")

    bing_ready = client.get("/api/onsite/bing/status", headers=headers)
    assert bing_ready.json()["configured"] is True
    index_status = client.get("/api/onsite/indexnow/status", headers=headers)
    assert index_status.json()["configured"] is True
    assert index_status.json()["key_location"] == "https://example.com/index-key.txt"

    class FakeIndexNowClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def post(self, url, json=None):
            assert url == onsite_router.INDEXNOW_ENDPOINT
            assert json["host"] == "example.com"
            assert json["key"] == "index-key"
            assert json["urlList"] == ["https://example.com/products/pump"]
            return httpx.Response(200, text="ok")

    monkeypatch.setattr(onsite_router.httpx, "Client", FakeIndexNowClient)
    submitted = client.post(
        "/api/onsite/indexnow/submit",
        headers=headers,
        json={"paths": ["/products/pump"]},
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "submitted"
    assert submitted.json()["submitted"] == 1

    runs = client.get("/api/onsite/data-sync/status", headers=headers).json()["runs"]
    assert runs[0]["source"] == "indexnow"
    assert runs[0]["submitted"] == 1


def test_brightdata_serp_run_classifies_owned_competitor_and_third_party(client: TestClient, demo_user, monkeypatch) -> None:
    import app.routers.onsite as onsite_router
    from app.config import settings

    headers = auth_header(client)
    client.patch("/api/onsite/settings", headers=headers, json={"site_origin": "https://example.com"})
    market = client.post(
        "/api/markets",
        headers=headers,
        json={"name": "United States", "region": "North America", "country_code": "US", "primary_locale": "en-US", "status": "priority"},
    ).json()
    client.post(
        f"/api/markets/{market['id']}/demand-signals",
        headers=headers,
        json={"theme": "industrial pump supplier", "locale": "en-US", "intent": "commercial", "intensity": 5},
    )
    client.post(
        f"/api/markets/{market['id']}/competitors",
        headers=headers,
        json={"name": "Competitor", "website": "https://competitor.com"},
    )

    monkeypatch.setattr(settings, "brightdata_dataset_api_key", "dataset-key")
    monkeypatch.setattr(settings, "brightdata_serp_dataset_id", "gd_mfz5x93lmsjjjylob")

    def fake_serp(db, tenant_id: str, keyword: str, *, country: str, locale: str, device: str, limit: int):
        assert keyword == "industrial pump supplier"
        assert country == "US"
        return [
            {"position": 1, "title": "Directory", "url": "https://industry-directory.example/list", "snippet": "Directory", "result_type": "organic"},
            {"position": 2, "title": "Competitor", "url": "https://competitor.com/pumps", "snippet": "Competitor", "result_type": "organic"},
            {"position": 3, "title": "Our page", "url": "https://example.com/pumps", "snippet": "Our page", "result_type": "organic"},
        ]

    monkeypatch.setattr(onsite_router, "_fetch_brightdata_serp", fake_serp)
    ran = client.post(
        "/api/onsite/serp/run",
        headers=headers,
        json={"keywords": [], "country": "US", "locale": "en-US", "device": "desktop", "limit": 10},
    )
    assert ran.status_code == 200, ran.text
    body = ran.json()
    assert body["configured"] is True
    assert body["ran"] == 1
    assert body["runs"][0]["own_best_position"] == 3
    assert body["runs"][0]["competitor_best_position"] == 2
    assert body["runs"][0]["third_party_count"] == 1

    summary = client.get("/api/onsite/performance", headers=headers).json()["serp"]
    assert summary["own_visible_runs"] == 1
    assert summary["competitor_visible_runs"] == 1
    assert summary["top_third_party_domains"][0]["domain"] == "industry-directory.example"


def test_brightdata_dataset_serp_request_shape(monkeypatch) -> None:
    import httpx

    import app.routers.onsite as onsite_router
    from app.config import settings

    monkeypatch.setattr(settings, "brightdata_dataset_api_key", "dataset-key")
    monkeypatch.setattr(settings, "brightdata_serp_dataset_id", "gd_mfz5x93lmsjjjylob")
    monkeypatch.setattr(settings, "brightdata_serp_endpoint", "https://api.brightdata.com/datasets/v3/scrape")
    real_client = httpx.Client

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.params["dataset_id"] == "gd_mfz5x93lmsjjjylob"
        assert request.url.params["notify"] == "false"
        assert request.headers["Authorization"] == "Bearer dataset-key"
        body = json.loads(request.content.decode())
        assert body["input"][0]["url"] == "https://www.google.com/"
        assert body["input"][0]["keyword"] == "industrial pump supplier"
        assert body["input"][0]["language"] == "en"
        assert body["input"][0]["brd_mobile"] == ""
        return httpx.Response(
            200,
            json=[
                {
                    "organic_results": [
                        {"position": 1, "title": "Result", "url": "https://example.com/pumps", "description": "Result text"}
                    ]
                }
            ],
        )

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            self.client = real_client(transport=httpx.MockTransport(handler), headers=kwargs.get("headers"))

        def __enter__(self):
            return self.client

        def __exit__(self, exc_type, exc, tb) -> None:
            self.client.close()

    monkeypatch.setattr(onsite_router.httpx, "Client", FakeClient)
    rows = onsite_router._fetch_brightdata_serp(
        None,
        "tenant",
        "industrial pump supplier",
        country="US",
        locale="en-US",
        device="desktop",
        limit=10,
    )
    assert rows[0]["position"] == 1
    assert rows[0]["url"] == "https://example.com/pumps"


def test_pagespeed_uses_ce17_overseas_check(client: TestClient, demo_user, monkeypatch) -> None:
    import app.routers.onsite.diagnosis as diagnosis

    headers = auth_header(client)
    client.patch("/api/onsite/settings", headers=headers, json={"site_origin": "https://example.com"})
    saved = client.patch(
        "/api/onsite/integrations",
        headers=headers,
        json={"ce17_user": "am@example.com", "ce17_api_pwd": "ce17-api-pwd"},
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["ce17_configured"] is True

    monkeypatch.setattr(
        diagnosis,
        "run_overseas_http_check",
        lambda **kwargs: {
            "performance_score": None,
            "seo_score": None,
            "accessibility_score": None,
            "best_practices_score": None,
            "lcp_ms": 820,
            "inp_ms": 1400,
            "cls": None,
            "detail": "17CE 海外打开 https://example.com/：通 2/2。",
        },
    )
    res = client.post("/api/onsite/performance/pagespeed", headers=headers, json={"urls": [], "strategies": ["mobile"], "limit": 2})
    assert res.status_code == 200, res.text
    body = res.json()
    assert len(body) == 1
    assert body[0]["status"] == "ok"
    assert body[0]["strategy"] == "overseas"
    assert body[0]["lcp_ms"] == 820
    assert body[0]["performance_score"] is None
    assert "17CE 海外打开" in body[0]["detail"]


def test_pagespeed_without_ce17_key_records_error(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    client.patch("/api/onsite/settings", headers=headers, json={"site_origin": "https://example.com"})
    res = client.post("/api/onsite/performance/pagespeed", headers=headers, json={"urls": [], "limit": 1})
    assert res.status_code == 200, res.text
    assert res.json()[0]["status"] == "error"
    assert "17CE" in res.json()[0]["detail"]
