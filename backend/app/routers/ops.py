from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth import require_admin
from app.database import get_db
from app.db_backup import copy_offsite, dump_path, dump_tables, status, write_dump
from app.models import User
from app.schemas import BackupCreateOut, BackupStatusOut

router = APIRouter(prefix="/api/ops", tags=["ops"])


@router.get("/backup", response_model=BackupStatusOut)
def backup_status(admin: User = Depends(require_admin)) -> BackupStatusOut:
    del admin
    return BackupStatusOut(**status())


@router.post("/backup", response_model=BackupCreateOut)
def create_backup(admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> BackupCreateOut:
    del admin
    path = write_dump(dump_tables(db))
    try:
        offsite = copy_offsite(path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"本机已写出，异地抄送失败：{exc}") from exc
    return BackupCreateOut(
        filename=path.name,
        size_bytes=path.stat().st_size,
        offsite=offsite,
        note="已在导出落点留下一份。定时任务仍是关的。",
    )


@router.get("/backup/{filename}")
def download_backup(filename: str, admin: User = Depends(require_admin)):
    del admin
    path = dump_path(filename)
    if path is None:
        raise HTTPException(status_code=404, detail="没有这份副本。")
    return FileResponse(path, filename=path.name, media_type="application/gzip")
