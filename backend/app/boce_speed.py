"""Boce overseas HTTP checks. This is open-time and status, not PageSpeed scores."""

from __future__ import annotations

import time

import httpx

NODE_LIST_URL = "https://api.boce.com/v3/node/list"
CREATE_URL = "https://api.boce.com/v3/task/create/curl"
RESULT_URL = "https://api.boce.com/v3/task/curl/{task_id}"
PREFERRED_MARKERS = ("香港", "美国", "新加坡", "日本", "台湾", "韩国", "英国", "德国", "法国", "澳洲", "澳大利亚")
POLL_SECONDS = 4
POLL_ATTEMPTS = 12


class BoceError(RuntimeError):
    pass


def pick_overseas_node_ids(nodes: list[dict], limit: int = 3) -> list[str]:
    preferred: list[dict] = []
    rest: list[dict] = []
    seen: set[str] = set()
    for node in nodes:
        node_id = str(node.get("id") or "").strip()
        if not node_id or node_id in seen:
            continue
        seen.add(node_id)
        label = f"{node.get('node_name') or ''}{node.get('isp_name') or ''}"
        if any(marker in label for marker in PREFERRED_MARKERS):
            preferred.append(node)
        else:
            rest.append(node)
    return [str(node["id"]) for node in (preferred + rest)[:limit]]


def _require_ok(payload: dict, action: str) -> dict:
    if int(payload.get("error_code") or 0) != 0:
        raise BoceError(payload.get("error") or f"拨测{action}失败。")
    return payload.get("data") or {}


def list_overseas_nodes(client: httpx.Client, api_key: str) -> list[dict]:
    response = client.get(NODE_LIST_URL, params={"key": api_key, "area": "oversea"})
    response.raise_for_status()
    data = _require_ok(response.json(), "拉海外节点")
    return list(data.get("list") or [])


def create_curl_task(client: httpx.Client, api_key: str, url: str, node_ids: list[str]) -> str:
    response = client.get(
        CREATE_URL,
        params={"key": api_key, "host": url, "node_ids": ",".join(node_ids)},
    )
    response.raise_for_status()
    data = _require_ok(response.json(), "创建测速任务")
    task_id = str(data.get("id") or "").strip()
    if not task_id:
        raise BoceError("拨测没有返回任务编号。")
    return task_id


def fetch_curl_result(client: httpx.Client, api_key: str, task_id: str) -> dict:
    response = client.get(RESULT_URL.format(task_id=task_id), params={"key": api_key})
    response.raise_for_status()
    payload = response.json()
    if int(payload.get("error_code") or 0) != 0:
        raise BoceError(payload.get("error") or "拨测取结果失败。")
    return payload


def wait_for_curl_result(client: httpx.Client, api_key: str, task_id: str) -> list[dict]:
    last: dict = {}
    for _ in range(POLL_ATTEMPTS):
        last = fetch_curl_result(client, api_key, task_id)
        if last.get("done"):
            return list(last.get("list") or [])
        time.sleep(POLL_SECONDS)
    raise BoceError("拨测海外节点还没返回结果。请稍后重试，不会在后台偷偷完成。")


def summarize_rows(url: str, rows: list[dict]) -> dict:
    lines: list[str] = []
    times: list[int] = []
    ok = 0
    for row in rows:
        name = str(row.get("node_name") or "海外节点")
        if int(row.get("error_code") or 0) != 0:
            lines.append(f"{name} 失败：{row.get('error') or '未知错误'}")
            continue
        ok += 1
        total_ms = int(round(float(row.get("time_total") or 0) * 1000))
        times.append(total_ms)
        lines.append(f"{name} {row.get('http_code') or '-'} {total_ms}ms")
    if not rows:
        raise BoceError("拨测没有返回任何节点结果。")
    return {
        "performance_score": None,
        "seo_score": None,
        "accessibility_score": None,
        "best_practices_score": None,
        "lcp_ms": round(sum(times) / len(times)) if times else None,
        "inp_ms": max(times) if times else None,
        "cls": None,
        "detail": f"拨测海外打开 {url}：通 {ok}/{len(rows)}。" + (" " + "；".join(lines) if lines else ""),
    }


def run_overseas_http_check(*, api_key: str, url: str, node_limit: int = 3) -> dict:
    key = (api_key or "").strip()
    if not key:
        raise BoceError("未配置拨测 API Key。")
    with httpx.Client(timeout=20) as client:
        nodes = list_overseas_nodes(client, key)
        node_ids = pick_overseas_node_ids(nodes, limit=node_limit)
        if not node_ids:
            raise BoceError("拨测没有可用的海外节点。")
        task_id = create_curl_task(client, key, url, node_ids)
        rows = wait_for_curl_result(client, key, task_id)
    return summarize_rows(url, rows)
