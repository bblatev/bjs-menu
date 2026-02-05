"""Menu Complete API routes - Tags, Combos, Upsells, LTOs, 86'd Items, Digital Boards.

All data persisted to the integrations table using JSON config fields.
"""

from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.session import DbSession
from app.models.hardware import Integration

router = APIRouter(prefix="/menu-complete")

# Storage key constants
STORE_TAGS = "menu_tags"
STORE_COMBOS = "menu_combos"
STORE_UPSELL = "menu_upsell_rules"
STORE_LTO = "menu_limited_offers"
STORE_86 = "menu_86_items"
STORE_BOARDS = "menu_digital_boards"
STORE_VARIANTS = "menu_variants"


def _load(db, store_id: str) -> list:
    """Load a list from the integrations table."""
    rec = db.query(Integration).filter(Integration.integration_id == store_id).first()
    if rec and rec.config and isinstance(rec.config, dict):
        return rec.config.get("items", [])
    return []


def _save(db, store_id: str, items: list, name: str = ""):
    """Save a list to the integrations table."""
    rec = db.query(Integration).filter(Integration.integration_id == store_id).first()
    if not rec:
        rec = Integration(
            integration_id=store_id,
            name=name or store_id,
            category="menu",
            status="active",
            config={"items": items, "next_id": len(items) + 1},
        )
        db.add(rec)
    else:
        next_id = (rec.config or {}).get("next_id", len(items) + 1)
        rec.config = {"items": items, "next_id": next_id}
    db.commit()


def _next_id(db, store_id: str) -> int:
    """Get and increment the next ID for a store."""
    rec = db.query(Integration).filter(Integration.integration_id == store_id).first()
    if rec and rec.config:
        nid = rec.config.get("next_id", 1)
        rec.config = {**rec.config, "next_id": nid + 1}
        db.commit()
        return nid
    return 1


# ============ SCHEMAS ============

class MultiLang(BaseModel):
    bg: str = ""
    en: str = ""
    de: Optional[str] = None
    ru: Optional[str] = None


class MenuTag(BaseModel):
    id: Optional[int] = None
    name: MultiLang
    color: str = "#FF6B00"
    icon: Optional[str] = None
    is_active: bool = True


class MenuVariant(BaseModel):
    id: Optional[int] = None
    menu_item_id: int
    name: MultiLang
    variant_type: str = "size"
    price: float
    cost: Optional[float] = None
    sku: Optional[str] = None
    is_default: bool = False
    is_active: bool = True


class ComboItem(BaseModel):
    menu_item_id: int
    quantity: int = 1
    is_required: bool = True


class Combo(BaseModel):
    id: Optional[int] = None
    name: MultiLang
    description: Optional[MultiLang] = None
    pricing_type: str = "fixed"
    fixed_price: Optional[float] = None
    discount_percent: Optional[float] = None
    is_active: bool = True
    combo_items: List[ComboItem] = []


class UpsellRule(BaseModel):
    id: Optional[int] = None
    trigger_item_id: int
    upsell_item_id: int
    upsell_type: str = "suggestion"
    discount_percent: Optional[float] = None
    message: Optional[MultiLang] = None
    is_active: bool = True
    priority: int = 1


class LimitedTimeOffer(BaseModel):
    id: Optional[int] = None
    name: MultiLang
    description: Optional[MultiLang] = None
    offer_type: str = "discount"
    menu_item_id: Optional[int] = None
    discount_percent: Optional[float] = None
    fixed_price: Optional[float] = None
    start_date: str
    end_date: str
    is_active: bool = True


class Item86(BaseModel):
    id: Optional[int] = None
    menu_item_id: int
    reason: str = "out_of_stock"
    eighty_sixed_at: Optional[str] = None
    expected_return: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool = True


class DigitalBoard(BaseModel):
    id: Optional[int] = None
    name: str
    display_type: str = "menu"
    layout: str = "grid"
    location: Optional[str] = None
    is_active: bool = True


# ============ TAGS ============

@router.get("/tags", response_model=List[MenuTag])
def get_tags(db: DbSession):
    return _load(db, STORE_TAGS)


@router.post("/tags", response_model=MenuTag)
def create_tag(db: DbSession, tag: MenuTag):
    items = _load(db, STORE_TAGS)
    tag.id = _next_id(db, STORE_TAGS)
    items.append(tag.model_dump())
    _save(db, STORE_TAGS, items, "Menu Tags")
    return tag


@router.delete("/tags/{tag_id}")
def delete_tag(db: DbSession, tag_id: int):
    items = _load(db, STORE_TAGS)
    items = [t for t in items if t.get("id") != tag_id]
    _save(db, STORE_TAGS, items, "Menu Tags")
    return {"status": "deleted"}


# ============ VARIANTS ============

