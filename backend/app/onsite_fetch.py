"""Read-only fetch of already-registered customer pages.

Not a site-wide crawler. No GSC. Observation snapshot only — never writes
proposed_change / AI drafts. Headless is not used; empty shells are flagged.
"""

from __future__ import annotations

import json
import re
import ssl
import time
import hashlib
import xml.etree.ElementTree as ET
from collections import deque
from contextlib import ExitStack
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Iterable
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

try:
    from protego import Protego
except ImportError:  # pragma: no cover - optional production enhancement
    Protego = None  # type: ignore[assignment]

try:
    import extruct
except ImportError:  # pragma: no cover - optional production enhancement
    extruct = None  # type: ignore[assignment]

try:
    import trafilatura
except ImportError:  # pragma: no cover - optional production enhancement
    trafilatura = None  # type: ignore[assignment]

from app.models import SitePage
from app.config import settings

USER_AGENT = "G-Snipers-Overseas/0.1 (+onsite-fetch; read-only)"
FETCH_TIMEOUT = 15.0
MAX_REDIRECTS = 5
MAX_BODY = 1_500_000
SHELL_TEXT_LIMIT = 80
DEFAULT_SITEMAP_PATHS = ("/sitemap.xml", "/sitemap_index.xml")
RENDER_WORD_GAIN_MIN = 40
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
    content_type: str = ""
    ttfb_ms: int | None = None
    redirect_count: int = 0
    html_bytes: int = 0
    body_hash: str = ""
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
    meta_robots: str = ""
    x_robots_tag: str = ""
    word_count: int = 0
    image_count: int = 0
    images_missing_alt: int = 0
    external_link_count: int = 0
    needs_js: bool = False
    fetch_mode: str = "http"
    render_status: str = "not_needed"
    render_final_url: str = ""
    render_word_count: int = 0
    error: str = ""
    extracted: bool = False
    redirects: list[str] = field(default_factory=list)

    @property
    def usable(self) -> bool:
        return self.extracted and self.crawl_status in USABLE_STATUSES


@dataclass
class CrawlTarget:
    url: str
    page: SitePage | None = None
    depth: int = 0
    source: str = "manual"
    in_sitemap: bool = False


@dataclass
class RobotsPolicy:
    parser: object

    def can_fetch(self, user_agent: str, url: str) -> bool:
        if Protego is not None and isinstance(self.parser, Protego):  # type: ignore[arg-type]
            return bool(self.parser.can_fetch(url, user_agent))
        return bool(self.parser.can_fetch(user_agent, url))


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
        self.meta_robots = ""
        self.hreflangs: list[str] = []
        self.links: list[str] = []
        self.json_ld_blocks: list[str] = []
        self.image_count = 0
        self.images_missing_alt = 0
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
            if name == "robots":
                self.meta_robots = ad.get("content", "").strip()
        elif tag == "link":
            rels = set(rel.split())
            if "canonical" in rels:
                self.canonical = ad.get("href", "").strip()
            if "alternate" in rels and ad.get("hreflang"):
                self.hreflangs.append(f"{ad['hreflang']}={ad.get('href', '').strip()}")
        elif tag == "a" and ad.get("href"):
            self.links.append(ad["href"].strip())
        elif tag == "img":
            self.image_count += 1
            if not ad.get("alt", "").strip():
                self.images_missing_alt += 1
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


def _schema_types_from_extruct(html: str, base_url: str) -> list[str]:
    if extruct is None:
        return []
    try:
        data = extruct.extract(html, base_url=base_url, syntaxes=["json-ld", "microdata", "rdfa"], uniform=True)
    except Exception:
        return []
    types: list[str] = []

    def walk(node: object) -> None:
        if isinstance(node, list):
            for item in node:
                walk(item)
            return
        if not isinstance(node, dict):
            return
        raw = node.get("@type") or node.get("type")
        if isinstance(raw, str) and raw.strip():
            types.append(raw.strip())
        elif isinstance(raw, list):
            types.extend(str(item).strip() for item in raw if str(item).strip())
        for key in ("@graph", "properties", "children", "mainEntity", "hasPart"):
            if key in node:
                walk(node[key])

    for syntax_rows in data.values():
        walk(syntax_rows)
    seen: set[str] = set()
    out: list[str] = []
    for item in types:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _main_content_text(html: str) -> str:
    if trafilatura is None:
        return ""
    try:
        return trafilatura.extract(html, include_comments=False, include_tables=False) or ""
    except Exception:
        return ""


