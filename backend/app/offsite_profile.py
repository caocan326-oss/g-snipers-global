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


def is_compose_url(url: str) -> bool:
    text = (url or "").strip().rstrip("/")
    if not text:
        return True
    generics = {spec.compose_url.rstrip("/") for spec in OFFICIAL_APIS.values()}
    if text in generics:
        return True
    parsed = urlparse(text)
    host = (parsed.hostname or "").lower().removeprefix("www.")
    path = (parsed.path or "").rstrip("/")
    for spec in OFFICIAL_APIS.values():
        spec_host = _host(spec.compose_url).removeprefix("www.")
        spec_path = urlparse(spec.compose_url).path.rstrip("/")
        if host == spec_host and (path == spec_path or path in GENERIC_PATHS):
            return True
    return False


def _host(url: str) -> str:
    return (urlparse(url if "://" in url else f"https://{url}").hostname or "").lower()


def _root_host(url: str) -> str:
    return _host(url).removeprefix("www.")


def is_own_site(url: str, site_origin: str) -> bool:
    left = _root_host(url)
    right = _root_host(site_origin)
    return bool(left and right and left == right)


def check_public_profile(
    *,
    profile_url: str,
    site_origin: str,
    brand: str = "",
    platform_name: str = "",
) -> dict:
    if not is_http_url(profile_url):
        raise ValueError("公开主页必须是 http/https 地址。")
    if is_compose_url(profile_url):
        raise ValueError("这是官方发帖入口，不是这家客户在该渠道的公司页。先填具体公司页 URL。我们不猜、不注册、不代登。")
    channel = (platform_name or "该渠道").strip() or "该渠道"
    if is_own_site(profile_url, site_origin):
        official = _fetch_profile(profile_url, site_origin, brand)
        if official["is_live"]:
            note = (
                f"这是客户官网，不是「{channel}」的公司页。官网打得开。"
                f"该渠道还没有可核的公开档案。不要拿别人的同名页来填。登记≠我们代发。"
            )
        else:
            note = (
                f"这是客户官网，不是「{channel}」的公司页。"
                f"{official['note']} 该渠道还没有可核的公开档案。不要拿别人的同名页来填。"
            )
        return {
            "profile_url": "",
            "http_status": official["http_status"],
            "is_live": False,
            "site_found": False,
            "brand_mentioned": False,
            "missing_channel_page": True,
            "note": note,
            "sent": False,
        }

    result = _fetch_profile(profile_url, site_origin, brand)
    result["missing_channel_page"] = False
    result["sent"] = False
    return result


def _fetch_profile(profile_url: str, site_origin: str, brand: str) -> dict:
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
        if site_host and (site_host in lowered or site_host.removeprefix("www.") in lowered):
            site_found = True
        parser = _LinkParser()
        parser.feed(text)
        for href in parser.links:
            host = _host(href)
            if site_host and (site_host in host or _root_host(site_origin) in host):
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
    }