@router.get("/items/{item_id}/variants", response_model=List[MenuVariant])
def get_variants(db: DbSession, item_id: int):
    all_variants = _load(db, STORE_VARIANTS)
    return [v for v in all_variants if v.get("menu_item_id") == item_id]


@router.post("/items/{item_id}/variants", response_model=MenuVariant)
def create_variant(db: DbSession, item_id: int, variant: MenuVariant):
    items = _load(db, STORE_VARIANTS)
    variant.id = _next_id(db, STORE_VARIANTS)
    variant.menu_item_id = item_id
    items.append(variant.model_dump())
    _save(db, STORE_VARIANTS, items, "Menu Variants")
    return variant


# ============ COMBOS ============

@router.get("/combos", response_model=List[Combo])
def get_combos(db: DbSession):
    return _load(db, STORE_COMBOS)


@router.post("/combos", response_model=Combo)
def create_combo(db: DbSession, combo: Combo):
    items = _load(db, STORE_COMBOS)
    combo.id = _next_id(db, STORE_COMBOS)
    items.append(combo.model_dump())
    _save(db, STORE_COMBOS, items, "Menu Combos")
    return combo


@router.delete("/combos/{combo_id}")
def delete_combo(db: DbSession, combo_id: int):
    items = _load(db, STORE_COMBOS)
    items = [c for c in items if c.get("id") != combo_id]
    _save(db, STORE_COMBOS, items, "Menu Combos")
    return {"status": "deleted"}


# ============ UPSELL RULES ============

@router.get("/upsell-rules", response_model=List[UpsellRule])
def get_upsell_rules(db: DbSession):
    return _load(db, STORE_UPSELL)


@router.post("/upsell-rules", response_model=UpsellRule)
def create_upsell_rule(db: DbSession, rule: UpsellRule):
    items = _load(db, STORE_UPSELL)
    rule.id = _next_id(db, STORE_UPSELL)
    items.append(rule.model_dump())
    _save(db, STORE_UPSELL, items, "Upsell Rules")
    return rule


@router.delete("/upsell-rules/{rule_id}")
def delete_upsell_rule(db: DbSession, rule_id: int):
    items = _load(db, STORE_UPSELL)
    items = [r for r in items if r.get("id") != rule_id]
    _save(db, STORE_UPSELL, items, "Upsell Rules")
    return {"status": "deleted"}


# ============ LIMITED TIME OFFERS ============

@router.get("/limited-offers", response_model=List[LimitedTimeOffer])
def get_limited_offers(db: DbSession):
    return _load(db, STORE_LTO)


@router.post("/limited-offers", response_model=LimitedTimeOffer)
def create_limited_offer(db: DbSession, offer: LimitedTimeOffer):
    items = _load(db, STORE_LTO)
    offer.id = _next_id(db, STORE_LTO)
    items.append(offer.model_dump())
    _save(db, STORE_LTO, items, "Limited Time Offers")
    return offer


@router.delete("/limited-offers/{offer_id}")
def delete_limited_offer(db: DbSession, offer_id: int):
    items = _load(db, STORE_LTO)
    items = [o for o in items if o.get("id") != offer_id]
    _save(db, STORE_LTO, items, "Limited Time Offers")
    return {"status": "deleted"}


# ============ 86'd ITEMS ============

@router.get("/86", response_model=List[Item86])
def get_86_items(db: DbSession):
    items = _load(db, STORE_86)
    return [i for i in items if i.get("is_active", True)]


@router.post("/86", response_model=Item86)
def create_86_item(db: DbSession, item: Item86):
    items = _load(db, STORE_86)
    item.id = _next_id(db, STORE_86)
    item.eighty_sixed_at = datetime.now(timezone.utc).isoformat()
    items.append(item.model_dump())
    _save(db, STORE_86, items, "86'd Items")
    return item


@router.delete("/86/{item_id}")
def remove_86_item(db: DbSession, item_id: int):
    items = _load(db, STORE_86)
    for item in items:
        if item.get("id") == item_id:
            item["is_active"] = False
    _save(db, STORE_86, items, "86'd Items")
    return {"status": "restored"}


# ============ DIGITAL BOARDS ============

@router.get("/digital-boards", response_model=List[DigitalBoard])
def get_digital_boards(db: DbSession):
    return _load(db, STORE_BOARDS)


@router.post("/digital-boards", response_model=DigitalBoard)
def create_digital_board(db: DbSession, board: DigitalBoard):
    items = _load(db, STORE_BOARDS)
    board.id = _next_id(db, STORE_BOARDS)
    items.append(board.model_dump())
    _save(db, STORE_BOARDS, items, "Digital Boards")
    return board


@router.delete("/digital-boards/{board_id}")
def delete_digital_board(db: DbSession, board_id: int):
    items = _load(db, STORE_BOARDS)
    items = [b for b in items if b.get("id") != board_id]
    _save(db, STORE_BOARDS, items, "Digital Boards")
    return {"status": "deleted"}
