from datetime import datetime, timezone

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.auth import get_current_user
from app.database import get_db
from app.models import ContentAsset, FactPack, User
from app.schemas import (
    ContentAssetApproveIn,
    ContentAssetCreate,
    ContentAssetGenerateIn,
    ContentAssetOut,
    ContentAssetReviewOut,
    ContentAssetUpdate,
    FactPackCreate,
    FactPackOut,
    FactPackUpdate,
)

from . import router
from .common import _asset_out, _fact_pack_out, _generate_asset_body, _review_asset
from .constants import ASSET_STATUSES, ASSET_TYPES, FACT_PACK_STATUSES


@router.get("/fact-packs", response_model=list[FactPackOut])
def list_fact_packs(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[FactPackOut]:
    rows = db.query(FactPack).filter(FactPack.tenant_id == user.tenant_id).order_by(FactPack.created_at.desc()).all()
    return [_fact_pack_out(row) for row in rows]


@router.post("/fact-packs", response_model=FactPackOut, status_code=201)
def create_fact_pack(
    body: FactPackCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FactPackOut:
    if body.status not in FACT_PACK_STATUSES:
        raise HTTPException(status_code=400, detail="无效事实包状态")
    row = FactPack(tenant_id=user.tenant_id, **body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return _fact_pack_out(row)


@router.patch("/fact-packs/{fact_pack_id}", response_model=FactPackOut)
def update_fact_pack(
    fact_pack_id: str,
    body: FactPackUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FactPackOut:
    row = db.get(FactPack, fact_pack_id)
    if row is None or row.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="事实包不存在")
    payload = body.model_dump(exclude_unset=True)
    if "status" in payload and payload["status"] not in FACT_PACK_STATUSES:
        raise HTTPException(status_code=400, detail="无效事实包状态")
    for field, value in payload.items():
        setattr(row, field, value or "")
    row.version += 1
    if row.status != "approved":
        row.approved_by = ""
        row.approved_at = None
    db.commit()
    db.refresh(row)
    return _fact_pack_out(row)


@router.post("/fact-packs/{fact_pack_id}/approve", response_model=FactPackOut)
def approve_fact_pack(
    fact_pack_id: str,
    body: ContentAssetApproveIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FactPackOut:
    if not body.confirmed:
        raise HTTPException(status_code=400, detail="批准事实包需要人工确认")
    row = db.get(FactPack, fact_pack_id)
    if row is None or row.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="事实包不存在")
    if not row.legal_name.strip() or not row.brand_names.strip() or not row.website.strip():
        raise HTTPException(status_code=400, detail="事实包至少需要公司英文名、品牌名和官网")
    row.status = "approved"
    row.approved_by = user.email
    row.approved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return _fact_pack_out(row)


@router.get("/content-assets", response_model=list[ContentAssetOut])
def list_content_assets(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[ContentAssetOut]:
    rows = (
        db.query(ContentAsset)
        .options(selectinload(ContentAsset.fact_pack))
        .filter(ContentAsset.tenant_id == user.tenant_id)
        .order_by(ContentAsset.created_at.desc())
        .all()
    )
    return [_asset_out(row) for row in rows]


@router.post("/content-assets", response_model=ContentAssetOut, status_code=201)
def create_content_asset(
    body: ContentAssetCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ContentAssetOut:
    if body.asset_type not in ASSET_TYPES:
        raise HTTPException(status_code=400, detail="无效内容资产类型")
    fact = None
    if body.fact_pack_id:
        fact = db.get(FactPack, body.fact_pack_id)
        if fact is None or fact.tenant_id != user.tenant_id:
            raise HTTPException(status_code=404, detail="事实包不存在")
    row = ContentAsset(tenant_id=user.tenant_id, **body.model_dump())
    db.add(row)
    db.commit()
    row = db.query(ContentAsset).options(selectinload(ContentAsset.fact_pack)).filter(ContentAsset.id == row.id).one()
    return _asset_out(row)


@router.post("/content-assets/generate", response_model=ContentAssetOut, status_code=201)
def generate_content_asset(
    body: ContentAssetGenerateIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ContentAssetOut:
    fact = db.get(FactPack, body.fact_pack_id)
    if fact is None or fact.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="事实包不存在")
    if fact.status != "approved":
        raise HTTPException(status_code=400, detail="事实包未批准，不能生成对外内容草稿")
    if body.asset_type not in ASSET_TYPES:
        raise HTTPException(status_code=400, detail="无效内容资产类型")
    title = body.title or f"{fact.name} · {body.asset_type}"
    row = ContentAsset(
        tenant_id=user.tenant_id,
        fact_pack_id=fact.id,
        asset_type=body.asset_type,
        title=title,
        body_md=_generate_asset_body(fact, body.asset_type),
        locale=body.locale,
        keywords=fact.product_categories_en,
        entities=", ".join(part for part in [fact.legal_name, fact.brand_names, fact.certifications] if part),
        status="draft",
    )
    db.add(row)
    db.commit()
    row = db.query(ContentAsset).options(selectinload(ContentAsset.fact_pack)).filter(ContentAsset.id == row.id).one()
    return _asset_out(row)


@router.patch("/content-assets/{asset_id}", response_model=ContentAssetOut)
def update_content_asset(
    asset_id: str,
    body: ContentAssetUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ContentAssetOut:
    row = db.get(ContentAsset, asset_id)
    if row is None or row.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="内容资产不存在")
    payload = body.model_dump(exclude_unset=True)
    if "asset_type" in payload and payload["asset_type"] not in ASSET_TYPES:
        raise HTTPException(status_code=400, detail="无效内容资产类型")
    if "status" in payload and payload["status"] not in ASSET_STATUSES:
        raise HTTPException(status_code=400, detail="无效内容资产状态")
    if payload.get("fact_pack_id"):
        fact = db.get(FactPack, payload["fact_pack_id"])
        if fact is None or fact.tenant_id != user.tenant_id:
            raise HTTPException(status_code=404, detail="事实包不存在")
    for field, value in payload.items():
        setattr(row, field, value or "")
    row.version += 1
    if row.status != "human_approved":
        row.approved_by = ""
        row.approved_at = None
    db.commit()
    row = db.query(ContentAsset).options(selectinload(ContentAsset.fact_pack)).filter(ContentAsset.id == row.id).one()
    return _asset_out(row)


@router.post("/content-assets/{asset_id}/ai-review", response_model=ContentAssetReviewOut)
def review_content_asset(
    asset_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ContentAssetReviewOut:
    row = (
        db.query(ContentAsset)
        .options(selectinload(ContentAsset.fact_pack))
        .filter(ContentAsset.id == asset_id, ContentAsset.tenant_id == user.tenant_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="内容资产不存在")
    status, findings = _review_asset(row, row.fact_pack)
    row.ai_review_status = status
    row.ai_review = "\n".join(findings) if findings else "规则初审通过：品牌、禁用词、认证和 NEED_INPUT 未发现阻断项。"
    row.status = "ai_reviewed"
    db.commit()
    db.refresh(row)
    return ContentAssetReviewOut(asset=_asset_out(row), findings=findings)


@router.post("/content-assets/{asset_id}/approve", response_model=ContentAssetOut)
def approve_content_asset(
    asset_id: str,
    body: ContentAssetApproveIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ContentAssetOut:
    if not body.confirmed:
        raise HTTPException(status_code=400, detail="批准内容资产需要人工确认")
    row = (
        db.query(ContentAsset)
        .options(selectinload(ContentAsset.fact_pack))
        .filter(ContentAsset.id == asset_id, ContentAsset.tenant_id == user.tenant_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="内容资产不存在")
    if row.fact_pack is None or row.fact_pack.status != "approved":
        raise HTTPException(status_code=400, detail="必须绑定已批准的客户基础资料")
    status, findings = _review_asset(row, row.fact_pack)
    if status != "pass":
        row.ai_review_status = status
        row.ai_review = "\n".join(findings)
        db.commit()
        raise HTTPException(status_code=400, detail="AI 初审未通过，不能人工批准")
    row.status = "human_approved"
    row.ai_review_status = "pass"
    row.ai_review = "规则初审通过：品牌、禁用词、认证和 NEED_INPUT 未发现阻断项。"
    row.human_review_note = body.note
    row.approved_by = user.email
    row.approved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return _asset_out(row)
