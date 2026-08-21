from __future__ import annotations

import json
from typing import Any
from dataclasses import dataclass, field

import httpx

from app.config import settings
from app.llm import OK, complete, configured as llm_configured


@dataclass
class GeoProviderStatus:
    key: str
    label: str
    configured: bool
    web_grounded: bool
    env_var: str
    role: str
    status: str = ""
    note: str = ""


@dataclass
class GeoProviderResult:
    provider: str
    engine: str
    model: str
    answer: str
    citations: list[str] = field(default_factory=list)
    web_grounded: bool = False
    surface: str = "api_proxy"
    status: str = "ok"
    detail: str = ""


class GeoProviderError(RuntimeError):
    pass


IMPLEMENTED_GROUNDED = frozenset({"bocha", "tavily"})


def configured_implemented_grounded() -> list[GeoProviderStatus]:
    return [row for row in provider_statuses() if row.configured and row.key in IMPLEMENTED_GROUNDED]


def provider_statuses() -> list[GeoProviderStatus]:
    return [
        GeoProviderStatus(
            key="deepseek",
            label="DeepSeek / LLM 网关",
            configured=llm_configured(),
            web_grounded=False,
            env_var="LLM_API_KEY",
            role="analysis",
            status="configured" if llm_configured() else "unconfigured",
            note="用于生成回答、分析和建议；不作为联网引用证据。",
        ),
        GeoProviderStatus(
            key="bocha",
            label="博查 Web Search",
            configured=bool(settings.bocha_api_key),
            web_grounded=True,
            env_var="BOCHA_API_KEY",
            role="search",
            status="configured" if settings.bocha_api_key else "unconfigured",
            note="SearchProvider：用于第三方来源、目录、媒体和 SourcePlatform 候选发现；不是 AI 答案 provider。",
        ),
        GeoProviderStatus(
            key="bailian",
            label="阿里云百炼联网搜索",
            configured=bool(settings.dashscope_api_key),
            web_grounded=True,
            env_var="DASHSCOPE_API_KEY",
            role="grounded_answer",
            status="configured" if settings.dashscope_api_key else "unconfigured",
            note="国内联网答案。能带回网址，但海外问句来源偏弱。默认不进「都测」，要看再选「只测这一源」。",
        ),
        GeoProviderStatus(
            key="perplexity",
            label="Perplexity",
            configured=bool(settings.perplexity_api_key),
            web_grounded=True,
            env_var="PERPLEXITY_API_KEY",
            role="ai_search",
            status="configured" if settings.perplexity_api_key else "unconfigured",
            note="预留：接入后可作为联网 AI 搜索引用观测源。",
        ),
        GeoProviderStatus(
            key="you",
            label="You.com",
            configured=bool(settings.you_api_key),
            web_grounded=True,
            env_var="YOU_API_KEY",
            role="ai_search",
            status="configured" if settings.you_api_key else "unconfigured",
            note="预留：接入后可作为联网 AI 搜索引用观测源。",
        ),
        GeoProviderStatus(
            key="exa",
            label="Exa",
            configured=bool(settings.exa_api_key),
            web_grounded=True,
            env_var="EXA_API_KEY",
            role="ai_search",
            status="configured" if settings.exa_api_key else "unconfigured",
            note="预留：接入后可用于语义搜索和第三方权威源发现。",
        ),
        GeoProviderStatus(
            key="tavily",
            label="Tavily",
            configured=bool(settings.tavily_api_key),
            web_grounded=True,
            env_var="TAVILY_API_KEY",
            role="ai_search",
            status="configured" if settings.tavily_api_key else "unconfigured",
            note="英文网页搜索：返回标题、摘要和网址，用来看海外结果里有没有官网。",
        ),
    ]


def provider_status(key: str) -> GeoProviderStatus | None:
    normalized = normalize_provider_key(key)
    return next((row for row in provider_statuses() if row.key == normalized), None)


def normalize_provider_key(key: str) -> str:
    value = (key or "").strip().lower()
    if value in {"", "llm", "deepseek", "openai_compatible"}:
        return "deepseek"
    if value in {"bocha_web_search", "bochaai", "bocha"}:
        return "bocha"
    if value in {"aliyun_bailian_web_search", "dashscope", "qwen_search", "bailian"}:
        return "bailian"
    if value in {"tavily_search", "tavily"}:
        return "tavily"
    return value


