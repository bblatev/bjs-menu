"""Fiscal printer management routes."""

import json

from fastapi import APIRouter, Body

from app.db.session import DbSession
from app.models.operations import AppSetting

router = APIRouter()


@router.get("/manufacturers")
async def get_manufacturers(db: DbSession):
    """Get supported fiscal printer manufacturers."""
    setting = db.query(AppSetting).filter(
        AppSetting.category == "fiscal_printers",
        AppSetting.key == "manufacturers",
    ).first()

    if setting and setting.value:
        return json.loads(setting.value)

    return []


@router.get("/models")
async def get_models(db: DbSession, manufacturer: str = None):
    """Get fiscal printer models."""
    setting = db.query(AppSetting).filter(
        AppSetting.category == "fiscal_printers",
        AppSetting.key == "models",
    ).first()

    if setting and setting.value:
        models = json.loads(setting.value)
        if manufacturer:
            models = [m for m in models if m.get("manufacturer") == manufacturer]
        return models

    return []


@router.get("/connection-types")
async def get_connection_types(db: DbSession):
    """Get supported connection types."""
    setting = db.query(AppSetting).filter(
        AppSetting.category == "fiscal_printers",
        AppSetting.key == "connection_types",
    ).first()

    if setting and setting.value:
        return json.loads(setting.value)

    return []


@router.post("/configure")
async def configure_printer(db: DbSession, config: dict = Body(...)):
    """Configure a fiscal printer."""
    setting = db.query(AppSetting).filter(
        AppSetting.category == "fiscal_printers",
        AppSetting.key == "printer_config",
    ).first()

    if setting:
        setting.value = json.dumps(config)
    else:
        setting = AppSetting(
            category="fiscal_printers",
            key="printer_config",
            value=json.dumps(config),
        )
        db.add(setting)

    db.commit()
    return {"success": True, "message": "Printer configured"}
