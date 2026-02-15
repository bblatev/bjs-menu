"""
Fiscal Printer Management Routes

Provides endpoints for:
- Listing all NRA-approved fiscal printer manufacturers and models
- Searching/filtering the printer catalog
- Auto-detecting connected fiscal printers (USB/Serial/Network)
- Configuring a printer for use
"""

import json
import logging

from fastapi import APIRouter, Body, Request, Query
from typing import Optional

from app.db.session import DbSession
from app.models.operations import AppSetting
from app.core.rate_limit import limiter
from app.services.fiscal_device_registry import get_registry

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/manufacturers")
@limiter.limit("60/minute")
async def get_manufacturers(request: Request, db: DbSession):
    """
    Get all supported fiscal printer manufacturers.
    Returns manufacturer list with model counts from the NRA-approved registry.
    """
    registry = get_registry()
    return registry.get_manufacturers()


@router.get("/models")
@limiter.limit("60/minute")
async def get_models(
    request: Request,
    db: DbSession,
    manufacturer: Optional[str] = Query(None, description="Filter by manufacturer ID"),
    mobile_only: bool = Query(False, description="Only show mobile printers"),
    connection: Optional[str] = Query(None, description="Filter by connection type"),
    protocol: Optional[str] = Query(None, description="Filter by protocol"),
    q: Optional[str] = Query(None, description="Search query"),
):
    """
    Get fiscal printer models from the NRA-approved registry.
    Supports filtering by manufacturer, connection type, protocol, and mobility.
    """
    registry = get_registry()
    printers = registry.search_printers(
        query=q or "",
        manufacturer=manufacturer,
        mobile_only=mobile_only,
        connection_type=connection,
        protocol=protocol,
    )
    return [registry.printer_to_dict(p) for p in printers]


@router.get("/models/{model_id}")
@limiter.limit("60/minute")
async def get_model_detail(request: Request, db: DbSession, model_id: str):
    """Get detailed info for a specific printer model."""
    registry = get_registry()
    printer = registry.get_printer(model_id)
    if not printer:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Printer model '{model_id}' not found")
    return registry.printer_to_dict(printer)


@router.get("/connection-types")
@limiter.limit("60/minute")
async def get_connection_types(request: Request, db: DbSession):
    """Get all supported connection types for fiscal printers."""
    registry = get_registry()
    return registry.get_connection_types()


@router.get("/protocols")
@limiter.limit("60/minute")
async def get_protocols(request: Request, db: DbSession):
    """Get all supported fiscal printer communication protocols."""
    return [
        {
            "id": "isl",
            "name": "Datecs ISL",
            "description": "Information Systems Language - Datecs legacy protocol",
            "manufacturers": ["Datecs"],
        },
        {
            "id": "isl_new",
            "name": "Datecs ISL New (X-series)",
            "description": "ISL new generation for Datecs X-series printers. SUPTO compliant.",
            "manufacturers": ["Datecs"],
        },
        {
            "id": "zfp",
            "name": "Tremol ZFP",
            "description": "Zero Fiscal Protocol - Tremol legacy protocol",
            "manufacturers": ["Tremol"],
        },
        {
            "id": "zfp_v2",
            "name": "Tremol ZFP V2 (KL series)",
            "description": "ZFP version 2 for Tremol KL-V2 series. SUPTO compliant.",
            "manufacturers": ["Tremol"],
        },
        {
            "id": "daisy_isl",
            "name": "Daisy ISL",
            "description": "Daisy variant of the ISL protocol",
            "manufacturers": ["Daisy"],
        },
        {
            "id": "eltrade_isl",
            "name": "Eltrade ISL",
            "description": "Eltrade variant of the ISL protocol",
            "manufacturers": ["Eltrade"],
        },
        {
            "id": "incotex_isl",
            "name": "Incotex ISL",
            "description": "Incotex variant of the ISL protocol",
            "manufacturers": ["Incotex"],
        },
        {
            "id": "isl_5011",
            "name": "ISL 5011",
            "description": "ISL protocol for the 5011S-KL model",
            "manufacturers": ["ISL"],
        },
    ]


@router.get("/stats")
@limiter.limit("60/minute")
async def get_registry_stats(request: Request, db: DbSession):
    """Get registry statistics."""
    registry = get_registry()
    manufacturers = registry.get_manufacturers()
    all_printers = registry.get_all_printers()

    return {
        "total_models": registry.total_count,
        "total_manufacturers": len(manufacturers),
        "manufacturers": {m["name"]: m["printer_count"] for m in manufacturers},
        "mobile_count": sum(1 for p in all_printers if p.is_mobile),
        "desktop_count": sum(1 for p in all_printers if not p.is_mobile),
        "with_cutter": sum(1 for p in all_printers if p.has_cutter),
        "with_pinpad": sum(1 for p in all_printers if p.has_pinpad),
        "protocols": list(set(p.protocol.value for p in all_printers)),
    }


@router.post("/detect")
@limiter.limit("10/minute")
async def detect_printers(request: Request, db: DbSession):
    """
    Auto-detect connected fiscal printers.

    Scans:
    - USB devices (matching VID:PID against NRA registry)
    - Serial ports (probing for fiscal printer protocol responses)
    - Network services (FPGate, ErpNet.FP on localhost)

    Returns detected devices with confidence scores and matched printer models.
    """
    try:
        from app.services.fiscal_auto_detect import get_auto_detect_service
        service = get_auto_detect_service()
        result = await service.detect_all()
        return result
    except Exception as e:
        logger.error(f"Auto-detection failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "devices": [],
            "total_detected": 0,
        }


@router.post("/configure")
@limiter.limit("30/minute")
async def configure_printer(request: Request, db: DbSession, config: dict = Body(...)):
    """
    Configure a fiscal printer for use.
    Saves the configuration (model, connection, credentials) to the database.
    """
    # Save to AppSetting
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

    # If a model_id is provided, validate it exists in registry
    model_id = config.get("model_id")
    if model_id:
        registry = get_registry()
        printer = registry.get_printer(model_id)
        if printer:
            return {
                "success": True,
                "message": f"Printer {printer.name} configured successfully",
                "model": registry.printer_to_dict(printer),
            }

    return {"success": True, "message": "Printer configured"}


@router.get("/current-config")
@limiter.limit("60/minute")
async def get_current_config(request: Request, db: DbSession):
    """Get the current fiscal printer configuration."""
    setting = db.query(AppSetting).filter(
        AppSetting.category == "fiscal_printers",
        AppSetting.key == "printer_config",
    ).first()

    if setting and setting.value:
        config = json.loads(setting.value) if isinstance(setting.value, str) else setting.value

        # Enrich with registry data if model_id present
        model_id = config.get("model_id")
        if model_id:
            registry = get_registry()
            printer = registry.get_printer(model_id)
            if printer:
                config["model_info"] = registry.printer_to_dict(printer)

        return {"success": True, "config": config}

    return {"success": True, "config": None, "message": "No printer configured"}
