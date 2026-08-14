"""Read-only fetch of already-registered customer pages.

Not a site-wide crawler. No GSC. Observation snapshot only — never writes
proposed_change / AI drafts. Headless is not used; empty shells are flagged.
"""

from __future__ import annotations

import json
import re
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Iterable
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

from app.models import SitePage

USER_AGENT = "G-Snipers-Overseas/0.1 (+onsite-fetch; read-only)"
FETCH_TIMEOUT = 15.0
MAX_REDIRECTS = 5
MAX_WORKERS = 3
MAX_BODY = 1_500_000
SHELL_TEXT_LIMIT = 80
# Tests may assign a MockTransport. Production stays None.
TEST_TRANSPORT: httpx.BaseTransport | None = None

CRAWL_OK = "ok"
CRAWL_ROBOTS = "robots_disallow"
CRAWL_TIMEOUT = "timeout"
CRAWL_SSL = "ssl_error"
CRAWL_4XX = "http_4xx"
CRAWL_5XX = "http_5xx"
CRAWL_HOST = "host_rejected"
CRAWL_JS = "needs_js"
CRAWL_ERROR = "error"
CRAWL_UNTESTED = "untested"

USABLE_STATUSES = {CRAWL_OK, CRAWL_JS, CRAWL_4XX, CRAWL_5XX}


class OriginError(ValueError):
    pass