def looks_like_empty_shell(html: str, visible_text: str) -> bool:
    text = re.sub(r"\s+", " ", visible_text or "").strip()
    low = html.lower()
    spa = any(token in low for token in ('id="app"', "id='app'", 'id="root"', 'id="__next"', "id='__next'"))
    return len(text) < SHELL_TEXT_LIMIT and (spa or len(html) < 800)


def extract_html(html: str, *, base_url: str, allowed_hosts: set[str]) -> dict[str, str | int | bool]:
    parser = _SeoParser()
    try:
        parser.feed(html or "")
        parser.close()
    except Exception:
        pass
    title = re.sub(r"\s+", " ", "".join(parser.title_parts)).strip()
    h1 = re.sub(r"\s+", " ", "".join(parser.h1_parts)).strip()
    visible = " ".join(parser.body_parts)
    main_content = _main_content_text(html or "")
    types = _schema_types_from_extruct(html or "", base_url) or _json_ld_types(parser.json_ld_blocks)
    paths: list[str] = []
    external = 0
    seen: set[str] = set()
    for href in parser.links:
        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)
        if parsed.scheme not in {"http", "https"}:
            continue
        if not host_allowed(absolute, allowed_hosts):
            external += 1
            continue
        path = parsed.path or "/"
        if path not in seen:
            seen.add(path)
            paths.append(path)
    parser_words = re.findall(r"[\w\u4e00-\u9fff]+", visible)
    main_words = re.findall(r"[\w\u4e00-\u9fff]+", main_content)
    return {
        "title": title,
        "meta_description": parser.meta_description.strip(),
        "h1": h1,
        "canonical": urljoin(base_url, parser.canonical) if parser.canonical else "",
        "hreflang": "; ".join(parser.hreflangs),
        "json_ld_types": ", ".join(types),
        "structured_data": ", ".join(types),
        "meta_robots": parser.meta_robots,
        "viewport": parser.viewport,
        "html_lang": parser.html_lang.strip(),
        "internal_links": "\n".join(paths),
        "word_count": len(main_words) if main_words else len(parser_words),
        "image_count": parser.image_count,
        "images_missing_alt": parser.images_missing_alt,
        "external_link_count": external,
        "needs_js": looks_like_empty_shell(html or "", visible),
    }


def load_robots(origin: str, client: httpx.Client) -> RobotsPolicy:
    robots_url = urljoin(origin.rstrip("/") + "/", "robots.txt")
    try:
        response = client.get(robots_url)
        if response.status_code >= 400:
            text = "User-agent: *\nAllow: /\n"
        else:
            text = response.text or ""
    except httpx.HTTPError:
        text = "User-agent: *\nAllow: /\n"
    if Protego is not None:
        return RobotsPolicy(Protego.parse(text))
    parser = RobotFileParser()
    parser.parse(text.splitlines())
    return RobotsPolicy(parser)


def _robots_sitemaps(origin: str, client: httpx.Client) -> list[str]:
    robots_url = urljoin(origin.rstrip("/") + "/", "robots.txt")
    try:
        response = client.get(robots_url)
    except httpx.HTTPError:
        return []
    if response.status_code >= 400:
        return []
    urls: list[str] = []
    for line in (response.text or "").splitlines():
        if line.lower().startswith("sitemap:"):
            raw = line.split(":", 1)[1].strip()
            if raw:
                urls.append(urljoin(origin.rstrip("/") + "/", raw))
    return urls


def _xml_text(element: ET.Element, name: str) -> str:
    for child in element:
        if child.tag.rsplit("}", 1)[-1] == name:
            return (child.text or "").strip()
    return ""


