"""
Settings Schemas
Pydantic models for venue settings endpoints
"""
from pydantic import BaseModel, Field
from typing import Dict, Any
from datetime import datetime


class SettingsResponse(BaseModel):
    """Schema for settings response"""
    venue_id: int
    settings: Dict[str, Any] = Field(..., description="Flexible settings object")
    updated_at: datetime


class SettingsUpdate(BaseModel):
    """Schema for settings update"""
    settings: Dict[str, Any] = Field(..., description="Settings to update (deep merge)")


class TranslationRequest(BaseModel):
    """Schema for translation request"""
    text: str = Field(..., min_length=1, max_length=5000, description="Text to translate")
    source_language: str = Field(..., min_length=2, max_length=5, description="Source language code")
    target_language: str = Field(..., min_length=2, max_length=5, description="Target language code")


class TranslationResponse(BaseModel):
    """Schema for translation response"""
    source_text: str
    source_language: str
    target_language: str
    translated_text: str
    from_cache: bool = Field(..., description="Whether translation came from cache")
