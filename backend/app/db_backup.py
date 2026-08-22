"""Customer DB copies. Daily schedule is off unless BACKUP_SCHEDULE_ENABLED=true."""

from __future__ import annotations

import gzip
import json
import shutil
import subprocess
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base

DUMP_PREFIX = "gsnipers-db-"


def local_dir() -> Path:
    raw = (settings.backup_local_dir or "").strip()
    path = Path(raw) if raw else Path.cwd() / "data" / "db-exports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


def dump_tables(db: Session) -> dict[str, Any]:
    inspector = inspect(db.bind)
    tables: dict[str, list[dict[str, Any]]] = {}
    for table in Base.metadata.sorted_tables:
        if table.name not in inspector.get_table_names():
            continue
        columns = [column.name for column in table.columns]
        rows = db.execute(text(f"SELECT * FROM {table.name}")).mappings().all()
        tables[table.name] = [{column: _json_value(row.get(column)) for column in columns} for row in rows]
    return {
        "format": "gsnipers-json-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "schedule_enabled": settings.backup_schedule_enabled,
        "tables": tables,
    }


def write_dump(payload: dict[str, Any]) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = local_dir() / f"{DUMP_PREFIX}{stamp}.json.gz"
    raw = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    path.write_bytes(gzip.compress(raw))
    _prune()
    return path


def _prune() -> None:
    keep = max(1, int(settings.backup_keep or 14))
    files = sorted(local_dir().glob(f"{DUMP_PREFIX}*.json.gz"), key=lambda item: item.stat().st_mtime, reverse=True)
    for stale in files[keep:]:
        stale.unlink(missing_ok=True)


def list_dumps() -> list[dict[str, Any]]:
    items = []
    for path in sorted(local_dir().glob(f"{DUMP_PREFIX}*"), key=lambda item: item.stat().st_mtime, reverse=True):
        items.append(
            {
                "filename": path.name,
                "size_bytes": path.stat().st_size,
                "modified_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
            }
        )
    return items


def dump_path(filename: str) -> Path | None:
    name = Path(filename).name
    if not name.startswith(DUMP_PREFIX) or ".." in name:
        return None
    path = local_dir() / name
    return path if path.is_file() else None


def offsite_configured() -> bool:
    kind = (settings.backup_offsite_kind or "none").strip().lower()
    if kind == "dir":
        return bool(settings.backup_offsite_dir.strip())
    if kind == "scp":
        return bool(settings.backup_offsite_scp.strip())
    return False


def copy_offsite(path: Path) -> str:
    kind = (settings.backup_offsite_kind or "none").strip().lower()
    if kind == "none" or not offsite_configured():
        return "skipped"
    if kind == "dir":
        dest_dir = Path(settings.backup_offsite_dir.strip())
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest_dir / path.name)
        return "copied"
    if kind == "scp":
        target = settings.backup_offsite_scp.strip().rstrip("/") + "/" + path.name
        subprocess.run(["scp", "-o", "BatchMode=yes", str(path), target], check=True)
        return "copied"
    raise RuntimeError(f"未知的异地方式：{kind}")


def status() -> dict[str, Any]:
    dumps = list_dumps()
    return {
        "schedule_enabled": bool(settings.backup_schedule_enabled),
        "local_dir": str(local_dir()),
        "keep": max(1, int(settings.backup_keep or 14)),
        "offsite_kind": (settings.backup_offsite_kind or "none").strip().lower() or "none",
        "offsite_configured": offsite_configured(),
        "offsite_dir": settings.backup_offsite_dir.strip() if (settings.backup_offsite_kind or "").strip().lower() == "dir" else "",
        "offsite_scp_set": bool(settings.backup_offsite_scp.strip()),
        "latest": dumps[0] if dumps else None,
        "dumps": dumps[:20],
        "note": "每天会在服务器打一份库副本。点导出再下载一份到你这台电脑。",
    }