def normalize_origin(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        raise OriginError("请先填写站点 origin，例如 https://www.snipers.com.cn")
    parsed = urlparse(text if "://" in text else f"https://{text}")
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise OriginError("站点 origin 必须是 http(s) 地址，例如 https://www.snipers.com.cn")
    host = parsed.hostname.lower()
    netloc = f"{host}:{parsed.port}" if parsed.port else host
    return f"{parsed.scheme}://{netloc}"


def origin_host(origin: str) -> str:
    host = (urlparse(origin).hostname or "").lower()
    if not host:
        raise OriginError("站点 origin 缺少主机名")
    return host


def allowed_hosts_from_origin(origin: str) -> set[str]:
    return {origin_host(origin)}


def host_allowed(url: str, allowed_hosts: set[str]) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return bool(host) and host in allowed_hosts


def build_fetch_url(origin: str, path: str) -> str:
    raw = (path or "").strip() or "/"
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    if not raw.startswith("/"):
        raw = "/" + raw
    return urljoin(origin.rstrip("/") + "/", raw.lstrip("/"))


def registered_targets(origin: str, pages: list[SitePage]) -> list[tuple[str, SitePage | None]]:
    """Site root plus already-registered paths. No link discovery."""
    seen: set[str] = set()
    out: list[tuple[str, SitePage | None]] = []
    root = build_fetch_url(origin, "/")
    seen.add(urlparse(root)._replace(fragment="").geturl())
    root_page = next((p for p in pages if (p.path or "").strip() in {"/", ""}), None)
    out.append((root, root_page))
    for page in pages:
        url = build_fetch_url(origin, page.path)
        key = urlparse(url)._replace(fragment="").geturl()
        if key in seen:
            if root_page is None and page.path.strip() in {"/", ""}:
                out[0] = (root, page)
            continue
        seen.add(key)
        out.append((url, page))
    return out


@dataclass
class PageSnapshot:
    crawl_status: str
    requested_url: str
    final_url: str = ""
    http_status: int | None = None
    title: str = ""
    meta_description: str = ""
    h1: str = ""
    canonical: str = ""
    hreflang: str = ""
    json_ld_types: str = ""
    viewport: str = ""
    html_lang: str = ""
    internal_links: str = ""
    structured_data: str = ""
    needs_js: bool = False
    error: str = ""
    extracted: bool = False
    redirects: list[str] = field(default_factory=list)

    @property
    def usable(self) -> bool:
        return self.extracted and self.crawl_status in USABLE_STATUSES


class _SeoParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.html_lang = ""
        self.title_parts: list[str] = []
        self.h1_parts: list[str] = []
        self.body_parts: list[str] = []
        self.meta_description = ""
        self.canonical = ""
        self.viewport = ""
        self.hreflangs: list[str] = []
        self.links: list[str] = []
        self.json_ld_blocks: list[str] = []
        self._in_title = False
        self._in_h1 = False
        self._in_ld = False
        self._skip = False
        self._ld_parts: list[str] = []
        self._h1_done = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        ad = {k.lower(): (v or "") for k, v in attrs}
        rel = ad.get("rel", "").lower()
        if tag == "html":
            self.html_lang = ad.get("lang", "")
        elif tag == "title":
            self._in_title = True
        elif tag == "h1" and not self._h1_done:
            self._in_h1 = True
        elif tag == "meta":
            name = (ad.get("name") or ad.get("property") or "").lower()
            if name in {"description", "og:description"} and not self.meta_description:
                self.meta_description = ad.get("content", "").strip()
            if name == "viewport":
                self.viewport = ad.get("content", "").strip()
        elif tag == "link":
            rels = set(rel.split())
            if "canonical" in rels:
                self.canonical = ad.get("href", "").strip()
            if "alternate" in rels and ad.get("hreflang"):
                self.hreflangs.append(f"{ad['hreflang']}={ad.get('href', '').strip()}")
        elif tag == "a" and ad.get("href"):
            self.links.append(ad["href"].strip())
        elif tag == "script":
            script_type = ad.get("type", "").lower()
            if "ld+json" in script_type:
                self._in_ld = True
                self._ld_parts = []
            else:
                self._skip = True
        elif tag in {"style", "noscript"}:
            self._skip = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        elif tag == "h1":
            if self._in_h1:
                self._h1_done = True
            self._in_h1 = False
        elif tag == "script":
            if self._in_ld:
                block = "".join(self._ld_parts).strip()
                if block:
                    self.json_ld_blocks.append(block)
                self._in_ld = False
                self._ld_parts = []
            self._skip = False
        elif tag in {"style", "noscript"}:
            self._skip = False

    def handle_data(self, data: str) -> None:
        if self._in_ld:
            self._ld_parts.append(data)
            return
        if self._skip:
            return
        if self._in_title:
            self.title_parts.append(data)
        if self._in_h1:
            self.h1_parts.append(data)
        text = data.strip()
        if text:
            self.body_parts.append(text)


def _json_ld_types(blocks: list[str]) -> list[str]:
    types: list[str] = []

    def walk(node: object) -> None:
        if isinstance(node, list):
            for item in node:
                walk(item)
            return
        if not isinstance(node, dict):
            return
        raw = node.get("@type")
        if isinstance(raw, str) and raw.strip():
            types.append(raw.strip())
        elif isinstance(raw, list):
            types.extend(str(x).strip() for x in raw if str(x).strip())
        for key in ("@graph", "mainEntity", "hasPart"):
            if key in node:
                walk(node[key])

    for block in blocks:
        try:
            walk(json.loads(block))
        except json.JSONDecodeError:
            continue
    seen: set[str] = set()
    out: list[str] = []
    for item in types:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def looks_like_empty_shell(html: str, visible_text: str) -> bool:
    text = re.sub(r"\s+", " ", visible_text or "").strip()
    low = html.lower()
    spa = any(token in low for token in ('id="app"', "id='app'", 'id="root"', 'id="__next"', "id='__next'"))
    return len(text) < SHELL_TEXT_LIMIT and (spa or len(html) < 800)


def extract_html(html: str, *, base_url: str, allowed_hosts: set[str]) -> dict[str, str | bool]:
    parser = _SeoParser()
    try:
        parser.feed(html or "")
        parser.close()
    except Exception:
        pass
    title = re.sub(r"\s+", " ", "".join(parser.title_parts)).strip()
    h1 = re.sub(r"\s+", " ", "".join(parser.h1_parts)).strip()
    visible = " ".join(parser.body_parts)
    types = _json_ld_types(parser.json_ld_blocks)
    paths: list[str] = []
    seen: set[str] = set()
    for href in parser.links:
        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)
        if parsed.scheme not in {"http", "https"}:
            continue
        if not host_allowed(absolute, allowed_hosts):
            continue
        path = parsed.path or "/"
        if path not in seen:
            seen.add(path)
            paths.append(path)
    return {
        "title": title,
        "meta_description": parser.meta_description.strip(),
        "h1": h1,
        "canonical": urljoin(base_url, parser.canonical) if parser.canonical else "",
        "hreflang": "; ".join(parser.hreflangs),
        "json_ld_types": ", ".join(types),
        "structured_data": ", ".join(types),
        "viewport": parser.viewport,
        "html_lang": parser.html_lang.strip(),
        "internal_links": "\n".join(paths),
        "needs_js": looks_like_empty_shell(html or "", visible),
    }


