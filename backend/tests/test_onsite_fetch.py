import httpx
from fastapi.testclient import TestClient

from app.geo_helpers import apply_proposed_change
from app.models import OnsiteIssue, SitePage
from app.onsite_fetch import (
    CRAWL_4XX,
    CRAWL_HOST,
    CRAWL_JS,
    CRAWL_OK,
    CRAWL_ROBOTS,
    PageSnapshot,
    apply_observation,
    extract_html,
    fetch_url,
    load_robots,
    make_client,
    normalize_origin,
)
from app.config import settings
from tests.conftest import auth_header

ORIGIN = "https://www.snipers.com.cn"

SAMPLE_HTML = """<!doctype html>
<html lang="en">
<head>
  <title>Smart Lock Guide</title>
  <meta name="description" content="Install a smart lock without replacing the whole door frame.">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="canonical" href="https://www.snipers.com.cn/en">
  <link rel="alternate" hreflang="zh-CN" href="https://www.snipers.com.cn/">
  <script type="application/ld+json">{"@context":"https://schema.org","@type":"WebPage"}</script>
</head>
<body>
  <h1>Smart lock for renters</h1>
  <p>Enough visible copy so this is not treated as an empty JavaScript shell page.</p>
  <a href="/guide">Guide</a>
</body>
</html>
"""


def test_extract_tdk_h1_canonical_jsonld() -> None:
    data = extract_html(SAMPLE_HTML, base_url=f"{ORIGIN}/en", allowed_hosts={"www.snipers.com.cn"})
    assert data["title"] == "Smart Lock Guide"
    assert "smart lock" in str(data["meta_description"]).lower()
    assert data["h1"] == "Smart lock for renters"
    assert data["canonical"] == f"{ORIGIN}/en"
    assert "WebPage" in str(data["json_ld_types"])
    assert "zh-CN=" in str(data["hreflang"])
    assert data["html_lang"] == "en"
    assert data["viewport"].startswith("width=device-width")
    assert data["needs_js"] is False
    assert "/guide" in str(data["internal_links"])


def test_fetch_follows_redirect_to_final_url() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        if path == "/old":
            return httpx.Response(301, headers={"location": "/en"})
        if path == "/en":
            return httpx.Response(200, text=SAMPLE_HTML, headers={"content-type": "text/html; charset=utf-8"})
        return httpx.Response(404, text="missing")

    transport = httpx.MockTransport(handler)
    with make_client(transport=transport) as client:
        snap = fetch_url(f"{ORIGIN}/old", {"www.snipers.com.cn"}, client=client)
    assert snap.crawl_status == CRAWL_OK
    assert snap.http_status == 200
    assert snap.final_url.endswith("/en")
    assert snap.title == "Smart Lock Guide"
    assert snap.h1 == "Smart lock for renters"
    assert "WebPage" in snap.json_ld_types
    assert snap.content_type == "text/html"
    assert snap.redirect_count == 1
    assert snap.html_bytes > 0
    assert len(snap.body_hash) == 64
    assert snap.ttfb_ms is not None


def test_fetch_rejects_off_host_redirect() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        return httpx.Response(302, headers={"location": "https://evil.example/phish"})

    transport = httpx.MockTransport(handler)
    with make_client(transport=transport) as client:
        snap = fetch_url(f"{ORIGIN}/out", {"www.snipers.com.cn"}, client=client)
    assert snap.crawl_status == CRAWL_HOST
    assert snap.extracted is False
    assert snap.title == ""


def test_fetch_rejects_foreign_host() -> None:
    with make_client() as client:
        snap = fetch_url("https://evil.example/", {"www.snipers.com.cn"}, client=client)
    assert snap.crawl_status == CRAWL_HOST


def test_observation_does_not_overwrite_draft() -> None:
    page = SitePage(
        tenant_id="t",
        path="/en",
        locale="en-US",
        title="old",
        meta_title="old title",
        meta_description="old desc",
        canonical="https://old.example/x",
    )
    issue = OnsiteIssue(
        tenant_id="t",
        page_id="p",
        category="canonical",
        title="Canonical 未登记",
        proposed_change="很长的改稿说明：" + ("英文化 TDK 与 canonical 方案。" * 40),
    )
    snap = PageSnapshot(
        crawl_status=CRAWL_OK,
        requested_url=f"{ORIGIN}/en",
        final_url=f"{ORIGIN}/en",
        http_status=200,
        title="Smart Lock Guide",
        meta_description="Install a smart lock without replacing the whole door frame.",
        h1="Smart lock for renters",
        canonical=f"{ORIGIN}/en",
        json_ld_types="WebPage",
        structured_data="WebPage",
        extracted=True,
    )
    before = issue.proposed_change
    apply_observation(page, snap)
    apply_proposed_change(page, issue)
    assert issue.proposed_change == before
    assert page.canonical == f"{ORIGIN}/en"
    assert page.meta_title == "Smart Lock Guide"
    assert "很长的改稿说明" not in (page.canonical or "")
    assert "很长的改稿说明" not in (page.meta_description or "")


