"""Shared LLM gateway. OpenAI-compatible HTTP, no vendor lock-in.

Missing LLM_API_KEY: app boots; callers get 未配置 and must not invent analysis.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.config import settings

UNCONFIGURED = "未配置"
UNTESTED = "未测"
OK = "ok"
ERROR = "error"


@dataclass
class LlmResult:
    configured: bool
    status: str
    text: str
    detail: str


def configured() -> bool:
    return bool((settings.llm_api_key or "").strip())


def status_label() -> str:
    return "已配置" if configured() else UNCONFIGURED


def gateway_info() -> dict[str, str | bool]:
    return {
        "configured": configured(),
        "status": status_label(),
        "env_var": "LLM_API_KEY",
        "base_url": settings.llm_base_url,
        "model": settings.llm_model,
        "note": "一个 OpenAI 兼容网关。未配 Key 时应用可启动，AI 步骤返回未配置，不编造分析。",
    }


def complete(*, system: str, user: str) -> LlmResult:
    if not configured():
        return LlmResult(
            configured=False,
            status=UNCONFIGURED,
            text="",
            detail="未配置 LLM_API_KEY。不编造分析、草稿或引用率。",
        )
    url = settings.llm_base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": settings.llm_model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }
    try:
        with httpx.Client(timeout=30.0) as client:
            res = client.post(url, json=payload, headers=headers)
        if res.status_code >= 400:
            return LlmResult(True, ERROR, "", f"LLM HTTP {res.status_code}，未编造结果。")
        data = res.json()
        text = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            or ""
        ).strip()
        if not text:
            return LlmResult(True, UNTESTED, "", "模型无输出，保持未测。")
        return LlmResult(True, OK, text, "")
    except Exception as exc:  # noqa: BLE001 — gateway must not crash the app
        return LlmResult(True, ERROR, "", f"LLM 调用失败：{exc}。未编造结果。")
