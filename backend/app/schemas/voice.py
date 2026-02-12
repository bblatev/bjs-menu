"""
Voice Assistant Schemas
Pydantic models for voice command endpoints
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime


class VoiceCommandRequest(BaseModel):
    """Schema for voice command request"""
    command_text: str = Field(..., min_length=1, max_length=500, description="Voice command text")
    language: Optional[str] = Field("bg", description="Language code (bg, en, de, ru)")


class VoiceCommandResponse(BaseModel):
    """Schema for voice command response"""
    success: bool
    intent: str = Field(..., description="Detected intent")
    entities: Dict[str, Any] = Field(default_factory=dict, description="Extracted entities")
    response: str = Field(..., description="Human-readable response")
    action_performed: Optional[str] = Field(None, description="Action that was performed")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confidence score")
    execution_time_ms: int = Field(..., description="Execution time in milliseconds")


class VoiceIntentResponse(BaseModel):
    """Schema for voice intent information"""
    intent: str
    description: str
    examples: list[str]
    required_entities: list[str]


class TranscribeResponse(BaseModel):
    """Schema for audio transcription response"""
    success: bool
    text: str = Field(..., description="Transcribed text")
    language: str = Field(..., description="Detected language")
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    duration: Optional[float] = Field(None, description="Audio duration in seconds")


class VoiceHistoryResponse(BaseModel):
    """Schema for voice command history"""
    id: int
    staff_user_id: int
    command_text: str
    intent: str
    entities: Optional[Dict[str, Any]]
    success: bool
    error_message: Optional[str]
    execution_time_ms: Optional[int]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