def load_robots(origin: str, client: httpx.Client) -> RobotFileParser:
    parser = RobotFileParser()
    robots_url = urljoin(origin.rstrip("/") + "/", "robots.txt")
    try:
        response = client.get(robots_url)
        if response.status_code >= 400:
            parser.parse(["User-agent: *", "Allow: /"])
        else:
            parser.parse((response.text or "").splitlines())
    except httpx.HTTPError:
        parser.parse(["User-agent: *", "Allow: /"])
    return parser


def _status_for_http(code: int, needs_js: bool) -> str:
    if 400 <= code <= 499:
        return CRAWL_4XX
    if code >= 500:
        return CRAWL_5XX
    if needs_js:
        return CRAWL_JS
    return CRAWL_OK


def fetch_url(
    url: str,
    allowed_hosts: set[str],
    *,
    client: httpx.Client,
    robots: RobotFileParser | None = None,
) -> PageSnapshot:
    snap = PageSnapshot(crawl_status=CRAWL_ERROR, requested_url=url)
    if not host_allowed(url, allowed_hosts):
        snap.crawl_status = CRAWL_HOST
        snap.error = f"主机名不在站点 origin 允许列表：{urlparse(url).hostname}"
        return snap
    if robots is not None and not robots.can_fetch(USER_AGENT, url):
        snap.crawl_status = CRAWL_ROBOTS
        snap.error = "robots.txt 禁止抓取该路径"
        return snap

    current = url
    response: httpx.Response | None = None
    try:
        for _ in range(MAX_REDIRECTS + 1):
            if not host_allowed(current, allowed_hosts):
                snap.crawl_status = CRAWL_HOST
                snap.final_url = current
                snap.error = f"跳转目标主机名不在允许列表：{urlparse(current).hostname}"
                return snap
            if robots is not None and not robots.can_fetch(USER_AGENT, current):
                snap.crawl_status = CRAWL_ROBOTS
                snap.final_url = current
                snap.error = "robots.txt 禁止抓取该路径"
                return snap
            response = client.get(current)
            if response.is_redirect:
                location = response.headers.get("location")
                if not location:
                    snap.crawl_status = CRAWL_ERROR
                    snap.http_status = response.status_code
                    snap.final_url = str(response.url)
                    snap.error = "重定向缺少 Location"
                    return snap
                nxt = urljoin(current, location)
                snap.redirects.append(nxt)
                current = nxt
                continue
            break
        else:
            snap.crawl_status = CRAWL_ERROR
            snap.error = "重定向次数过多"
            snap.final_url = current
            return snap
    except httpx.TimeoutException as exc:
        snap.crawl_status = CRAWL_TIMEOUT
        snap.error = f"超时（{FETCH_TIMEOUT:.0f}s）：{exc}"
        return snap
    except httpx.ConnectError as exc:
        message = str(exc)
        if "CERTIFICATE" in message.upper() or "SSL" in message.upper():
            snap.crawl_status = CRAWL_SSL
            snap.error = f"SSL 失败：{exc}"
        else:
            snap.crawl_status = CRAWL_ERROR
            snap.error = f"连接失败：{exc}"
        return snap
    except ssl.SSLError as exc:
        snap.crawl_status = CRAWL_SSL
        snap.error = f"SSL 失败：{exc}"
        return snap
    except httpx.HTTPError as exc:
        snap.crawl_status = CRAWL_ERROR
        snap.error = f"抓取失败：{exc}"
        return snap

    assert response is not None
    snap.http_status = response.status_code
    snap.final_url = str(response.url)
    if not host_allowed(snap.final_url, allowed_hosts):
        snap.crawl_status = CRAWL_HOST
        snap.error = f"终态主机名不在允许列表：{urlparse(snap.final_url).hostname}"
        return snap

    body = response.text or ""
    if len(body) > MAX_BODY:
        body = body[:MAX_BODY]
    extracted = extract_html(body, base_url=snap.final_url or url, allowed_hosts=allowed_hosts)
    snap.title = str(extracted["title"])
    snap.meta_description = str(extracted["meta_description"])
    snap.h1 = str(extracted["h1"])
    snap.canonical = str(extracted["canonical"])
    snap.hreflang = str(extracted["hreflang"])
    snap.json_ld_types = str(extracted["json_ld_types"])
    snap.structured_data = str(extracted["structured_data"])
    snap.viewport = str(extracted["viewport"])
    snap.html_lang = str(extracted["html_lang"])
    snap.internal_links = str(extracted["internal_links"])
    snap.needs_js = bool(extracted["needs_js"])
    snap.extracted = True
    snap.crawl_status = _status_for_http(response.status_code, snap.needs_js)
    if snap.crawl_status in {CRAWL_4XX, CRAWL_5XX}:
        snap.error = f"HTTP {response.status_code}"
    elif snap.needs_js:
        snap.error = "正文几乎是空壳，需要 JS 渲染。本期不启动无头浏览器。"
    return snap


