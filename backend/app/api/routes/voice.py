"""Voice Assistant API routes.

Handles voice command processing with DB-backed intent resolution.
"""

from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import func

from app.db.session import DbSession
from app.models.restaurant import MenuItem, Table
from app.models.stock import StockOnHand
from app.models.product import Product
from app.core.rate_limit import limiter

router = APIRouter()


class VoiceCommandRequest(BaseModel):
    command_text: str
    language: str = "en"


def _resolve_intent(text: str) -> str:
    """Determine intent from command text using keyword matching."""
    text = text.lower()
    if any(w in text for w in ["order", "new order", "create order"]):
        return "create_order"
    if any(w in text for w in ["table", "status", "tables"]):
        return "check_tables"
    if any(w in text for w in ["reservation", "book", "reserve"]):
        return "make_reservation"
    if any(w in text for w in ["menu", "item", "price"]):
        return "menu_query"
    if any(w in text for w in ["stock", "inventory", "check stock"]):
        return "check_inventory"
    if any(w in text for w in ["bill", "check", "payment"]):
        return "process_payment"
    if any(w in text for w in ["help", "what can you do"]):
        return "help"
    return "unknown"


def _handle_check_tables(db: DbSession) -> dict:
    """Query the Table model for real availability data."""
    tables = db.query(Table).all()
    total = len(tables)
    available = sum(1 for t in tables if t.status == "available")
    occupied = sum(1 for t in tables if t.status == "occupied")
    reserved = sum(1 for t in tables if t.status == "reserved")

    available_numbers = [t.number for t in tables if t.status == "available"]
    summary = f"{available} of {total} tables available."
    if available_numbers:
        summary += f" Free: {', '.join(available_numbers[:5])}"
        if len(available_numbers) > 5:
            summary += f" (+{len(available_numbers) - 5} more)"

    return {
        "response": summary,
        "data": {
            "total": total,
            "available": available,
            "occupied": occupied,
            "reserved": reserved,
            "available_tables": available_numbers,
        },
    }


def _handle_check_inventory(db: DbSession) -> dict:
    """Query StockOnHand joined with Product for low-stock items."""
    low_stock = (
        db.query(StockOnHand, Product)
        .join(Product, StockOnHand.product_id == Product.id)
        .filter(
            Product.active == True,
            Product.min_stock.isnot(None),
            StockOnHand.qty <= Product.min_stock,
        )
        .order_by(StockOnHand.qty.asc())
        .limit(10)
        .all()
    )

    if not low_stock:
        return {
            "response": "All items are above minimum stock levels.",
            "data": {"low_stock_count": 0, "items": []},
        }

    items = []
    for soh, prod in low_stock:
        items.append({
            "product_id": prod.id,
            "name": prod.name,
            "qty": float(soh.qty),
            "min_stock": float(prod.min_stock) if prod.min_stock else None,
            "unit": prod.unit,
        })

    summary = f"{len(items)} item(s) at or below minimum stock."
    top_items = ", ".join(f"{i['name']} ({i['qty']} {i['unit'] or ''})" for i in items[:3])
    summary += f" Low: {top_items}"

    return {
        "response": summary,
        "data": {"low_stock_count": len(items), "items": items},
    }


def _handle_menu_query(db: DbSession, text: str) -> dict:
    """Search MenuItem by name and return price/category info."""
    # Extract search terms (remove common intent words)
    stop_words = {"menu", "item", "price", "what", "is", "the", "how", "much", "does", "cost", "about", "tell", "me", "show"}
    words = [w for w in text.lower().split() if w not in stop_words]
    search_term = " ".join(words).strip()

    if not search_term:
        # Return popular items
        items = db.query(MenuItem).filter(
            MenuItem.available == True,
            MenuItem.not_deleted(),
        ).limit(5).all()
        return {
            "response": "Here are some menu items. What would you like to know about?",
            "data": {
                "items": [
                    {"id": i.id, "name": i.name, "price": float(i.price), "category": i.category}
                    for i in items
                ],
            },
        }

    # Search by name
    results = db.query(MenuItem).filter(
        MenuItem.name.ilike(f"%{search_term}%"),
        MenuItem.not_deleted(),
    ).limit(5).all()

    if not results:
        return {
            "response": f"No menu items found matching '{search_term}'.",
            "data": {"items": [], "search_term": search_term},
        }

    items_data = []
    for item in results:
        items_data.append({
            "id": item.id,
            "name": item.name,
            "price": float(item.price),
            "category": item.category,
            "available": item.available,
            "allergens": item.allergens or [],
        })

    if len(results) == 1:
        i = items_data[0]
        response = f"{i['name']} - ${i['price']:.2f} ({i['category']})"
        if not i["available"]:
            response += " [currently unavailable]"
    else:
        response = f"Found {len(results)} items matching '{search_term}': "
        response += ", ".join(f"{i['name']} (${i['price']:.2f})" for i in items_data)

    return {
        "response": response,
        "data": {"items": items_data, "search_term": search_term},
    }


@router.get("/")
@limiter.limit("60/minute")
def get_voice_root(request: Request, db: DbSession):
    """Voice assistant service status."""
    return {"module": "voice", "status": "active", "supported_intents": ["create_order", "check_tables", "make_reservation", "menu_query", "check_inventory", "process_payment"], "endpoint": "/command"}


@router.post("/command")
@limiter.limit("30/minute")
async def process_voice_command(request: Request, body: VoiceCommandRequest, db: DbSession):
    """Process a voice command and return intent + response with real DB data."""
    text = body.command_text
    intent = _resolve_intent(text)

    if intent == "check_tables":
        result = _handle_check_tables(db)
    elif intent == "check_inventory":
        result = _handle_check_inventory(db)
    elif intent == "menu_query":
        result = _handle_menu_query(db, text)
    elif intent == "create_order":
        result = {
            "response": "Creating a new order. What items would you like to add?",
            "data": None,
        }
    elif intent == "make_reservation":
        result = {
            "response": "I can help with a reservation. For how many guests?",
            "data": None,
        }
    elif intent == "process_payment":
        result = {
            "response": "Which table's bill would you like to process?",
            "data": None,
        }
    elif intent == "help":
        result = {
            "response": "I can help you with: checking tables, inventory levels, menu prices, orders, reservations, and payments.",
            "data": None,
        }
    else:
        result = {
            "response": "I didn't understand that command. Try saying 'check tables', 'inventory', 'menu pizza', or 'help'.",
            "data": None,
        }

    return {
        "intent": intent,
        "confidence": 1.0 if intent != "unknown" else 0.0,
        "response": result["response"],
        "data": result.get("data"),
    }
