import json
import logging
from pydantic import BaseModel
import ollama

logger = logging.getLogger(__name__)


class SubtitleSegment(BaseModel):
    id: int
    text: str


class SubtitleResponse(BaseModel):
    segments: list[SubtitleSegment]


def correct_grammar(
    segments: list[dict[str, float | int | str]],
    model_name: str = "llama3.1",
) -> list[dict[str, float | int | str]]:
    """Correct the grammar of subtitle text segments using Ollama LLM.

    Args:
        segments: List of segment dictionaries with keys 'id', 'start', 'end', 'text'.
        model_name: Ollama LLM model name to use for grammar correction.

    Returns:
        A list of segment dictionaries with updated 'text' fields.
    """
    if not segments:
        return []

    # Map original text by ID for safe fallback
    corrected_map: dict[int, str] = {
        int(seg["id"]): str(seg["text"]) for seg in segments
    }

    batch_size = 40
    for i in range(0, len(segments), batch_size):
        batch = segments[i : i + batch_size]
        payload = [
            {"id": int(seg["id"]), "text": str(seg["text"])} for seg in batch
        ]

        try:
            prompt_system = (
                "You are a subtitle editor. Correct grammar. "
                "DO NOT change IDs. Keep the exact same number of segments."
            )
            messages = [
                {"role": "system", "content": prompt_system},
                {"role": "user", "content": json.dumps(payload)},
            ]

            response = ollama.chat(
                model=model_name,
                format=SubtitleResponse.model_json_schema(),
                messages=messages,
            )

            content = ""
            if hasattr(response, "message") and hasattr(response.message, "content"):
                content = response.message.content
            elif isinstance(response, dict):
                content = response.get("message", {}).get("content", "")

            if content:
                parsed_response = SubtitleResponse.model_validate_json(content)
                for item in parsed_response.segments:
                    corrected_map[item.id] = item.text
            else:
                logger.warning(
                    f"Ollama returned empty content for batch starting at index {i}."
                )

        except Exception as e:
            logger.warning(
                f"Grammar correction failed for batch starting at index {i}: {e}. "
                "Falling back to original segment text."
            )

    result: list[dict[str, float | int | str]] = []
    for seg in segments:
        updated_seg = dict(seg)
        seg_id = int(seg["id"])
        updated_seg["text"] = corrected_map.get(seg_id, str(seg["text"]))
        result.append(updated_seg)

    return result
