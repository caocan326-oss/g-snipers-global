"""Rule-based citation classes. A shop URL is never an official site.

owned = the customer's registered host. marketplace = known shops.
Everything else is other. Owned wins if the customer registered a shop host.
"""

from __future__ import annotations

from urllib.parse import urlparse

MARKETPLACE_ROOTS = (
    "jd.com",
    "jd.hk",
    "tmall.com",
    "tmall.hk",
    "taobao.com",
    "pinduoduo.com",
    "yangkeduo.com",
    "suning.com",
    "vip.com",
    "1688.com",
    "kaola.com",
    "gome.com.cn",
    "dangdang.com",
    "alibaba.com",
    "aliexpress.com",
    "made-in-china.com",
    "globalsources.com",
    "walmart.com",
    "newegg.com",
    "bestbuy.com",
)

MARKETPLACE_BRANDS = ("amazon", "ebay", "shopee", "lazada")


def citation_host(value: str) -> str:
    host = urlparse(value if "://" in (value or "") else f"https://{value}").netloc.lower()
    return host[4:] if host.startswith("www.") else host


def is_owned_url(url: str, root: str, aliases: list[str] | None = None) -> bool:
    host = citation_host(url)
    if not host or not root:
        return False
    owned_root = citation_host(root)
    extra = {citation_host(item) for item in (aliases or []) if item}
    return host == owned_root or host.endswith("." + owned_root) or host in extra


def is_marketplace_host(host: str) -> bool:
    value = (host or "").lower()
    if not value:
        return False
    if any(value == root or value.endswith("." + root) for root in MARKETPLACE_ROOTS):
        return True
    for brand in MARKETPLACE_BRANDS:
        if value.startswith(brand + ".") or f".{brand}." in value or value.endswith(f".{brand}.com"):
            return True
    return False


def is_marketplace_url(url: str) -> bool:
    return is_marketplace_host(citation_host(url))


def classify_citation(url: str, root: str, aliases: list[str] | None = None) -> str:
    if is_owned_url(url, root, aliases):
        return "owned"
    if is_marketplace_url(url):
        return "marketplace"
    return "other"


def split_citations(
    urls: list[str],
    root: str,
    aliases: list[str] | None = None,
) -> tuple[list[str], list[str], list[str]]:
    owned: list[str] = []
    marketplace: list[str] = []
    other: list[str] = []
    seen: set[str] = set()
    for url in urls:
        value = (url or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        kind = classify_citation(value, root, aliases)
        if kind == "owned":
            owned.append(value)
        elif kind == "marketplace":
            marketplace.append(value)
        else:
            other.append(value)
    return owned, marketplace, other


def marketplace_urls(urls: list[str]) -> list[str]:
    return [url for url in urls if is_marketplace_url(url)]
