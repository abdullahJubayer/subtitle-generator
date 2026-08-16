import json
import logging
import time
from typing import Callable, Optional
from src.grammar_correction.llm_providers import call_llm_provider
from src.grammar_correction.prompts import build_system_prompt
from src.schemas import SegmentDict, SubtitleResponse, SubtitleSegment

logger = logging.getLogger(__name__)


def correct_grammar(
    segments: list[SegmentDict],
    model_name: str = "llama3.2:3b",
    target_language: str = "English",
    provider: str = "ollama",
    api_key: str | None = None,
    llm_callback: Optional[
        Callable[[str, str, str, str, str, list[tuple[str, str]]], None]
    ] = None,
) -> list[SegmentDict]:
    """Correct the grammar of subtitle text segments or translate them using LLM provider.

    Args:
        segments: List of segment dictionaries with keys 'id', 'start', 'end', 'text'.
        model_name: LLM model name to use for grammar correction/translation.
        target_language: Target language for translation/correction (default "English").
        provider: LLM provider name ("ollama" or "gemini", default "ollama").
        api_key: API key for cloud LLM provider (optional).
        llm_callback: Optional callback receiving (payload_json, response_json, provider, model_name, batch_info, diff_items).

    Returns:
        A list of segment dictionaries with updated 'text' fields.
    """
    if not segments:
        return []

    # Map original text by ID for safe fallback
    corrected_map: dict[int, str] = {
        int(seg["id"]): str(seg["text"]) for seg in segments
    }

    provider_clean = (provider or "ollama").strip().lower()
    if provider_clean in ("gemini", "puter"):
        batch_size = len(segments)  # Single prompt full-transcript execution for Cloud LLMs
    else:
        batch_size = 10  # 10 segments per batch for local models to prevent segment merging

    total_batches = (len(segments) + batch_size - 1) // batch_size
    is_translation = target_language.strip().lower() not in ("english", "en")

    if is_translation:
        logger.info(
            "[Step 3/4] 🌐 Starting LLM natural translation into '%s' (%d segments in %d batch(es)) using provider '%s' (model '%s')...",
            target_language,
            len(segments),
            total_batches,
            provider,
            model_name,
        )
    else:
        logger.info(
            "[Step 3/4] 🧠 Starting LLM English grammar correction (%d segments in %d batch(es)) using provider '%s' (model '%s')...",
            len(segments),
            total_batches,
            provider,
            model_name,
        )

    for i in range(0, len(segments), batch_size):
        batch = segments[i : i + batch_size]
        batch_index = (i // batch_size) + 1
        payload = [
            {"id": int(seg["id"]), "text": str(seg["text"])} for seg in batch
        ]

        if is_translation:
            logger.info(
                "  ➔ Processing LLM Translation Batch %d/%d (%d segments) -> Target: '%s'",
                batch_index,
                total_batches,
                len(batch),
                target_language,
            )
        else:
            logger.info(
                "  ➔ Processing LLM Grammar Batch %d/%d (%d segments)",
                batch_index,
                total_batches,
                len(batch),
            )

        start_time = time.time()
        content = None
        try:
            prompt_system = build_system_prompt(target_language)
            messages = [
                {"role": "system", "content": prompt_system},
                {"role": "user", "content": json.dumps(payload)},
            ]

            content = call_llm_provider(
                provider=provider,
                model_name=model_name,
                messages=messages,
                api_key=api_key,
            )

            if content:
                parsed_response = SubtitleResponse.model_validate_json(content)
                adapted_count = 0
                res_segs = parsed_response.segments

                # Positional + ID alignment guard:
                # If output segment count matches batch size, map by array index idx to guarantee 100% timestamp alignment
                use_positional_mapping = len(res_segs) == len(batch)
                for idx, item in enumerate(res_segs):
                    if item.text and item.text.strip():
                        if use_positional_mapping and idx < len(batch):
                            target_id = int(batch[idx]["id"])
                        else:
                            target_id = item.id

                        if target_id in corrected_map:
                            corrected_map[target_id] = item.text.strip()
                            adapted_count += 1
                logger.info(
                    "  ✓ LLM Batch %d/%d successfully processed (%d segments adapted)",
                    batch_index,
                    total_batches,
                    adapted_count,
                )
            else:
                logger.warning(
                    f"LLM provider '{provider}' returned empty content for batch {batch_index}/{total_batches}."
                )

        except Exception as e:
            logger.warning(
                f"Grammar correction failed for batch starting at index {i}: {e}. "
                "Falling back to original segment text."
            )
            content = json.dumps({"error": str(e), "provider": provider, "model": model_name, "status": "failed"}, indent=2)

        latency = time.time() - start_time
        if llm_callback:
            diff_items: list[tuple[str, str]] = []
            for seg in batch:
                seg_id = int(seg["id"])
                orig_text = str(seg["text"])
                adapted_text = corrected_map.get(seg_id, orig_text)
                diff_items.append((orig_text, adapted_text))

            batch_info = f"Batch: {batch_index}/{total_batches} ({len(batch)} segs) | Latency: {latency:.2f}s"
            payload_json = json.dumps(payload, indent=2)
            response_json = content or json.dumps({"error": "Empty response", "status": "failed"}, indent=2)
            try:
                llm_callback(
                    payload_json,
                    response_json,
                    provider,
                    model_name,
                    batch_info,
                    diff_items,
                    prompt_system,
                )
            except Exception as cb_err:
                logger.warning("Error executing llm_callback: %s", cb_err)

    result: list[dict[str, float | int | str]] = []
    for seg in segments:
        updated_seg = dict(seg)
        seg_id = int(seg["id"])
        updated_seg["text"] = corrected_map.get(seg_id, str(seg["text"]))
        result.append(updated_seg)

    return result


def correct_single_segment(
    segment: SegmentDict,
    model_name: str = "llama3.2:3b",
    target_language: str = "English",
    provider: str = "ollama",
    api_key: str | None = None,
    llm_callback: Optional[
        Callable[[str, str, str, str, str, list[tuple[str, str]]], None]
    ] = None,
) -> str:
    """Correct or translate a single subtitle segment line using LLM provider.

    Args:
        segment: Single segment dictionary with keys 'id', 'start', 'end', 'text'.
        model_name: LLM model name to use for translation/correction.
        target_language: Target language for translation/correction.
        provider: LLM provider name ("ollama", "gemini", or "puter").
        api_key: Optional API key.
        llm_callback: Optional callback receiving interaction telemetry.

    Returns:
        The updated translated or corrected text string.
    """
    res = correct_grammar(
        [segment],
        model_name=model_name,
        target_language=target_language,
        provider=provider,
        api_key=api_key,
        llm_callback=llm_callback,
    )
    if res and len(res) > 0:
        return str(res[0].get("text", segment.get("text", "")))
    return str(segment.get("text", ""))

