import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import SiteArchive, Tenant, User
from app.schemas import SiteArchiveDeleteIn, SiteArchiveOut, SiteArchiveRestoreOut
from app.site_context import archive_current_context, readable_counts, restore_archive_context

router = APIRouter(prefix="/api/site-context", tags=["site-context"])


def _archive_out(row: SiteArchive) -> SiteArchiveOut:
    counts = json.loads(row.counts_json or "{}")
    return SiteArchiveOut(
        id=row.id,
        site_origin=row.site_origin,
        archived_at=row.archived_at,
        restored_at=row.restored_at,
        note=row.note,
        counts=counts,
        readable_counts=readable_counts(counts),
    )


@router.get("/archives", response_model=list[SiteArchiveOut])
def list_archives(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[SiteArchiveOut]:
    rows = (
        db.query(SiteArchive)
        .filter(SiteArchive.tenant_id == user.tenant_id)
        .order_by(SiteArchive.archived_at.desc())
        .all()
    )
    return [_archive_out(row) for row in rows]


@router.post("/archives/{archive_id}/restore", response_model=SiteArchiveRestoreOut)
def restore_archive(
    archive_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SiteArchiveRestoreOut:
    archive = db.get(SiteArchive, archive_id)
    if archive is None or archive.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="历史网站不存在")
    tenant = db.get(Tenant, user.tenant_id)
    current_origin = (tenant.site_origin if tenant else "").strip()
    archived_current = False
    if current_origin and current_origin != archive.site_origin:
        archived_current = archive_current_context(db, user, note=f"恢复 {archive.site_origin} 前自动归档当前网站") is not None
    restore_archive_context(db, user, archive)
    db.commit()
    return SiteArchiveRestoreOut(
        restored=True,
        site_origin=archive.site_origin,
        archived_current=archived_current,
        note="已恢复历史网站，当前工作台已切回该网站数据。",
    )


@router.delete("/archives/{archive_id}", status_code=204)
def delete_archive(
    archive_id: str,
    body: SiteArchiveDeleteIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    archive = db.get(SiteArchive, archive_id)
    if archive is None or archive.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="历史网站不存在")
    if body.confirm.strip() not in {archive.site_origin, "DELETE"}:
        raise HTTPException(status_code=400, detail="删除历史数据需要二次确认，请输入网站域名或 DELETE。")
    db.delete(archive)
    db.commit()
