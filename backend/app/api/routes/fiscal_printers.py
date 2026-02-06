"""Fiscal printer management routes."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/manufacturers")
async def get_manufacturers():
    """Get supported fiscal printer manufacturers."""
    return [
        {"id": "datecs", "name": "Datecs", "country": "BG", "models_count": 5},
        {"id": "tremol", "name": "Tremol", "country": "BG", "models_count": 3},
        {"id": "daisy", "name": "Daisy", "country": "BG", "models_count": 4},
        {"id": "eltrade", "name": "Eltrade", "country": "BG", "models_count": 2},
    ]


@router.get("/models")
async def get_models(manufacturer: str = None):
    """Get fiscal printer models."""
    return [
        {"id": "dp25", "manufacturer": "datecs", "name": "Datecs DP-25", "connection": "serial", "nra_certified": True},
        {"id": "dp55", "manufacturer": "datecs", "name": "Datecs DP-55", "connection": "lan", "nra_certified": True},
        {"id": "fp700", "manufacturer": "tremol", "name": "Tremol FP700", "connection": "usb", "nra_certified": True},
        {"id": "compact_s", "manufacturer": "daisy", "name": "Daisy Compact S", "connection": "serial", "nra_certified": True},
    ]


@router.get("/connection-types")
async def get_connection_types():
    """Get supported connection types."""
    return [
        {"id": "serial", "name": "Serial (COM)", "description": "RS-232 serial connection"},
        {"id": "usb", "name": "USB", "description": "USB connection"},
        {"id": "lan", "name": "LAN/Ethernet", "description": "Network connection"},
        {"id": "bluetooth", "name": "Bluetooth", "description": "Wireless Bluetooth"},
    ]


@router.post("/configure")
async def configure_printer(config: dict):
    """Configure a fiscal printer."""
    return {"success": True, "message": "Printer configured"}
