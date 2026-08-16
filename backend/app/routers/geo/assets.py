from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai_engine import assist_geo_asset
from app.auth import get_current_user
from app.database import get_db
from app.geo_helpers import CHECKLIST_DEFS, CHECK_STATUSES, build_llms_txt
from app.models import GeoAsset, GeoChecklistItem, SeoPage, Tenant, User
from app.schemas import (
    AiAssistOut,
    AiStepIn,
    ConfirmReadyIn,
    GeoAssetOut,
    GeoAssetUpdate,
    GeoChecklistItemOut,
    GeoChecklistItemUpdate,
)

from . import router


@router.get("/assets", response_model=list[GeoAssetOut])
def list_assets(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[GeoAsset]:
    return db.query(GeoAsset).filter(GeoAsset.tenant_id == user.tenant_id).all()


@router.post("/assets/llms.txt/generate", response_model=GeoAssetOut)
def generate_llms_txt(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> GeoAsset:
    tenant = db.get(Tenant, user.tenant_id)
    pages = db.query(SeoPage).filter(SeoPage.tenant_id == user.tenant_id).all()
    body = build_llms_txt(tenant, pages) if tenant else ""
    asset = db.query(GeoAsset).filter(GeoAsset.tenant_id == user.tenant_id, GeoAsset.kind == "llms_txt").first()
    if asset is None:
        asset = GeoAsset(tenant_id=user.tenant_id, kind="llms_txt", title="llms.txt 草稿")
        db.add(asset)
    asset.body = body
    asset.status = "draft"
    asset.updated_by = user.id
    db.commit()
    db.refresh(asset)
    return asset


@router.patch("/assets/{asset_id}", response_model=GeoAssetOut)
def update_asset(
    asset_id: str,
    body: GeoAssetUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GeoAsset:
    asset = db.get(GeoAsset, asset_id)
    if asset is None or asset.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="资产不存在")
    asset.body = body.body
    asset.status = "draft"
    asset.updated_by = user.id
    db.commit()
    db.refresh(asset)
    return asset


@router.post("/assets/{asset_id}/mark-ready", response_model=GeoAssetOut)
def mark_asset_ready(
    asset_id: str,
    body: ConfirmReadyIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GeoAsset:
    if not body.confirmed:
        raise HTTPException(status_code=400, detail="需要客户经理人工确认后才能标记可交付")
    asset = db.get(GeoAsset, asset_id)
    if asset is None or asset.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="资产不存在")
    if not asset.body.strip():
        raise HTTPException(status_code=400, detail="正文为空，不能标记可交付")
    asset.status = "ready"
    asset.updated_by = user.id
    db.commit()
    db.refresh(asset)
    return asset


@router.post("/checklists/ensure", response_model=list[GeoChecklistItemOut])
def ensure_checklist(
    seo_page_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[GeoChecklistItem]:
    page = db.get(SeoPage, seo_page_id)
    if page is None or page.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="选题不存在")
    existing = {
        i.item_key: i
        for i in db.query(GeoChecklistItem).filter(GeoChecklistItem.seo_page_id == seo_page_id).all()
    }
    for key, label in CHECKLIST_DEFS:
        if key not in existing:
            db.add(
                GeoChecklistItem(
                    tenant_id=user.tenant_id,
                    seo_page_id=seo_page_id,
                    item_key=key,
                    label=label,
                    status="untested",
                )
            )
    db.commit()
    return (
        db.query(GeoChecklistItem)
        .filter(GeoChecklistItem.seo_page_id == seo_page_id)
        .order_by(GeoChecklistItem.item_key)
        .all()
    )


@router.patch("/checklist-items/{item_id}", response_model=GeoChecklistItemOut)
def update_checklist_item(
    item_id: str,
    body: GeoChecklistItemUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GeoChecklistItem:
    if body.status not in CHECK_STATUSES:
        raise HTTPException(status_code=400, detail="无效清单状态")
    row = db.get(GeoChecklistItem, item_id)
    if row is None or row.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="清单项不存在")
    row.status = body.status
    row.notes = body.notes
    db.commit()
    db.refresh(row)
    return row


@router.post("/assets/{asset_id}/ai", response_model=AiAssistOut)
def ai_asset(
    asset_id: str,
    body: AiStepIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AiAssistOut:
    row = db.get(GeoAsset, asset_id)
    if row is None or row.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="资产不存在")
    payload = assist_geo_asset(db, row, step=body.step or "content")
    db.commit()
    return AiAssistOut(**payload)