def test_robots_and_4xx_and_empty_shell() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /secret\n")
        if path == "/missing":
            return httpx.Response(404, text="<html><head><title>Not found</title></head><body>gone</body></html>")
        if path == "/app":
            return httpx.Response(200, text='<html><body><div id="app"></div></body></html>')
        return httpx.Response(200, text=SAMPLE_HTML)

    transport = httpx.MockTransport(handler)
    with make_client(transport=transport) as client:
        robots = load_robots(ORIGIN, client)
        blocked = fetch_url(f"{ORIGIN}/secret", {"www.snipers.com.cn"}, client=client, robots=robots)
        missing = fetch_url(f"{ORIGIN}/missing", {"www.snipers.com.cn"}, client=client, robots=robots)
        shell = fetch_url(f"{ORIGIN}/app", {"www.snipers.com.cn"}, client=client, robots=robots)
    assert blocked.crawl_status == CRAWL_ROBOTS
    assert missing.crawl_status == CRAWL_4XX
    assert missing.title == "Not found"
    assert shell.crawl_status == CRAWL_JS
    assert shell.needs_js is True


def test_js_shell_can_be_rechecked_by_configured_browser(monkeypatch) -> None:
    shell_html = '<html><body><div id="app"></div></body></html>'
    rendered_html = """<!doctype html>
<html lang="en"><head>
  <title>Rendered Product Page</title>
  <meta name="description" content="Rendered description for B2B buyers.">
  <link rel="canonical" href="https://www.snipers.com.cn/rendered">
</head><body>
  <h1>Rendered Product Page</h1>
  <p>Industrial buyers can read the rendered product overview, application scenarios, specifications,
  certifications, export delivery details, service process, warranty policy, installation notes, FAQ,
  after-sales support, distributor cooperation, and procurement guidance after JavaScript has loaded.</p>
  <a href="/contact">Contact</a>
</body></html>"""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=shell_html, headers={"content-type": "text/html"})

    def fake_render(url: str) -> tuple[str, str]:
        assert url == f"{ORIGIN}/app"
        return rendered_html, f"{ORIGIN}/rendered"

    monkeypatch.setattr(settings, "brightdata_browser_ws", "wss://example.invalid/browser")
    monkeypatch.setattr(settings, "onsite_render_js_enabled", True)
    import app.onsite_fetch as onsite_fetch

    monkeypatch.setattr(onsite_fetch, "_render_html_with_browser", fake_render)
    with make_client(transport=httpx.MockTransport(handler)) as client:
        snap = fetch_url(f"{ORIGIN}/app", {"www.snipers.com.cn"}, client=client)

    assert snap.crawl_status == CRAWL_OK
    assert snap.needs_js is False
    assert snap.final_url == f"{ORIGIN}/rendered"
    assert snap.title == "Rendered Product Page"
    assert snap.h1 == "Rendered Product Page"
    assert "/contact" in snap.internal_links
    assert snap.error == "已通过浏览器渲染复查"


