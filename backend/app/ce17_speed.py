"""17CE overseas HTTP checks. Open-time and status, not PageSpeed scores."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import ssl
import time

import websockets

WS_ENDPOINT = "wss://wsapi.17ce.com:8001/socket/"
ORIGIN = "https://www.17ce.com"


class Ce17Error(RuntimeError):
    pass


def md5_hex(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def auth_code(user: str, api_pwd: str, ut: str) -> str:
    raw = md5_hex(api_pwd)[4:23] + user.strip() + ut
    return md5_hex(base64.b64encode(raw.encode("utf-8")).decode("utf-8"))


def ws_url(user: str, api_pwd: str, ut: str | None = None) -> str:
    stamp = ut or str(int(time.time()))
    return f"{WS_ENDPOINT}?ut={stamp}&code={auth_code(user, api_pwd, stamp)}&user={user.strip()}"


def speed_request(url: str, node_num: int = 3) -> dict:
    return {
        "txnid": 1,
        "nodetype": 1,
        "num": node_num,
        "Url": url,
        "TestType": "HTTP",
        "TimeOut": 30,
        "Request": "GET",
        "NoCache": True,
        "type": 1,
        "isps": [3],
        "areas": [2, 3],
        "pro_ids": [0],
        "city_ids": [0],
        "FollowLocation": 2,
        "UserAgent": "Mozilla/5.0 (compatible; G-Snipers-Overseas/1.0)",
    }


def _node_name(row: dict) -> str:
    info = row.get("NodeInfo") or {}
    return str(
        info.get("name")
        or info.get("city")
        or info.get("prov")
        or info.get("isp")
        or row.get("NodeID")
        or "海外节点"
    )


def _total_ms(row: dict) -> int:
    value = float(row.get("TotalTime") or 0)
    return int(round(value * 1000 if value < 120 else value))


def summarize_rows(url: str, rows: list[dict]) -> dict:
    lines: list[str] = []
    times: list[int] = []
    ok = 0
    for row in rows:
        name = _node_name(row)
        code = row.get("HttpCode")
        if code in (None, 0) or int(code) >= 400:
            lines.append(f"{name} 失败：HTTP {code or '-'}")
            continue
        ok += 1
        total_ms = _total_ms(row)
        times.append(total_ms)
        lines.append(f"{name} {code} {total_ms}ms")
    if not rows:
        raise Ce17Error("17CE 没有返回任何节点结果。")
    return {
        "performance_score": None,
        "seo_score": None,
        "accessibility_score": None,
        "best_practices_score": None,
        "lcp_ms": round(sum(times) / len(times)) if times else None,
        "inp_ms": max(times) if times else None,
        "cls": None,
        "detail": f"17CE 海外打开 {url}：通 {ok}/{len(rows)}。" + (" " + "；".join(lines) if lines else ""),
    }


def _auth_failed(payload: dict) -> str:
    result = payload.get("result") if isinstance(payload.get("result"), dict) else payload
    rt = result.get("rt") if isinstance(result, dict) else payload.get("rt")
    msg = ""
    if isinstance(result, dict):
        msg = str(result.get("msg") or result.get("error") or "")
    msg = msg or str(payload.get("error") or payload.get("msg") or "")
    if rt in (-1, "-1") or "auth" in msg.lower() or payload.get("error") in {"10008", 10008}:
        return msg or "17CE 认证失败。请确认账号、api_pwd，以及 WebSocket 账户里有积分。"
    return ""


async def _run_check(*, user: str, api_pwd: str, url: str, node_num: int) -> dict:
    context = ssl.create_default_context()
    async with websockets.connect(
        ws_url(user, api_pwd),
        origin=ORIGIN,
        ssl=context,
        open_timeout=15,
        close_timeout=5,
        max_size=2**22,
    ) as ws:
        first = json.loads(await asyncio.wait_for(ws.recv(), 15))
        failed = _auth_failed(first)
        if failed:
            raise Ce17Error(failed)
        if first.get("type") not in {"NewData", "TaskAccept", "TaskEnd", "TaskErr"}:
            await ws.send(json.dumps(speed_request(url, node_num), ensure_ascii=False))
        elif first.get("type") == "TaskErr":
            raise Ce17Error(first.get("error") or "17CE 测速出错。")

        rows: list[dict] = []
        if first.get("type") == "NewData" and first.get("data"):
            rows.append(first["data"])

        deadline = time.monotonic() + 50
        while time.monotonic() < deadline:
            try:
                payload = json.loads(await asyncio.wait_for(ws.recv(), 20))
            except TimeoutError as exc:
                raise Ce17Error("17CE 海外节点还没返回结果。请稍后重试，不会在后台偷偷完成。") from exc
            kind = payload.get("type")
            if kind == "NewData" and payload.get("data"):
                rows.append(payload["data"])
            elif kind == "TaskEnd":
                break
            elif kind == "TaskErr":
                raise Ce17Error(payload.get("error") or "17CE 测速出错。")
            failed = _auth_failed(payload)
            if failed:
                raise Ce17Error(failed)
        if not rows:
            raise Ce17Error("17CE 没有返回海外节点结果。请确认 WebSocket 账户有积分。")
        return summarize_rows(url, rows)


def run_overseas_http_check(*, user: str, api_pwd: str, url: str, node_num: int = 3) -> dict:
    if not (user or "").strip() or not (api_pwd or "").strip():
        raise Ce17Error("未配置 17CE 账号或 api_pwd。")
    return asyncio.run(_run_check(user=user.strip(), api_pwd=api_pwd.strip(), url=url, node_num=node_num))