def _extract_urls_from_raw(data: Any) -> list[str]:
    raw_text = json.dumps(data, ensure_ascii=False)
    urls: list[str] = []
    for marker in ("http://", "https://"):
        start = 0
        while True:
            idx = raw_text.find(marker, start)
            if idx < 0:
                break
            end = idx
            while end < len(raw_text) and raw_text[end] not in ['"', "'", "\\", " ", "\n", "\r", "\t", ")", "]", "}"]:
                end += 1
            url = raw_text[idx:end].rstrip(".,;")
            if url:
                urls.append(url)
            start = end
    return sorted(set(urls))


def _search_result_urls(block: Any) -> list[str]:
    rows = []
    if isinstance(block, dict):
        rows = block.get("search_results") or block.get("searchResults") or []
    elif isinstance(block, list):
        rows = block
    urls: list[str] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        url = (item.get("url") or item.get("link") or "").strip()
        if url.startswith("http"):
            urls.append(url)
    return urls


def _bailian_urls(data: dict) -> list[str]:
    output = data.get("output") if isinstance(data.get("output"), dict) else {}
    urls = _search_result_urls(output.get("search_info") or output.get("searchInfo"))
    urls.extend(_search_result_urls(data.get("search_info") or data.get("search_results")))
    if urls:
        return sorted(set(urls))
    return _extract_urls_from_raw(data)


def _bailian_answer(data: dict) -> str:
    output = data.get("output") if isinstance(data.get("output"), dict) else {}
    choices = output.get("choices") or data.get("choices") or []
    if not choices:
        text = output.get("text") or ""
        return text.strip() if isinstance(text, str) else ""
    message = choices[0].get("message") or {}
    content = message.get("content") or ""
    return content.strip() if isinstance(content, str) else ""


def _call_bocha(prompt_text: str) -> GeoProviderResult:
    if not settings.bocha_api_key:
        raise GeoProviderError("未配置 BOCHA_API_KEY，不能执行博查搜索采样。")
    payload = {"query": prompt_text, "freshness": "noLimit", "summary": True, "count": 10}
    from app.usage import UsageLimitError, record_current

    try:
        record_current("bocha", 1)
    except UsageLimitError:
        raise
    try:
        with httpx.Client(timeout=45) as client:
            response = client.post(
                settings.bocha_web_search_url,
                headers={"Authorization": f"Bearer {settings.bocha_api_key}", "Content-Type": "application/json"},
                json=payload,
            )
        if response.status_code >= 400:
            raise GeoProviderError(f"博查返回 HTTP {response.status_code}: {response.text[:300]}")
        data = response.json()
    except httpx.HTTPError as exc:
        raise GeoProviderError(f"博查请求失败：{str(exc)[:200]}") from exc

    pages = (((data.get("data") or {}).get("webPages") or {}).get("value") or [])
    urls: list[str] = []
    snippets: list[str] = []
    for item in pages:
        url = item.get("url") or ""
        if url:
            urls.append(url)
        title = item.get("name") or item.get("title") or ""
        snippet = item.get("snippet") or item.get("summary") or ""
        if title or snippet:
            snippets.append(f"{title}\n{snippet}".strip())
    return GeoProviderResult(
        provider="bocha",
        engine="bocha",
        model="bocha-web-search",
        answer="\n\n".join(snippets) or json.dumps(data, ensure_ascii=False)[:2000],
        citations=sorted(set(urls)),
        web_grounded=True,
        surface="search_provider",
        detail=f"Bocha returned {len(urls)} source URLs.",
    )


def _tavily_country(region_hint: str) -> str:
    value = (region_hint or "").strip().lower()
    aliases = {
        "us": "united states",
        "usa": "united states",
        "uk": "united kingdom",
        "gb": "united kingdom",
        "de": "germany",
        "jp": "japan",
        "ae": "united arab emirates",
        "au": "australia",
    }
    if value in aliases:
        return aliases[value]
    if len(value) > 3:
        return value
    return ""


