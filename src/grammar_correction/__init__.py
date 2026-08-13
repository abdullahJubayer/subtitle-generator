"""Grammar correction module using Ollama LLM and Pydantic."""

from src.grammar_correction.corrector import (
    SubtitleResponse,
    SubtitleSegment,
    correct_grammar,
)
from src.grammar_correction.prompts import build_system_prompt

__all__ = ["correct_grammar", "build_system_prompt", "SubtitleSegment", "SubtitleResponse"]
