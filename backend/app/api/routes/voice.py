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

    # Simple intent matching
    if any(w in text for w in ["order", "new order", "create order"]):
        intent = "create_order"
        response = "Creating a new order. What items would you like to add?"
        confidence = 0.92
    elif any(w in text for w in ["table", "status", "tables"]):
        intent = "check_tables"
        response = "There are 8 occupied tables and 12 available."
        confidence = 0.88
    elif any(w in text for w in ["reservation", "book", "reserve"]):
        intent = "make_reservation"
        response = "I can help with a reservation. For how many guests?"
        confidence = 0.90
    elif any(w in text for w in ["menu", "item", "price"]):
        intent = "menu_query"
        response = "What menu item would you like to know about?"
        confidence = 0.85
    elif any(w in text for w in ["stock", "inventory", "check stock"]):
        intent = "check_inventory"
        response = "Checking inventory levels. There are 3 items below par level."
        confidence = 0.87
    elif any(w in text for w in ["bill", "check", "payment"]):
        intent = "process_payment"
        response = "Which table's bill would you like to process?"
        confidence = 0.91
    elif any(w in text for w in ["help", "what can you do"]):
        intent = "help"
        response = "I can help you with orders, tables, reservations, menu items, inventory, and payments."
        confidence = 0.95
    else:
        intent = "unknown"
        response = "I didn't understand that command. Try saying 'new order', 'check tables', or 'help'."
        confidence = 0.30

    return {
        "intent": intent,
        "confidence": confidence,
        "response": response,
    }