def discover_sitemap_urls(
    origin: str,
    allowed_hosts: set[str],
    *,
    client: httpx.Client,
    max_urls: int = 100,
) -> list[str]:
    """Find URLs from robots-declared and common sitemap paths."""
    sitemap_urls: list[str] = []
    seen_sitemaps: set[str] = set()
    candidates = [*_robots_sitemaps(origin, client), *(urljoin(origin.rstrip("/") + "/", p.lstrip("/")) for p in DEFAULT_SITEMAP_PATHS)]
    queue: deque[str] = deque(candidates)
    found: list[str] = []
    seen_urls: set[str] = set()
    while queue and len(found) < max_urls:
        sitemap_url = queue.popleft()
        if sitemap_url in seen_sitemaps or not host_allowed(sitemap_url, allowed_hosts):
            continue
        seen_sitemaps.add(sitemap_url)
        try:
            response = client.get(sitemap_url)
        except httpx.HTTPError:
            continue
        if response.status_code >= 400:
            continue
        text = response.text or ""
        try:
            root = ET.fromstring(text.encode("utf-8"))
        except ET.ParseError:
            continue
        root_name = root.tag.rsplit("}", 1)[-1]
        if root_name == "sitemapindex":
            for item in root:
                loc = _xml_text(item, "loc")
                if loc and host_allowed(loc, allowed_hosts):
                    queue.append(loc)
            continue
        if root_name != "urlset":
            continue
        for item in root:
            loc = _xml_text(item, "loc")
            if not loc or not host_allowed(loc, allowed_hosts):
                continue
            normalized = urlparse(loc)._replace(fragment="").geturl()
            if normalized in seen_urls:
                continue
            seen_urls.add(normalized)
            found.append(normalized)
            if len(found) >= max_urls:
                break
    return found


def _status_for_http(code: int, needs_js: bool) -> str:
    if 400 <= code <= 499:
        return CRAWL_4XX
    if code >= 500:
        return CRAWL_5XX
    if needs_js:
        return CRAWL_JS
    return CRAWL_OK


def browser_render_available() -> bool:
    return bool(settings.onsite_render_js_enabled and settings.brightdata_browser_ws.strip())


def _render_html_with_browser(url: str) -> tuple[str, str]:
    """Render one URL through a configured remote Chromium endpoint."""
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - depends on optional production package
        raise RuntimeError("playwright 未安装，无法启用浏览器渲染") from exc

    endpoint = settings.brightdata_browser_ws.strip()
    timeout_ms = max(5000, int(settings.onsite_render_timeout_ms or 30000))
    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp(endpoint, timeout=timeout_ms)
        page = browser.new_page(user_agent=USER_AGENT)
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            try:
                page.wait_for_load_state("networkidle", timeout=min(timeout_ms, 8000))
            except PlaywrightTimeoutError:
                pass
            final_url = page.url
            html = page.content()
            return html or "", final_url or url
        finally:
            page.close()
            browser.close()


def _maybe_render_js_snapshot(snap: PageSnapshot, *, allowed_hosts: set[str]) -> None:
    if not snap.needs_js or not browser_render_available():
        return
    snap.render_status = "attempted"
    target = snap.final_url or snap.requested_url
    if not host_allowed(target, allowed_hosts):
        snap.render_status = "skipped"
        return
    started = time.perf_counter()
    try:
        rendered_html, final_url = _render_html_with_browser(target)
    except Exception as exc:
        snap.render_status = "error"
        snap.error = f"{snap.error}；浏览器渲染失败：{exc}" if snap.error else f"浏览器渲染失败：{exc}"
        return
    if not rendered_html:
        snap.render_status = "error"
        snap.error = f"{snap.error}；浏览器渲染返回空内容" if snap.error else "浏览器渲染返回空内容"
        return
    if not host_allowed(final_url, allowed_hosts):
        snap.render_status = "host_rejected"
        snap.crawl_status = CRAWL_HOST
        snap.final_url = final_url
        snap.error = f"浏览器渲染终态主机名不在允许列表：{urlparse(final_url).hostname}"
        return

    rendered = extract_html(rendered_html[:MAX_BODY], base_url=final_url, allowed_hosts=allowed_hosts)
    old_word_count = snap.word_count
    rendered_needs_js = bool(rendered["needs_js"])
    rendered_word_count = int(rendered["word_count"])
    if rendered_needs_js and rendered_word_count < old_word_count + RENDER_WORD_GAIN_MIN:
        snap.render_status = "insufficient"
        snap.render_final_url = final_url
        snap.render_word_count = rendered_word_count
        snap.error = f"{snap.error}；浏览器渲染后正文仍不足" if snap.error else "浏览器渲染后正文仍不足"
        return

    raw_body = rendered_html.encode("utf-8", errors="replace")
    snap.fetch_mode = "browser"
    snap.render_status = "ok" if not rendered_needs_js else "still_needs_js"
    snap.render_final_url = final_url
    snap.render_word_count = rendered_word_count
    snap.final_url = final_url
    snap.ttfb_ms = int(round((time.perf_counter() - started) * 1000))
    snap.content_type = "text/html"
    snap.html_bytes = len(raw_body)
    snap.body_hash = hashlib.sha256(raw_body[:MAX_BODY]).hexdigest()
    snap.title = str(rendered["title"])
    snap.meta_description = str(rendered["meta_description"])
    snap.h1 = str(rendered["h1"])
    snap.canonical = str(rendered["canonical"])
    snap.hreflang = str(rendered["hreflang"])
    snap.json_ld_types = str(rendered["json_ld_types"])
    snap.structured_data = str(rendered["structured_data"])
    snap.meta_robots = str(rendered["meta_robots"])
    snap.viewport = str(rendered["viewport"])
    snap.html_lang = str(rendered["html_lang"])
    snap.internal_links = str(rendered["internal_links"])
    snap.word_count = rendered_word_count
    snap.image_count = int(rendered["image_count"])
    snap.images_missing_alt = int(rendered["images_missing_alt"])
    snap.external_link_count = int(rendered["external_link_count"])
    snap.needs_js = rendered_needs_js
    snap.extracted = True
    snap.crawl_status = _status_for_http(snap.http_status or 200, snap.needs_js)
    snap.error = "已通过浏览器渲染复查" if not snap.needs_js else "浏览器渲染后仍疑似 JS 空壳"


