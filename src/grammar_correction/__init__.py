"""Grammar correction module using Ollama LLM and Pydantic."""

from src.grammar_correction.corrector import (
    SubtitleResponse,
    SubtitleSegment,
    correct_grammar,
)

__all__ = ["correct_grammar", "SubtitleSegment", "SubtitleResponse"]
