from __future__ import annotations

from dataclasses import dataclass, field

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
            note="预留：接入后可作为 Agent 搜索结果和来源观测源。",
        ),
    ]


def provider_status(key: str) -> GeoProviderStatus | None:
    normalized = normalize_provider_key(key)
    return next((row for row in provider_statuses() if row.key == normalized), None)


def normalize_provider_key(key: str) -> str:
    value = (key or "").strip().lower()
    if value in {"", "llm", "deepseek", "openai_compatible"}:
        return "deepseek"
    return value


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

    status = provider_status(provider)
    label = status.label if status else provider
    raise GeoProviderError(f"{label} provider 已预留，但当前版本尚未接入真实 API。")
