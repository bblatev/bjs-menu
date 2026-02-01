"""Menu Complete API routes - Tags, Combos, Upsells, LTOs, 86'd Items, Digital Boards."""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

router = APIRouter(prefix="/menu-complete")

# In-memory storage (replace with database in production)
_tags_db = []
_combos_db = []
_upsell_rules_db = []
_limited_offers_db = []
_items_86_db = []
_digital_boards_db = []
_variants_db = {}

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
async def get_tags():
    return _tags_db

@router.post("/tags", response_model=MenuTag)
async def create_tag(tag: MenuTag):
    tag.id = len(_tags_db) + 1
    _tags_db.append(tag.model_dump())
    return tag

@router.delete("/tags/{tag_id}")
async def delete_tag(tag_id: int):
    global _tags_db
    _tags_db = [t for t in _tags_db if t.get("id") != tag_id]
    return {"status": "deleted"}

# ============ VARIANTS ============

@router.get("/items/{item_id}/variants", response_model=List[MenuVariant])
async def get_variants(item_id: int):
    return _variants_db.get(item_id, [])

@router.post("/items/{item_id}/variants", response_model=MenuVariant)
async def create_variant(item_id: int, variant: MenuVariant):
    if item_id not in _variants_db:
        _variants_db[item_id] = []
    variant.id = len(_variants_db[item_id]) + 1
    variant.menu_item_id = item_id
    _variants_db[item_id].append(variant.model_dump())
    return variant

# ============ COMBOS ============

@router.get("/combos", response_model=List[Combo])
async def get_combos():
    return _combos_db

@router.post("/combos", response_model=Combo)
async def create_combo(combo: Combo):
    combo.id = len(_combos_db) + 1
    _combos_db.append(combo.model_dump())
    return combo

@router.delete("/combos/{combo_id}")
async def delete_combo(combo_id: int):
    global _combos_db
    _combos_db = [c for c in _combos_db if c.get("id") != combo_id]
    return {"status": "deleted"}

# ============ UPSELL RULES ============

@router.get("/upsell-rules", response_model=List[UpsellRule])
async def get_upsell_rules():
    return _upsell_rules_db

@router.post("/upsell-rules", response_model=UpsellRule)
async def create_upsell_rule(rule: UpsellRule):
    rule.id = len(_upsell_rules_db) + 1
    _upsell_rules_db.append(rule.model_dump())
    return rule

@router.delete("/upsell-rules/{rule_id}")
async def delete_upsell_rule(rule_id: int):
    global _upsell_rules_db
    _upsell_rules_db = [r for r in _upsell_rules_db if r.get("id") != rule_id]
    return {"status": "deleted"}

# ============ LIMITED TIME OFFERS ============

@router.get("/limited-offers", response_model=List[LimitedTimeOffer])
async def get_limited_offers():
    return _limited_offers_db

@router.post("/limited-offers", response_model=LimitedTimeOffer)
async def create_limited_offer(offer: LimitedTimeOffer):
    offer.id = len(_limited_offers_db) + 1
    _limited_offers_db.append(offer.model_dump())
    return offer

@router.delete("/limited-offers/{offer_id}")
async def delete_limited_offer(offer_id: int):
    global _limited_offers_db
    _limited_offers_db = [o for o in _limited_offers_db if o.get("id") != offer_id]
    return {"status": "deleted"}

# ============ 86'd ITEMS ============

@router.get("/86", response_model=List[Item86])
async def get_86_items():
    return [i for i in _items_86_db if i.get("is_active", True)]

@router.post("/86", response_model=Item86)
async def create_86_item(item: Item86):
    item.id = len(_items_86_db) + 1
    item.eighty_sixed_at = datetime.utcnow().isoformat()
    _items_86_db.append(item.model_dump())
    return item

@router.delete("/86/{item_id}")
async def remove_86_item(item_id: int):
    global _items_86_db
    for item in _items_86_db:
        if item.get("id") == item_id:
            item["is_active"] = False
    return {"status": "restored"}

# ============ DIGITAL BOARDS ============

@router.get("/digital-boards", response_model=List[DigitalBoard])
async def get_digital_boards():
    return _digital_boards_db

@router.post("/digital-boards", response_model=DigitalBoard)
async def create_digital_board(board: DigitalBoard):
    board.id = len(_digital_boards_db) + 1
    _digital_boards_db.append(board.model_dump())
    return board

@router.delete("/digital-boards/{board_id}")
async def delete_digital_board(board_id: int):
    global _digital_boards_db
    _digital_boards_db = [b for b in _digital_boards_db if b.get("id") != board_id]
    return {"status": "deleted"}