def fetch_url(
    url: str,
    allowed_hosts: set[str],
    *,
    client: httpx.Client,
    robots: RobotsPolicy | None = None,
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
            started = time.perf_counter()
            response = client.get(current)
            snap.ttfb_ms = int(round((time.perf_counter() - started) * 1000))
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
    snap.content_type = response.headers.get("content-type", "").split(";", 1)[0].strip()[:160]
    snap.x_robots_tag = response.headers.get("x-robots-tag", "").strip()
    if not host_allowed(snap.final_url, allowed_hosts):
        snap.crawl_status = CRAWL_HOST
        snap.error = f"终态主机名不在允许列表：{urlparse(snap.final_url).hostname}"
        return snap

    raw_body = response.content or b""
    snap.html_bytes = len(raw_body)
    snap.body_hash = hashlib.sha256(raw_body[:MAX_BODY]).hexdigest() if raw_body else ""
    body = response.text or ""
    if len(body) > MAX_BODY:
        body = body[:MAX_BODY]
    snap.redirect_count = len(snap.redirects)
    extracted = extract_html(body, base_url=snap.final_url or url, allowed_hosts=allowed_hosts)
    snap.title = str(extracted["title"])
    snap.meta_description = str(extracted["meta_description"])
    snap.h1 = str(extracted["h1"])
    snap.canonical = str(extracted["canonical"])
    snap.hreflang = str(extracted["hreflang"])
    snap.json_ld_types = str(extracted["json_ld_types"])
    snap.structured_data = str(extracted["structured_data"])
    snap.meta_robots = str(extracted["meta_robots"])
    snap.viewport = str(extracted["viewport"])
    snap.html_lang = str(extracted["html_lang"])
    snap.internal_links = str(extracted["internal_links"])
    snap.word_count = int(extracted["word_count"])
    snap.image_count = int(extracted["image_count"])
    snap.images_missing_alt = int(extracted["images_missing_alt"])
    snap.external_link_count = int(extracted["external_link_count"])
    snap.needs_js = bool(extracted["needs_js"])
    snap.extracted = True
    snap.crawl_status = _status_for_http(response.status_code, snap.needs_js)
    if snap.crawl_status in {CRAWL_4XX, CRAWL_5XX}:
        snap.error = f"HTTP {response.status_code}"
    elif snap.needs_js:
        snap.error = "正文几乎是空壳，需要 JS 渲染。"
        _maybe_render_js_snapshot(snap, allowed_hosts=allowed_hosts)
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
) -> list[tuple[str, SitePage | None, PageSnapshot]]:
    """Serial GET. Each URL gets its own Client — httpx.Client is not thread-safe."""
    allowed = allowed_hosts_from_origin(origin)
    items = list(targets)
    with make_client(transport=transport) as robots_client:
        robots = load_robots(origin, robots_client)
    results: list[tuple[str, SitePage | None, PageSnapshot]] = []
    with ExitStack() as stack:
        clients = [stack.enter_context(make_client(transport=transport)) for _item in items]
        for (url, page), client in zip(items, clients):
            snap = fetch_url(url, allowed, client=client, robots=robots)
            results.append((url, page, snap))
    return results


