"""Grammar correction module using Ollama/Gemini LLMs and Pydantic."""

from src.grammar_correction.corrector import (
    SubtitleResponse,
    SubtitleSegment,
    correct_grammar,
)
from src.grammar_correction.llm_providers import (
    call_llm_provider,
    get_available_gemini_models,
)
from src.grammar_correction.prompts import build_system_prompt

__all__ = [
    "correct_grammar",
    "call_llm_provider",
    "get_available_gemini_models",
    "build_system_prompt",
    "SubtitleSegment",
    "SubtitleResponse",
]
