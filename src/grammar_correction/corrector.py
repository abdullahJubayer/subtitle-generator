import json
import logging
import ollama
from src.schemas import SegmentDict, SubtitleResponse, SubtitleSegment

logger = logging.getLogger(__name__)


def correct_grammar(
    segments: list[SegmentDict],
    model_name: str = "llama3.2:3b",
    target_language: str = "English",
) -> list[SegmentDict]:
    """Correct the grammar of subtitle text segments or translate them using Ollama LLM.

    Args:
        segments: List of segment dictionaries with keys 'id', 'start', 'end', 'text'.
        model_name: Ollama LLM model name to use for grammar correction/translation.
        target_language: Target language for translation/correction (default "English").

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
            if target_language.lower() != "english":
                prompt_system = (
                    f"You are an expert translator and subtitle editor. Translate and adapt the subtitle text into fluent, natural, idiomatically accurate {target_language}. DO NOT change IDs. Keep the exact same number of segments."
                )
            else:
                prompt_system = (
                    "You are a subtitle editor. Correct grammar. "
                    "DO NOT change IDs. Keep the exact same number of segments."
                )
            messages = [
                {"role": "system", "content": prompt_system},
                {"role": "user", "content": json.dumps(payload)},
            ]

            # Auto-detect available local model if specified model fails or is missing
            try:
                response = ollama.chat(
                    model=model_name,
                    format=SubtitleResponse.model_json_schema(),
                    messages=messages,
                )
            except ollama.ResponseError as err:
                if err.status_code == 404:
                    available = ollama.list()
                    models_list = getattr(available, "models", []) or available.get("models", [])
                    if models_list:
                        first_model = models_list[0].model if hasattr(models_list[0], "model") else models_list[0].get("name", "")
                        logger.info("Model '%s' not found. Auto-switching to locally installed model '%s'", model_name, first_model)
                        model_name = first_model
                        response = ollama.chat(
                            model=model_name,
                            format=SubtitleResponse.model_json_schema(),
                            messages=messages,
                        )
                    else:
                        raise
                else:
                    raise

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
