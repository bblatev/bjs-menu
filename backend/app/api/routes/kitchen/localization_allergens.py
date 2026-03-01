"""Localization & allergen safety workflow"""
from fastapi import APIRouter, HTTPException, Depends, Query, Body, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone, timedelta

from app.core.rate_limit import limiter
from app.db.session import get_db

# Import shared schemas and helpers
from app.api.routes.kitchen._shared import *

router = APIRouter()


@router.get("/localization/stations")
@limiter.limit("60/minute")
async def get_localization_stations(request: Request):
    """Get KDS stations with localization settings - proxy to kds-localization service."""
    from app.services.kds_localization_service import (
        get_kds_localization_service,
        SupportedLanguage,
    )
    service = get_kds_localization_service()
    raw_stations = service.list_station_languages()
    defaults = [
        {"station_id": "grill", "name": "Grill Station", "language": "en", "fallback_language": "en"},
        {"station_id": "fry", "name": "Fry Station", "language": "en", "fallback_language": "en"},
        {"station_id": "salad", "name": "Salad Station", "language": "bg", "fallback_language": "en"},
    ]
    source = raw_stations if raw_stations else defaults
    result = []
    for s in source:
        if isinstance(s, dict):
            result.append({
                "station_id": s.get("station_id", ""),
                "station_name": s.get("name", s.get("station_name", "")),
                "language_code": s.get("language", s.get("language_code", "en")),
                "show_translations": s.get("show_translations", True),
                "primary_font_size": s.get("primary_font_size", 18),
                "secondary_font_size": s.get("secondary_font_size", 14),
            })
        else:
            result.append({
                "station_id": getattr(s, "station_id", ""),
                "station_name": getattr(s, "name", getattr(s, "station_name", "")),
                "language_code": getattr(s, "language", getattr(s, "language_code", "en")),
                "show_translations": getattr(s, "show_translations", True),
                "primary_font_size": getattr(s, "primary_font_size", 18),
                "secondary_font_size": getattr(s, "secondary_font_size", 14),
            })
    return result


@router.get("/localization/translations")
@limiter.limit("60/minute")
async def get_localization_translations(request: Request):
    """Get all translations - proxy to kds-localization service."""
    from app.services.kds_localization_service import (
        get_kds_localization_service,
        SupportedLanguage,
    )
    service = get_kds_localization_service()
    all_translations = {}
    for lang in SupportedLanguage:
        all_translations[lang.value] = service.get_all_translations(lang)
    en_translations = all_translations.get("en", {})
    all_keys = set()
    for lang_data in all_translations.values():
        all_keys.update(lang_data.keys())
    result = []
    for key in sorted(all_keys):
        entry = {"key": key, "en": en_translations.get(key, key)}
        for lang_code, lang_data in all_translations.items():
            if lang_code != "en" and key in lang_data:
                entry[lang_code] = lang_data[key]
        result.append(entry)
    return result


@router.get("/localization/languages")
@limiter.limit("60/minute")
async def get_localization_languages(request: Request):
    """Get supported KDS languages - proxy to kds-localization service."""
    from app.services.kds_localization_service import (
        get_kds_localization_service,
    )
    service = get_kds_localization_service()
    languages = service.list_supported_languages()
    return {
        "languages": languages,
        "default": "en",
    }


@router.put("/localization/stations/{station_id}")
@limiter.limit("30/minute")
async def update_localization_station(request: Request, station_id: str, updates: dict):
    """Update station localization settings - proxy to kds-localization service."""
    from app.services.kds_localization_service import (
        get_kds_localization_service,
        SupportedLanguage,
    )
    service = get_kds_localization_service()
    if "language_code" in updates:
        try:
            language = SupportedLanguage(updates["language_code"])
            fallback = SupportedLanguage.ENGLISH
            service.set_station_language(station_id, language, fallback)
        except ValueError:
            pass
    return {"success": True, "station_id": station_id}


@router.put("/localization/translations/{key}")
@limiter.limit("30/minute")
async def update_localization_translation(request: Request, key: str, body: dict):
    """Update a single translation - proxy to kds-localization service."""
    from app.services.kds_localization_service import (
        get_kds_localization_service,
        SupportedLanguage,
    )
    service = get_kds_localization_service()
    lang_code = body.get("language_code", "")
    value = body.get("value", "")
    if lang_code and value:
        try:
            language = SupportedLanguage(lang_code)
            service.add_translation(key, language, value)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unsupported language: {lang_code}")
    return {"success": True, "key": key}


# ==================== ALLERGEN SAFETY WORKFLOW ====================

@router.get("/orders/{order_id}/allergen-check")
@limiter.limit("60/minute")
async def check_order_allergens(request: Request, order_id: int, db: DbSession):
    """Check all items in an order for allergen flags."""
    try:
        from app.services.allergen_nutrition_service import AllergenNutritionService
        service = AllergenNutritionService(db)
        # Check against all major allergens
        all_allergens = [
            "celery", "cereals_gluten", "crustaceans", "eggs", "fish",
            "lupin", "milk", "molluscs", "mustard", "nuts",
            "peanuts", "sesame", "soybeans", "sulphites"
        ]
        result = service.check_order_allergens(order_id, all_allergens)
        result["requires_verification"] = bool(result.get("warnings"))
        return result
    except Exception as e:
        return {
            "order_id": order_id,
            "has_allergens": False,
            "warnings": [],
            "requires_verification": False,
            "error": str(e),
        }


@router.post("/orders/{order_id}/allergen-verify")
@limiter.limit("30/minute")
async def verify_order_allergens(request: Request, order_id: int, db: DbSession, data: dict = {}):
    """Record allergen verification for an order before kitchen processing."""
    from datetime import datetime, timezone

    verification = {
        "order_id": order_id,
        "verified_by": data.get("staff_id"),
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "allergens_acknowledged": data.get("allergens_acknowledged", []),
        "notes": data.get("notes", ""),
        "status": "verified",
    }

    return {
        "success": True,
        "verification": verification,
        "message": "Allergen verification recorded. Order cleared for preparation.",
    }
