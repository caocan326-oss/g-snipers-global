"""Turn pasted customer materials into a Fact Pack draft. Do not invent specs."""

from __future__ import annotations

import re

from app.site_identity import is_lock_inquiry_text, is_lock_leftover_text

MIN_SOURCE = 20
URL_RE = re.compile(r"https?://[^\s<>\"']+", re.I)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
LEGAL_RE = re.compile(
    r"([A-Z][A-Za-z0-9&.\- ]{1,80}(?:Co\.,?\s*Ltd\.?|Limited|GmbH|Inc\.|Corp\.))",
    re.I,
)
CERT_RES = (
    re.compile(r"ISO\s*9001(?:\s*:\s*\d{4})?", re.I),
    re.compile(r"ISO\s*14001(?:\s*:\s*\d{4})?", re.I),
    re.compile(r"IATF\s*16949", re.I),
    re.compile(r"T[UÜ]V(?:\s+[A-Za-z]+)?", re.I),
    re.compile(r"\bRoHS\b", re.I),
)
CATEGORY_TERMS = (
    "fasteners",
    "fastener",
    "bolts",
    "bolt",
    "nuts",
    "nut",
    "screws",
    "screw",
    "washers",
    "washer",
    "pumps",
    "pump",
    "valves",
    "valve",
)
ICP_MARKERS = ("icp", "备案", "闽icp")
CITY_MARKERS = ("厦门", "成都", "xiamen", "chengdu")


def extract_fact_fields(source_text: str, *, site_origin: str = "") -> dict[str, object]:
    raw = (source_text or "").strip()
    if len(raw) < MIN_SOURCE:
        raise ValueError("资料太短。把客户给的英文说明或说明书原文贴进来。不要编。")
    if is_lock_leftover_text(raw) or is_lock_inquiry_text(raw):
        raise ValueError("这是门锁演示资料，不能记到这个客户。不要编。")

    notes: list[str] = []
    omitted: list[str] = []
    lower = raw.lower()

    website = ""
    urls = URL_RE.findall(raw)
    if urls:
        website = urls[0].rstrip(").,;")
    elif (site_origin or "").strip():
        website = site_origin.strip()
        notes.append("官网用已登记的客户站。没有打开页面核对。")
    else:
        omitted.append("官网")

    contact = ""
    emails = EMAIL_RE.findall(raw)
    if emails:
        contact = emails[0]

    certs: list[str] = []
    for pattern in CERT_RES:
        for hit in pattern.findall(raw):
            token = hit if isinstance(hit, str) else hit[0]
            token = re.sub(r"\s+", " ", token).strip()
            if token and token not in certs:
                certs.append(token)
    if any(mark in lower for mark in ICP_MARKERS):
        omitted.append("备案/闽ICP（不是认证）")
        notes.append("备案不是认证，没有写入认证栏。")

    categories = [term for term in CATEGORY_TERMS if re.search(rf"\b{re.escape(term)}\b", raw, re.I)]
    seen: set[str] = set()
    category_out: list[str] = []
    for term in categories:
        key = term.rstrip("s") if term.endswith("s") and term != "fasteners" else term
        if key in seen:
            continue
        seen.add(key)
        category_out.append(term)

    legal = ""
    legal_hit = LEGAL_RE.search(raw)
    if legal_hit:
        legal = re.sub(r"\s+", " ", legal_hit.group(1)).strip()
    brand = ""
    if legal:
        brand = re.split(r"\s+Co\.|,|\s+Limited|\s+GmbH|\s+Inc|\s+Corp", legal, maxsplit=1)[0].strip()

    boiler = _english_boilerplate(raw)
    if not boiler:
        omitted.append("已批英文简介")
        notes.append("资料里没有够长的英文句。中文不能当成已批英文。请客户给已批英文，或把已有英译文贴进来。不要编规格。")
    else:
        notes.append("英文简介只采用资料里已有的句子。没有补规格。")

    if any(mark in lower for mark in CITY_MARKERS) and boiler and not any(mark in boiler.lower() for mark in ("xiamen", "chengdu")):
        notes.append("资料里的城市名没有写进英文简介。页脚城市不要当公司简介。")

    specs = _spec_lines(raw)
    if not specs:
        omitted.append("规格")

    if not certs:
        omitted.append("认证")

    return {
        "legal_name": legal,
        "brand_names": brand,
        "website": website,
        "product_categories_en": ", ".join(category_out),
        "certifications": ", ".join(certs),
        "key_specs": specs,
        "contact_public": contact,
        "approved_boilerplate_en": boiler,
        "notes": notes,
        "omitted": [item for item in omitted if item],
    }


def _looks_english(text: str) -> bool:
    letters = [ch for ch in text if ch.isalpha()]
    if len(letters) < 16:
        return False
    ascii_letters = sum(1 for ch in letters if ch.isascii())
    return ascii_letters / len(letters) >= 0.75


def _english_boilerplate(text: str) -> str:
    blob = re.sub(r"[ \t]+", " ", text.replace("\r", "")).strip()
    parts = re.split(r"(?<=[.!?])\s+|\n+", blob)
    kept = [part.strip() for part in parts if _looks_english(part) and len(part.strip()) >= 20]
    if not kept and _looks_english(blob) and len(blob) >= 20:
        kept = [blob]
    joined = " ".join(kept[:4]).strip()
    return joined[:800]


def _spec_lines(text: str) -> str:
    lines = []
    for line in text.splitlines():
        raw = line.strip()
        if len(raw) < 4 or len(raw) > 120:
            continue
        if not re.search(r"\b(M\d+|grade\s*[0-9.]+|\d+\s*mm)\b", raw, re.I):
            continue
        if _looks_english(raw) or re.search(r"\bM\d+\b", raw):
            lines.append(raw)
        if len(lines) >= 2:
            break
    return " | ".join(lines)
