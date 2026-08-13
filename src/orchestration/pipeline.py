"""Pipeline orchestration module linking Modules A through D."""

import logging
import os
import tempfile
from pathlib import Path
from typing import Callable, Optional
from src.audio_extraction.extractor import extract_audio
from src.grammar_correction.corrector import correct_grammar
from src.schemas import SegmentDict, WhisperModelSize
from src.srt_generation.generator import generate_srt
from src.transcription.transcriber import transcribe_audio

logger = logging.getLogger(__name__)


def run_pipeline(
    video_path: str,
    output_path: str | None = None,
    model_size: WhisperModelSize = "small",
    skip_grammar: bool = False,
    ollama_model: str = "llama3.2:3b",
    target_language: str = "English",
    llm_provider: str = "ollama",
    api_key: str | None = None,
    audio_track: int = 0,
    llm_callback: Optional[
        Callable[[str, str, str, str, str, list[tuple[str, str]]], None]
    ] = None,
    transcription_callback: Optional[Callable[[list[SegmentDict]], None]] = None,
    progress_callback: Optional[Callable[[float, str], None]] = None,
) -> str:
    """Run the complete Video-to-Subtitle pipeline."""
    video_file = Path(video_path).resolve()
    if not video_file.exists():
        raise FileNotFoundError(f"Input video file not found: {video_path}")

    if not output_path:
        target_srt = video_file.with_suffix(".srt")
    else:
        target_srt = Path(output_path).resolve()

    logger.info("Starting Video-to-Subtitle Pipeline for '%s'", video_file)

    # Step 1: Extract Audio (Module A)
    temp_dir = tempfile.mkdtemp(prefix="subtitle_pipeline_")
    temp_audio_path = os.path.join(temp_dir, f"{video_file.stem}_temp_audio.wav")

    try:
        if progress_callback:
            progress_callback(10.0, "Extracting audio track...")
        logger.info("[Step 1/4] Extracting audio track %d...", audio_track)
        extracted_audio = extract_audio(str(video_file), temp_audio_path, audio_track=audio_track)

        # Step 2: Transcribe (Module B)
        logger.info("[Step 2/4] Transcribing audio with Whisper ('%s')...", model_size)

        def _tx_progress(pct: float, msg: str) -> None:
            if progress_callback:
                progress_callback(pct, msg)

        segments: list[SegmentDict] = transcribe_audio(
            extracted_audio, model_size=model_size, progress_callback=_tx_progress
        )
        logger.info("Transcription completed: %d segments", len(segments))

        if transcription_callback:
            try:
                transcription_callback(segments)
            except Exception as cb_err:
                logger.warning("Error executing transcription_callback: %s", cb_err)

        # Step 3: Grammar Correction (Module C)
        if not skip_grammar:
            logger.info(
                "[Step 3/4] Correcting grammar with provider '%s' (model='%s', target='%s')...",
                llm_provider,
                ollama_model,
                target_language,
            )
            segments = correct_grammar(
                segments,
                model_name=ollama_model,
                target_language=target_language,
                provider=llm_provider,
                api_key=api_key,
                llm_callback=llm_callback,
            )
        else:
            logger.info("[Step 3/4] Skipping LLM grammar correction as requested.")

        # Step 4: SRT Generation (Module D)
        logger.info("[Step 4/4] Generating SRT file at '%s'...", target_srt)
        final_srt_path = generate_srt(segments, str(target_srt))

        logger.info("Pipeline executed successfully! Output: %s", final_srt_path)
        return final_srt_path

    finally:
        # Cleanup temporary audio files
        if os.path.exists(temp_audio_path):
            try:
                os.remove(temp_audio_path)
            except Exception as e:
                logger.warning("Failed to clean up temporary audio file '%s': %s", temp_audio_path, e)
        if os.path.exists(temp_dir):
            try:
                os.rmdir(temp_dir)
            except Exception:
                pass