def make_client(timeout: float = FETCH_TIMEOUT, transport: httpx.BaseTransport | None = None) -> httpx.Client:
    return httpx.Client(
        timeout=httpx.Timeout(timeout),
        follow_redirects=False,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8"},
        transport=transport or TEST_TRANSPORT,
        max_redirects=MAX_REDIRECTS,
    )


def fetch_many(
    targets: Iterable[tuple[str, SitePage | None]],
    origin: str,
    *,
    transport: httpx.BaseTransport | None = None,
    max_workers: int = MAX_WORKERS,
) -> list[tuple[str, SitePage | None, PageSnapshot]]:
    allowed = allowed_hosts_from_origin(origin)
    items = list(targets)
    with make_client(transport=transport) as client:
        robots = load_robots(origin, client)
        results: list[tuple[str, SitePage | None, PageSnapshot] | None] = [None] * len(items)

        def _one(index: int, url: str, page: SitePage | None) -> tuple[int, PageSnapshot]:
            return index, fetch_url(url, allowed, client=client, robots=robots)

        workers = max(1, min(max_workers, len(items) or 1))
        if workers == 1 or len(items) <= 1:
            for i, (url, page) in enumerate(items):
                results[i] = (url, page, fetch_url(url, allowed, client=client, robots=robots))
        else:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futs = [pool.submit(_one, i, url, page) for i, (url, page) in enumerate(items)]
                for fut in as_completed(futs):
                    index, snap = fut.result()
                    url, page = items[index]
                    results[index] = (url, page, snap)
    return [row for row in results if row is not None]


def apply_observation(page: SitePage, snap: PageSnapshot) -> None:
    """Overwrite observation fields only. Never touch issue drafts."""
    page.crawl_status = snap.crawl_status
    page.fetched_at = datetime.now(timezone.utc)
    page.final_url = snap.final_url or ""
    page.http_status = snap.http_status
    page.needs_js = snap.needs_js
    page.crawl_error = snap.error or ""
    if not snap.extracted:
        return
    if snap.title:
        page.title = snap.title[:300]
        page.meta_title = snap.title
    page.meta_description = snap.meta_description
    page.headings = f"H1 {snap.h1}" if snap.h1 else ""
    page.canonical = snap.canonical
    page.hreflang = snap.hreflang
    page.html_lang = snap.html_lang[:32]
    page.viewport = snap.viewport[:300]
    page.json_ld_types = snap.json_ld_types[:400]
    page.structured_data = snap.structured_data
    page.internal_links = snap.internal_links
    # index_status stays untested — HTML is not GSC.