def _call_tavily(prompt_text: str, region_hint: str = "") -> GeoProviderResult:
    if not settings.tavily_api_key:
        raise GeoProviderError("未配置 TAVILY_API_KEY，不能执行 Tavily 搜索采样。")
    payload: dict[str, Any] = {
        "query": prompt_text,
        "search_depth": "basic",
        "include_answer": True,
        "max_results": 8,
    }
    country = _tavily_country(region_hint)
    if country:
        payload["country"] = country
    from app.usage import UsageLimitError, record_current

    try:
        record_current("tavily", 1)
    except UsageLimitError:
        raise
    try:
        with httpx.Client(timeout=45) as client:
            response = client.post(
                settings.tavily_search_url,
                headers={"Authorization": f"Bearer {settings.tavily_api_key}", "Content-Type": "application/json"},
                json=payload,
            )
        if response.status_code >= 400:
            raise GeoProviderError(f"Tavily 返回 HTTP {response.status_code}: {response.text[:300]}")
        data = response.json()
    except httpx.HTTPError as exc:
        raise GeoProviderError(f"Tavily 请求失败：{str(exc)[:200]}") from exc

    pages = data.get("results") or []
    urls: list[str] = []
    snippets: list[str] = []
    answer = (data.get("answer") or "").strip()
    if answer:
        snippets.append(answer)
    for item in pages:
        url = item.get("url") or ""
        if url:
            urls.append(url)
        title = item.get("title") or ""
        snippet = item.get("content") or ""
        if title or snippet:
            snippets.append(f"{title}\n{snippet}".strip())
    return GeoProviderResult(
        provider="tavily",
        engine="tavily",
        model="tavily-search",
        answer="\n\n".join(snippets) or json.dumps(data, ensure_ascii=False)[:2000],
        citations=sorted(set(urls)),
        web_grounded=True,
        surface="search_provider",
        detail=f"Tavily returned {len(urls)} source URLs.",
    )


def _call_bailian(prompt_text: str, model: str = "", region_hint: str = "") -> GeoProviderResult:
    if not settings.dashscope_api_key:
        raise GeoProviderError("未配置 DASHSCOPE_API_KEY，不能执行百炼联网采样。")
    system = "You are a search-grounded B2B SEO/GEO evaluator. Prefer reliable official or third-party sources."
    if region_hint:
        system += f" Region hint: {region_hint}."
    model_name = model or settings.bailian_model or "qwen-plus"
    payload = {
        "model": model_name,
        "input": {
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt_text},
            ]
        },
        "parameters": {
            "result_format": "message",
            "enable_search": True,
            "search_options": {
                "enable_source": True,
                "enable_citation": True,
            },
        },
    }
    from app.usage import UsageLimitError, record_current

    try:
        record_current("bailian", 1)
    except UsageLimitError:
        raise
    try:
        with httpx.Client(timeout=90) as client:
            response = client.post(
                settings.bailian_generation_url,
                headers={"Authorization": f"Bearer {settings.dashscope_api_key}", "Content-Type": "application/json"},
                json=payload,
            )
        if response.status_code >= 400:
            raise GeoProviderError(f"百炼返回 HTTP {response.status_code}: {response.text[:300]}")
        data = response.json()
    except httpx.HTTPError as exc:
        raise GeoProviderError(f"百炼请求失败：{str(exc)[:200]}") from exc

    if data.get("code") and data.get("code") not in {"", "Success", "success"}:
        raise GeoProviderError(f"百炼返回 {data.get('code')}: {str(data.get('message') or '')[:200]}")

    urls = _bailian_urls(data)
    answer = _bailian_answer(data)
    return GeoProviderResult(
        provider="bailian",
        engine="bailian",
        model=model_name,
        answer=answer or json.dumps(data, ensure_ascii=False)[:2000],
        citations=urls,
        web_grounded=True,
        surface="grounded_answer_provider",
        detail=f"Bailian returned {len(urls)} source URLs.",
    )


def sample_with_provider(
    provider_key: str,
    *,
    prompt_text: str,
    model: str = "",
    region_hint: str = "",
) -> GeoProviderResult:
    provider = normalize_provider_key(provider_key)
    if provider == "deepseek":
        if not llm_configured():
            raise GeoProviderError("未配置 LLM_API_KEY，不能执行 DeepSeek/LLM 采样。")
        system = (
            "You are answering as a buyer-facing AI assistant. "
            "Answer the user's question directly. "
            "Do not invent source citations. Do not mention this evaluation instruction."
        )
        if region_hint:
            system += f" Region hint: {region_hint}."
        res = complete(system=system, user=prompt_text)
        if res.status != OK:
            raise GeoProviderError(f"{res.status} {res.detail}".strip())
        return GeoProviderResult(
            provider="deepseek",
            engine="deepseek",
            model=model or settings.llm_model or "configured-llm",
            answer=res.text,
            citations=[],
            web_grounded=False,
            surface="llm_api_non_grounded",
            detail=res.detail,
        )

    if provider == "bocha":
        return _call_bocha(prompt_text)

    if provider == "tavily":
        return _call_tavily(prompt_text, region_hint=region_hint)

    if provider == "bailian":
        return _call_bailian(prompt_text, model=model, region_hint=region_hint)

    status = provider_status(provider)
    label = status.label if status else provider
    raise GeoProviderError(f"{label} provider 已预留，但当前版本尚未接入真实 API。")
