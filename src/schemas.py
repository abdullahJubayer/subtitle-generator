"""Shared Pydantic data schemas and type aliases for Subtitle Generator pipeline."""

from typing import Any, Literal, TypedDict
from pydantic import BaseModel, Field

# Type Aliases
WhisperModelSize = Literal["tiny", "base", "small", "medium", "large"]

class SegmentDict(TypedDict):
    """Standardized dictionary layout passed between pipeline modules."""
    id: int
    start: float
    end: float
    text: str


class SubtitleSegment(BaseModel):
    """Pydantic schema for individual subtitle segment."""
    id: int = Field(..., description="1-indexed segment identifier")
    text: str = Field(..., description="Subtitle text content")


class SubtitleResponse(BaseModel):
    """Pydantic schema for structured LLM response."""
    segments: list[SubtitleSegment]
