"""Voice Assistant API routes.

Handles voice command processing for the voice control page.
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class VoiceCommandRequest(BaseModel):
    command_text: str
    language: str = "en"


@router.post("/command")
async def process_voice_command(request: VoiceCommandRequest):
    """Process a voice command and return intent + response."""
    text = request.command_text.lower()

    # Simple keyword-based intent matching
    if any(w in text for w in ["order", "new order", "create order"]):
        intent = "create_order"
        response = "Creating a new order. What items would you like to add?"
    elif any(w in text for w in ["table", "status", "tables"]):
        intent = "check_tables"
        response = "Checking table status."
    elif any(w in text for w in ["reservation", "book", "reserve"]):
        intent = "make_reservation"
        response = "I can help with a reservation. For how many guests?"
    elif any(w in text for w in ["menu", "item", "price"]):
        intent = "menu_query"
        response = "What menu item would you like to know about?"
    elif any(w in text for w in ["stock", "inventory", "check stock"]):
        intent = "check_inventory"
        response = "Checking inventory levels."
    elif any(w in text for w in ["bill", "check", "payment"]):
        intent = "process_payment"
        response = "Which table's bill would you like to process?"
    elif any(w in text for w in ["help", "what can you do"]):
        intent = "help"
        response = "I can help you with orders, tables, reservations, menu items, inventory, and payments."
    else:
        intent = "unknown"
        response = "I didn't understand that command. Try saying 'new order', 'check tables', or 'help'."

    return {
        "intent": intent,
        "confidence": 1.0 if intent != "unknown" else 0.0,
        "response": response,
    }
