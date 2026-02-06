"""KDS Localization API routes.

Multilingual support for Kitchen Display Systems.
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.kds_localization_service import (
    get_kds_localization_service,
    SupportedLanguage,
)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class SetStationLanguageRequest(BaseModel):
    station_id: str
    language: str  # Language code (en, es, bg, fr, etc.)
    fallback_language: str = "en"


class AddTranslationRequest(BaseModel):
    key: str
    language: str
    text: str


class SetItemTranslationRequest(BaseModel):
    item_id: str
    language: str
    name: str


class SetModifierTranslationRequest(BaseModel):
    modifier_id: str
    language: str
    name: str


class BulkTranslationRequest(BaseModel):
    language: str
    translations: dict  # {key: text, ...}


class LocalizeOrderRequest(BaseModel):
    order: dict
    station_id: str


# ============================================================================
# Languages
# ============================================================================

@router.get("/languages")
async def list_supported_languages():
    """
    List all supported languages for KDS.

    Languages with has_translations=true have built-in translations.
    """
    service = get_kds_localization_service()

    languages = service.list_supported_languages()

    return {
        "languages": languages,
        "default": "en",
    }


# ============================================================================
# Station Language Settings
# ============================================================================

@router.get("/stations")
async def list_stations():
    """List all KDS stations with their language settings."""
    service = get_kds_localization_service()
    stations = service.list_station_languages()
    return {
        "stations": stations if stations else [
            {"station_id": "grill", "name": "Grill Station", "language": "en", "fallback_language": "en"},
            {"station_id": "fry", "name": "Fry Station", "language": "en", "fallback_language": "en"},
            {"station_id": "salad", "name": "Salad Station", "language": "bg", "fallback_language": "en"},
        ],
        "count": len(stations) if stations else 3,
    }


@router.post("/stations/language")
async def set_station_language(request: SetStationLanguageRequest):
    """
    Set the display language for a kitchen station.

    Each station can have its own language preference.
    """
    service = get_kds_localization_service()

    try:
        language = SupportedLanguage(request.language)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unsupported language: {request.language}")

    try:
        fallback = SupportedLanguage(request.fallback_language)
    except ValueError:
        fallback = SupportedLanguage.ENGLISH

    station_lang = service.set_station_language(
        request.station_id,
        language,
        fallback,
    )

    return {
        "success": True,
        "station_id": station_lang.station_id,
        "language": station_lang.language.value,
        "fallback_language": station_lang.fallback_language.value,
    }


@router.get("/stations/languages")
async def list_station_languages():
    """List language settings for all stations."""
    service = get_kds_localization_service()

    stations = service.list_station_languages()

    return {
        "stations": stations,
        "count": len(stations),
    }


@router.get("/stations/{station_id}/language")
async def get_station_language(station_id: str):
    """Get the language setting for a specific station."""
    service = get_kds_localization_service()

    language = service.get_station_language(station_id)

    return {
        "station_id": station_id,
        "language": language.value,
    }


# ============================================================================
# UI Labels
# ============================================================================

@router.get("/stations/{station_id}/ui-labels")
async def get_station_ui_labels(station_id: str):
    """
    Get all UI labels for a station in its configured language.

    Returns labels for buttons, headers, and other UI elements.
    """
    service = get_kds_localization_service()

    labels = service.get_ui_labels(station_id)
    language = service.get_station_language(station_id)

    return {
        "station_id": station_id,
        "language": language.value,
        "labels": labels,
    }


@router.get("/ui-labels/{language}")
async def get_ui_labels_by_language(language: str):
    """Get UI labels for a specific language."""
    service = get_kds_localization_service()

    try:
        lang = SupportedLanguage(language)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unsupported language: {language}")

    all_translations = service.get_all_translations(lang)

    # Filter to UI labels only
    labels = {
        key.replace("ui.", ""): text
        for key, text in all_translations.items()
        if key.startswith("ui.")
    }

    return {
        "language": language,
        "labels": labels,
    }


# ============================================================================
# Translations Management
# ============================================================================

@router.get("/translations/{language}")
async def get_translations(language: str):
    """Get all translations for a language."""
    service = get_kds_localization_service()

    try:
        lang = SupportedLanguage(language)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unsupported language: {language}")

    translations = service.get_all_translations(lang)

    return {
        "language": language,
        "translations": translations,
        "count": len(translations),
    }


@router.post("/translations")
async def add_translation(request: AddTranslationRequest):
    """Add or update a single translation."""
    service = get_kds_localization_service()

    try:
        language = SupportedLanguage(request.language)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unsupported language: {request.language}")

    service.add_translation(request.key, language, request.text)

    return {
        "success": True,
        "key": request.key,
        "language": request.language,
        "text": request.text,
    }


@router.post("/translations/bulk")
async def add_bulk_translations(request: BulkTranslationRequest):
    """Add multiple translations at once."""
    service = get_kds_localization_service()

    try:
        language = SupportedLanguage(request.language)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unsupported language: {request.language}")

    added = 0
    for key, text in request.translations.items():
        service.add_translation(key, language, text)
        added += 1

    return {
        "success": True,
        "language": request.language,
        "added": added,
    }


# ============================================================================
# Menu Item Translations
# ============================================================================

@router.post("/items/translation")
async def set_item_translation(request: SetItemTranslationRequest):
    """Set translation for a menu item."""
    service = get_kds_localization_service()

    try:
        language = SupportedLanguage(request.language)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unsupported language: {request.language}")

    service.set_item_translation(request.item_id, language, request.name)

    return {
        "success": True,
        "item_id": request.item_id,
        "language": request.language,
        "name": request.name,
    }


@router.post("/items/translations/bulk")
async def set_bulk_item_translations(items: List[SetItemTranslationRequest]):
    """Set translations for multiple menu items."""
    service = get_kds_localization_service()

    added = 0
    for item in items:
        try:
            language = SupportedLanguage(item.language)
            service.set_item_translation(item.item_id, language, item.name)
            added += 1
        except ValueError:
            continue

    return {
        "success": True,
        "added": added,
    }


# ============================================================================
# Modifier Translations
# ============================================================================

@router.post("/modifiers/translation")
async def set_modifier_translation(request: SetModifierTranslationRequest):
    """Set translation for a modifier."""
    service = get_kds_localization_service()

    try:
        language = SupportedLanguage(request.language)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unsupported language: {request.language}")

    service.set_modifier_translation(request.modifier_id, language, request.name)

    return {
        "success": True,
        "modifier_id": request.modifier_id,
        "language": request.language,
        "name": request.name,
    }


@router.post("/modifiers/translations/bulk")
async def set_bulk_modifier_translations(modifiers: List[SetModifierTranslationRequest]):
    """Set translations for multiple modifiers."""
    service = get_kds_localization_service()

    added = 0
    for mod in modifiers:
        try:
            language = SupportedLanguage(mod.language)
            service.set_modifier_translation(mod.modifier_id, language, mod.name)
            added += 1
        except ValueError:
            continue

    return {
        "success": True,
        "added": added,
    }


# ============================================================================
# Order Localization
# ============================================================================

@router.post("/localize-order")
async def localize_order(request: LocalizeOrderRequest):
    """
    Localize an order for display on a specific station.

    Translates item names, modifiers, status, and course information
    to the station's configured language.
    """
    service = get_kds_localization_service()

    localized = service.localize_order(request.order, request.station_id)
    language = service.get_station_language(request.station_id)

    return {
        "station_id": request.station_id,
        "language": language.value,
        "order": localized,
    }


# ============================================================================
# Translation Categories
# ============================================================================

@router.get("/categories")
async def get_translation_categories():
    """Get available translation categories."""
    return {
        "categories": [
            {
                "id": "status",
                "name": "Order Status",
                "description": "Status labels (new, cooking, ready, etc.)",
                "prefix": "status.",
            },
            {
                "id": "station",
                "name": "Stations",
                "description": "Kitchen station names",
                "prefix": "station.",
            },
            {
                "id": "ui",
                "name": "UI Elements",
                "description": "Buttons, headers, and interface labels",
                "prefix": "ui.",
            },
            {
                "id": "mod",
                "name": "Common Modifiers",
                "description": "Modifier prefixes (no, extra, light, etc.)",
                "prefix": "mod.",
            },
            {
                "id": "course",
                "name": "Courses",
                "description": "Course/timing names",
                "prefix": "course.",
            },
        ],
    }


@router.get("/categories/{category}/keys")
async def get_category_keys(category: str, language: str = "en"):
    """Get all translation keys for a category."""
    service = get_kds_localization_service()

    try:
        lang = SupportedLanguage(language)
    except ValueError:
        lang = SupportedLanguage.ENGLISH

    all_translations = service.get_all_translations(lang)
    prefix = f"{category}."

    keys = {
        key: text
        for key, text in all_translations.items()
        if key.startswith(prefix)
    }

    return {
        "category": category,
        "language": language,
        "keys": keys,
    }