def _target_key(url: str) -> str:
    parsed = urlparse(url)
    return parsed._replace(fragment="", query="").geturl().rstrip("/") or parsed.geturl()


def _internal_paths(internal_links: str) -> list[str]:
    paths: list[str] = []
    for raw in (internal_links or "").splitlines():
        item = raw.strip()
        if item.startswith("/") and not item.startswith("//"):
            paths.append(item.split("#", 1)[0])
    return paths


def fetch_site(
    origin: str,
    registered_pages: list[SitePage],
    *,
    max_urls: int = 50,
    max_depth: int = 2,
    transport: httpx.BaseTransport | None = None,
) -> list[tuple[CrawlTarget, PageSnapshot]]:
    """Small diagnostic site crawl: sitemap + registered pages + internal links."""
    allowed = allowed_hosts_from_origin(origin)
    page_by_path = {(p.path or "/").strip() or "/": p for p in registered_pages}
    queue: deque[CrawlTarget] = deque()
    queued: set[str] = set()
    sitemap_keys: set[str] = set()

    def enqueue(url: str, *, page: SitePage | None = None, depth: int = 0, source: str = "internal_link", in_sitemap: bool = False) -> None:
        if not host_allowed(url, allowed):
            return
        key = _target_key(url)
        if key in queued or len(queued) >= max_urls:
            return
        queued.add(key)
        queue.append(CrawlTarget(url=url, page=page, depth=depth, source=source, in_sitemap=in_sitemap))

    with make_client(transport=transport) as setup_client:
        robots = load_robots(origin, setup_client)
        for url in discover_sitemap_urls(origin, allowed, client=setup_client, max_urls=max_urls):
            sitemap_keys.add(_target_key(url))
            path = urlparse(url).path or "/"
            enqueue(url, page=page_by_path.get(path), depth=0, source="sitemap", in_sitemap=True)

    enqueue(build_fetch_url(origin, "/"), page=page_by_path.get("/"), depth=0, source="root", in_sitemap=_target_key(build_fetch_url(origin, "/")) in sitemap_keys)
    for page in registered_pages:
        url = build_fetch_url(origin, page.path)
        enqueue(url, page=page, depth=0, source=page.discovery_source or "manual", in_sitemap=_target_key(url) in sitemap_keys)

    results: list[tuple[CrawlTarget, PageSnapshot]] = []
    while queue and len(results) < max_urls:
        target = queue.popleft()
        with make_client(transport=transport) as client:
            snap = fetch_url(target.url, allowed, client=client, robots=robots)
        results.append((target, snap))
        if not snap.usable or target.depth >= max_depth:
            continue
        for path in _internal_paths(snap.internal_links):
            enqueue(
                build_fetch_url(origin, path),
                page=page_by_path.get(path),
                depth=target.depth + 1,
                source="internal_link",
                in_sitemap=_target_key(build_fetch_url(origin, path)) in sitemap_keys,
            )
    return results


def apply_observation(page: SitePage, snap: PageSnapshot) -> None:
    """Overwrite observation fields only. Never touch issue drafts."""
    page.crawl_status = snap.crawl_status
    page.fetched_at = datetime.now(timezone.utc)
    page.final_url = snap.final_url or ""
    page.http_status = snap.http_status
    page.content_type = snap.content_type[:160]
    page.ttfb_ms = snap.ttfb_ms
    page.redirect_count = snap.redirect_count
    page.html_bytes = snap.html_bytes
    page.body_hash = snap.body_hash[:64]
    page.needs_js = snap.needs_js
    page.fetch_mode = snap.fetch_mode[:40]
    page.render_status = snap.render_status[:40]
    page.render_final_url = snap.render_final_url[:700]
    page.render_word_count = snap.render_word_count
    page.crawl_error = snap.error or ""
    page.x_robots_tag = snap.x_robots_tag[:300]
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
    page.meta_robots = snap.meta_robots[:300]
    page.word_count = snap.word_count
    page.image_count = snap.image_count
    page.images_missing_alt = snap.images_missing_alt
    page.external_link_count = snap.external_link_count
    # index_status stays untested — HTML is not GSC.
