"""Server-side Google HTTP. Production in Beijing must use the Cloudflare Worker."""

from __future__ import annotations

from typing import Any

import httpx

from app.config import settings

ALLOWED_HOSTS = {
    "oauth2.googleapis.com",
    "www.googleapis.com",
    "searchconsole.googleapis.com",
    "pagespeedonline.googleapis.com",
}


def configured() -> bool:
    return bool(settings.google_relay_url.strip() and settings.google_relay_key.strip())


def _host(url: str) -> str:
    from urllib.parse import urlparse

    return (urlparse(url).hostname or "").lower()


def request(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    data: Any = None,
    json: Any = None,
    timeout: float = 30,
) -> httpx.Response:
    host = _host(url)
    if host not in ALLOWED_HOSTS:
        raise ValueError(f"Google relay refuses host {host or url}")

    outbound = dict(headers or {})
    if configured():
        target = settings.google_relay_url.rstrip("/") + "/"
        outbound["x-relay-key"] = settings.google_relay_key
        outbound["x-relay-target"] = url
        with httpx.Client(timeout=timeout) as client:
            return client.request(method, target, headers=outbound, data=data, json=json)

    with httpx.Client(timeout=timeout) as client:
        return client.request(method, url, headers=headers, data=data, json=json)
