"""Public profile checks. No login, no register, no send."""

from __future__ import annotations

from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx

from app.official_apis import OFFICIAL_APIS

GENERIC_PATHS = {"", "/company", "/compose/post", "/pin-builder", "/tiktokstudio"}


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        values = {key.lower(): value or "" for key, value in attrs}
        href = values.get("href", "")
        if href:
            self.links.append(href)


def is_http_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def is_generic_profile_url(url: str) -> bool:
    text = (url or "").strip().rstrip("/")
    if not text:
        return True
    generics = {spec.compose_url.rstrip("/") for spec in OFFICIAL_APIS.values()}
    if text in generics:
        return True
    path = (urlparse(text).path or "").rstrip("/")
    return path in GENERIC_PATHS


def _host(url: str) -> str:
    return (urlparse(url if "://" in url else f"https://{url}").hostname or "").lower()


def check_public_profile(*, profile_url: str, site_origin: str, brand: str = "") -> dict:
    if not is_http_url(profile_url):
        raise ValueError("公开主页必须是 http/https 地址。")
    if is_generic_profile_url(profile_url):
        raise ValueError("这是官方发帖入口或站点首页，不是这家客户的公开主页。先填具体公司页/档案 URL。我们不猜、不注册、不代登。")

    site_host = _host(site_origin)
    brand_key = (brand or "").strip().lower()
    http_status: int | None = None
    is_live = False
    site_found = False
    brand_mentioned = False
    try:
        with httpx.Client(timeout=20, follow_redirects=True, headers={"User-Agent": "G-Snipers-ProfileCheck/0.1"}) as client:
            response = client.get(profile_url)
        http_status = response.status_code
        is_live = 200 <= response.status_code < 400
        text = (response.text or "")[:300000]
        lowered = text.lower()
        brand_mentioned = bool(brand_key and brand_key in lowered)
        if site_host and site_host in lowered:
            site_found = True
        parser = _LinkParser()
        parser.feed(text)
        for href in parser.links:
            host = _host(href)
            if site_host and site_host in host:
                site_found = True
                break
        if http_status == 451:
            note = "URL 返回 HTTP 451，公开抓不到（登录墙或地区限制）。不等于没有主页，也不等于我们代发。请人打开看。"
        elif not is_live:
            note = f"URL 返回 HTTP {http_status}，公开主页打不开。不是我们注册的，也不代发。"
        elif site_found:
            note = "公开主页打得开，页上有客户官网域名或链接。登记≠我们代发。"
        elif brand_mentioned:
            note = "公开主页打得开，提到了品牌名，但没找到官网域名。请补官网链。登记≠我们代发。"
        else:
            note = "公开主页打得开，没找到客户官网。先核对是不是这家的页。登记≠我们代发。"
    except httpx.HTTPError as exc:
        note = f"核验请求失败：{str(exc)[:200]}。不是我们代发。"
    return {
        "profile_url": profile_url,
        "http_status": http_status,
        "is_live": is_live,
        "site_found": site_found,
        "brand_mentioned": brand_mentioned,
        "note": note,
        "sent": False,
    }