def test_confirm_apply_long_draft_does_not_pollute(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    page = client.post(
        "/api/onsite/pages",
        headers=headers,
        json={
            "path": "/en",
            "locale": "en-US",
            "title": "Live",
            "canonical": "https://www.snipers.com.cn/en",
            "meta_title": "English title",
        },
    ).json()
    long_draft = "确认上线说明：" + ("把中文 TDK 改成英文并核对 canonical。" * 30)
    assert len(long_draft) > 400
    issue = client.post(
        f"/api/onsite/pages/{page['id']}/issues",
        headers=headers,
        json={"category": "schema", "title": "补 FAQ", "proposed_change": long_draft},
    ).json()
    confirmed = client.post(
        f"/api/onsite/issues/{issue['id']}/confirm-apply",
        headers=headers,
        json={"confirmed": True},
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["proposed_change"] == long_draft
    after = client.get(f"/api/onsite/pages/{page['id']}", headers=headers).json()
    assert after["canonical"] == "https://www.snipers.com.cn/en"
    assert after["meta_title"] == "English title"
    assert long_draft not in (after["canonical"] or "")
    assert long_draft not in (after["title"] or "")


def test_fetch_registered_updates_observation_and_verifies(client: TestClient, demo_user, monkeypatch) -> None:
    headers = auth_header(client)
    missing = client.post("/api/onsite/fetch-registered", headers=headers)
    assert missing.status_code == 400

    saved = client.patch(
        "/api/onsite/settings",
        headers=headers,
        json={"site_origin": ORIGIN},
    )
    assert saved.status_code == 200
    assert saved.json()["site_origin"] == ORIGIN

    page = client.post(
        "/api/onsite/pages",
        headers=headers,
        json={
            "path": "/en",
            "locale": "en-US",
            "title": "门锁安装",
            "meta_title": "智能门锁安装指南",
            "meta_description": "中文描述还没改",
        },
    ).json()
    analyzed = client.post(f"/api/onsite/pages/{page['id']}/analyze", headers=headers).json()
    assert analyzed["created"] >= 1
    before = client.get(f"/api/onsite/pages/{page['id']}", headers=headers).json()
    zh = next(i for i in before["issues"] if i["title"] == "TDK 含中文")
    draft = "改成英文 Title / Description，上线后回抓。"
    client.patch(
        f"/api/onsite/issues/{zh['id']}/draft",
        headers=headers,
        json={"proposed_change": draft},
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        if request.url.path in {"/", "/en"}:
            return httpx.Response(200, text=SAMPLE_HTML, headers={"content-type": "text/html; charset=utf-8"})
        return httpx.Response(404, text="no")

    import app.onsite_fetch as onsite_fetch

    monkeypatch.setattr(onsite_fetch, "TEST_TRANSPORT", httpx.MockTransport(handler))

    fetched = client.post("/api/onsite/fetch-registered", headers=headers)
    assert fetched.status_code == 200, fetched.text
    body = fetched.json()
    assert body["ai_status"] == "skipped"
    assert body["fetched"] >= 1
    assert all(r["crawl_status"] != "ok" or r["url"].startswith(ORIGIN) for r in body["results"])

    after = client.get(f"/api/onsite/pages/{page['id']}", headers=headers).json()
    assert after["meta_title"] == "Smart Lock Guide"
    assert after["canonical"] == f"{ORIGIN}/en"
    assert after["json_ld_types"] == "WebPage"
    assert after["content_type"] == "text/html"
    assert after["html_bytes"] > 0
    assert len(after["body_hash"]) == 64
    assert after["ttfb_ms"] is not None
    assert after["crawl_status"] in {"ok", "needs_js"}
    assert after["fetched_at"]
    assert after["index_status"] == "untested"
    zh_after = next(i for i in after["issues"] if i["id"] == zh["id"])
    assert zh_after["status"] == "verified"
    assert zh_after["proposed_change"] == draft
    assert draft not in (after["meta_title"] or "")
    assert draft not in (after["canonical"] or "")


def test_analyze_reads_current_observation_not_old_detail(client: TestClient, demo_user) -> None:
    headers = auth_header(client)
    page = client.post(
        "/api/onsite/pages",
        headers=headers,
        json={
            "path": "/",
            "locale": "en-US",
            "title": "Home",
            "meta_title": "中文首页标题",
            "meta_description": "还是中文描述需要改掉才行啊",
        },
    ).json()
    client.post(f"/api/onsite/pages/{page['id']}/analyze", headers=headers)
    detail = client.get(f"/api/onsite/pages/{page['id']}", headers=headers).json()
    zh = next(i for i in detail["issues"] if i["title"] == "TDK 含中文")
    assert "中文" in zh["detail"]

    client.patch(
        f"/api/onsite/pages/{page['id']}",
        headers=headers,
        json={"meta_title": "English home", "meta_description": "A long enough English description for the homepage."},
    )
    client.post(f"/api/onsite/pages/{page['id']}/analyze", headers=headers)
    again = client.get(f"/api/onsite/pages/{page['id']}", headers=headers).json()
    zh_again = next(i for i in again["issues"] if i["id"] == zh["id"])
    assert zh_again["status"] == "verified"
    assert "已满足" in zh_again["detail"]


def test_normalize_origin_does_not_guess_www() -> None:
    assert normalize_origin("https://snipers.com.cn") == "https://snipers.com.cn"
    assert normalize_origin("https://www.snipers.com.cn/") == "https://www.snipers.com.cn"


def test_fetch_many_does_not_share_client_across_urls(monkeypatch) -> None:
    """Would fail if fetch_many handed one Client to a thread pool (httpx is not thread-safe)."""
    import threading
    import time

    import app.onsite_fetch as onsite_fetch
    from app.onsite_fetch import fetch_many

    page_clients: list[int] = []
    in_flight: dict[int, int] = {}
    max_in_flight: dict[int, int] = {}
    lock = threading.Lock()
    orig_fetch = onsite_fetch.fetch_url
    orig_request = httpx.Client.request

    def tracked_fetch(url, allowed, *, client, robots=None):
        page_clients.append(id(client))
        return orig_fetch(url, allowed, client=client, robots=robots)

    def tracked_request(self, method, url, *args, **kwargs):
        cid = id(self)
        with lock:
            in_flight[cid] = in_flight.get(cid, 0) + 1
            max_in_flight[cid] = max(max_in_flight.get(cid, 0), in_flight[cid])
        try:
            time.sleep(0.02)
            return orig_request(self, method, url, *args, **kwargs)
        finally:
            with lock:
                in_flight[cid] -= 1

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        return httpx.Response(200, text=SAMPLE_HTML)

    monkeypatch.setattr(onsite_fetch, "fetch_url", tracked_fetch)
    monkeypatch.setattr(httpx.Client, "request", tracked_request)

    targets = [(f"{ORIGIN}/a", None), (f"{ORIGIN}/b", None), (f"{ORIGIN}/c", None)]
    rows = fetch_many(targets, ORIGIN, transport=httpx.MockTransport(handler))
    assert len(rows) == 3
    assert all(snap.crawl_status == CRAWL_OK for _url, _page, snap in rows)
    assert len(page_clients) == 3
    assert len(set(page_clients)) == 3
    assert all(count == 1 for count in max_in_flight.values())


def test_fetch_registered_does_not_call_llm(client: TestClient, demo_user, monkeypatch) -> None:
    headers = auth_header(client)
    client.patch("/api/onsite/settings", headers=headers, json={"site_origin": ORIGIN})
    client.post(
        "/api/onsite/pages",
        headers=headers,
        json={"path": "/en", "locale": "en-US", "title": "Live"},
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        return httpx.Response(200, text=SAMPLE_HTML)

    import app.onsite_fetch as onsite_fetch
    import app.routers.onsite as onsite_router

    monkeypatch.setattr(onsite_fetch, "TEST_TRANSPORT", httpx.MockTransport(handler))

    def boom(*_args, **_kwargs):
        raise AssertionError("抓取接口不得调用 LLM")

    monkeypatch.setattr(onsite_router, "assist_onsite_issue", boom)
    monkeypatch.setattr(onsite_router, "_ai_after_analyze", boom)

    fetched = client.post("/api/onsite/fetch-registered", headers=headers)
    assert fetched.status_code == 200, fetched.text
    body = fetched.json()
    assert body["ai_status"] == "skipped"
    assert "不跑 LLM" in body["note"]
    assert body["fetched"] >= 1


def test_crawl_site_discovers_sitemap_links_and_report(client: TestClient, demo_user, monkeypatch) -> None:
    headers = auth_header(client)
    client.patch("/api/onsite/settings", headers=headers, json={"site_origin": ORIGIN})

    product_html = """<!doctype html>
<html lang="en"><head>
<title>Product Page</title>
<meta name="description" content="A useful product page for overseas buyers with enough detail.">
<meta name="robots" content="index,follow">
<link rel="canonical" href="https://www.snipers.com.cn/product">
</head><body>
<h1>Product Page</h1>
<p>Smart lock product specification, application, installation, support, buyer FAQ, warranty and export service content.</p>
<img src="/a.jpg"><a href="/contact">Contact</a><a href="https://example.com/out">Out</a>
</body></html>"""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text=f"User-agent: *\nAllow: /\nSitemap: {ORIGIN}/sitemap.xml\n")
        if request.url.path == "/sitemap.xml":
            return httpx.Response(
                200,
                text=f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>{ORIGIN}/product</loc></url>
</urlset>""",
            )
        if request.url.path in {"/", "/product", "/contact"}:
            return httpx.Response(200, headers={"X-Robots-Tag": "index"}, text=product_html)
        return httpx.Response(404, text="no")

    import app.onsite_fetch as onsite_fetch

    monkeypatch.setattr(onsite_fetch, "TEST_TRANSPORT", httpx.MockTransport(handler))
    crawled = client.post("/api/onsite/crawl-site", headers=headers, json={"max_urls": 5, "max_depth": 1})
    assert crawled.status_code == 200, crawled.text
    body = crawled.json()
    assert body["discovered"] >= 2
    assert body["fetched"] >= 2

    pages = client.get("/api/onsite/pages", headers=headers).json()
    product = next(p for p in pages if p["path"] == "/product")
    assert product["discovery_source"] == "sitemap"
    assert product["is_in_sitemap"] == "yes"
    assert product["image_count"] == 1
    assert product["images_missing_alt"] == 1
    assert product["external_link_count"] == 1
    assert product["meta_robots"] == "index,follow"
    assert product["x_robots_tag"] == "index"

    report = client.get("/api/onsite/report", headers=headers)
    assert report.status_code == 200
    assert "SEO" in report.json()["markdown"]
    assert "/product" in report.json()["markdown"]
