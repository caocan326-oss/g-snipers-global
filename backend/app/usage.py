"""Daily paid-API caps per customer. Counts calls, not money."""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import UsageDaily, UsageQuota

_TENANT: ContextVar[str] = ContextVar("usage_tenant", default="")
_DB: ContextVar[Session | None] = ContextVar("usage_db", default=None)

METERS = (
    {
        "key": "serp",
        "label": "关键词排名",
        "vendor": "Bright Data",
        "default_daily": 15,
        "hint": "每查 1 个词算 1 次。按钮一次最多 5 个词。",
    },
    {
        "key": "bocha",
        "label": "AI 搜索 · 博查",
        "vendor": "博查",
        "default_daily": 24,
        "hint": "GEO 抽查每问 1 次。8 个买家问题就是 8 次。",
    },
    {
        "key": "bailian",
        "label": "AI 搜索 · 百炼",
        "vendor": "阿里云百炼",
        "default_daily": 24,
        "hint": "GEO 抽查每问 1 次。和博查分开算。",
    },
    {
        "key": "llm",
        "label": "改法与分析",
        "vendor": "大模型",
        "default_daily": 60,
        "hint": "写改法、分析、非联网抽查，每调用 1 次算 1 次。",
    },
    {
        "key": "pagespeed",
        "label": "测速",
        "vendor": "PageSpeed / 17CE",
        "default_daily": 8,
        "hint": "每测 1 个页面算 1 次。",
    },
)

_DEFAULTS = {item["key"]: int(item["default_daily"]) for item in METERS}
_LABELS = {item["key"]: item["label"] for item in METERS}


class UsageLimitError(Exception):
    def __init__(self, meter: str, used: int, limit: int, need: int) -> None:
        self.meter = meter
        self.used = used
        self.limit = limit
        self.need = need
        label = _LABELS.get(meter, meter)
        super().__init__(
            f"这家客户今天的「{label}」次数不够。已用 {used}/{limit}，这次还要 {need} 次。找管理员加当天上限，或明天再试。"
        )


def set_usage_tenant(tenant_id: str, db: Session | None = None) -> None:
    _TENANT.set(tenant_id or "")
    if db is not None:
        _DB.set(db)


def current_tenant_id() -> str:
    return _TENANT.get()


def usage_day() -> str:
    return datetime.now(timezone(timedelta(hours=8))).date().isoformat()


def default_limit(meter: str) -> int:
    return _DEFAULTS.get(meter, 0)


def quota_limit(db: Session, tenant_id: str, meter: str) -> int:
    row = (
        db.query(UsageQuota)
        .filter(UsageQuota.tenant_id == tenant_id, UsageQuota.meter == meter)
        .first()
    )
    if row is None:
        return default_limit(meter)
    return max(0, int(row.daily_limit))


def used_today(db: Session, tenant_id: str, meter: str) -> int:
    row = (
        db.query(UsageDaily)
        .filter(
            UsageDaily.tenant_id == tenant_id,
            UsageDaily.meter == meter,
            UsageDaily.used_on == usage_day(),
        )
        .first()
    )
    return int(row.used_count) if row else 0


@dataclass
class MeterSnapshot:
    key: str
    label: str
    vendor: str
    hint: str
    used: int
    limit: int
    remaining: int


def snapshot(db: Session, tenant_id: str, meter: str) -> MeterSnapshot:
    spec = next((item for item in METERS if item["key"] == meter), None)
    if spec is None:
        raise ValueError(meter)
    used = used_today(db, tenant_id, meter)
    limit = quota_limit(db, tenant_id, meter)
    return MeterSnapshot(
        key=meter,
        label=str(spec["label"]),
        vendor=str(spec["vendor"]),
        hint=str(spec["hint"]),
        used=used,
        limit=limit,
        remaining=max(0, limit - used),
    )


def tenant_usage(db: Session, tenant_id: str) -> list[MeterSnapshot]:
    return [snapshot(db, tenant_id, item["key"]) for item in METERS]


def assert_can(db: Session, tenant_id: str, meter: str, need: int = 1) -> MeterSnapshot:
    row = snapshot(db, tenant_id, meter)
    if need < 1:
        return row
    if row.used + need > row.limit:
        raise UsageLimitError(meter, row.used, row.limit, need)
    return row


def record(db: Session, tenant_id: str, meter: str, need: int = 1) -> MeterSnapshot:
    assert_can(db, tenant_id, meter, need)
    day = usage_day()
    row = (
        db.query(UsageDaily)
        .filter(UsageDaily.tenant_id == tenant_id, UsageDaily.meter == meter, UsageDaily.used_on == day)
        .first()
    )
    if row is None:
        row = UsageDaily(tenant_id=tenant_id, meter=meter, used_on=day, used_count=0)
        db.add(row)
        db.flush()
    row.used_count = int(row.used_count) + need
    db.flush()
    return snapshot(db, tenant_id, meter)


def record_current(meter: str, need: int = 1) -> None:
    tenant_id = current_tenant_id()
    db = _DB.get()
    if not tenant_id or db is None:
        return
    record(db, tenant_id, meter, need)


def raise_http(exc: UsageLimitError) -> None:
    raise HTTPException(status_code=429, detail=str(exc)) from exc


def set_quota(db: Session, tenant_id: str, meter: str, daily_limit: int, updated_by: str | None) -> MeterSnapshot:
    if meter not in _DEFAULTS:
        raise HTTPException(status_code=400, detail="没有这个接口。")
    limit = max(0, int(daily_limit))
    row = (
        db.query(UsageQuota)
        .filter(UsageQuota.tenant_id == tenant_id, UsageQuota.meter == meter)
        .first()
    )
    if row is None:
        row = UsageQuota(tenant_id=tenant_id, meter=meter, daily_limit=limit, updated_by=updated_by)
        db.add(row)
    else:
        row.daily_limit = limit
        row.updated_by = updated_by
    db.flush()
    return snapshot(db, tenant_id, meter)
