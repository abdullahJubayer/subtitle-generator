"""Pipeline orchestration module linking Modules A through D."""

import logging
import os
import tempfile
from pathlib import Path
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
    ollama_model: str = "llama3.1",
) -> str:
    """Run the complete Video-to-Subtitle pipeline.

    Args:
        video_path: Path to input video file.
        output_path: Path for output .srt file (optional, defaults to video stem + .srt).
        model_size: Whisper model size (default "small").
        skip_grammar: If True, bypasses LLM grammar correction.
        ollama_model: Ollama model name to use for grammar correction.

    Returns:
        Absolute path to the generated .srt file.

    Raises:
        FileNotFoundError: If input video file does not exist.
        RuntimeError: If any pipeline module encounters a critical failure.
    """
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
        logger.info("[Step 1/4] Extracting audio track...")
        extracted_audio = extract_audio(str(video_file), temp_audio_path)

        # Step 2: Transcribe (Module B)
        logger.info("[Step 2/4] Transcribing audio with Whisper ('%s')...", model_size)
        segments: list[SegmentDict] = transcribe_audio(
            extracted_audio, model_size=model_size
        )
        logger.info("Transcription completed: %d segments", len(segments))

        # Step 3: Grammar Correction (Module C)
        if not skip_grammar:
            logger.info(
                "[Step 3/4] Correcting grammar with Ollama ('%s')...", ollama_model
            )
            segments = correct_grammar(segments, model_name=ollama_model)
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
                logger.warning("Failed to clean up temporary audio file '%s': %e", temp_audio_path, e)
        if os.path.exists(temp_dir):
            try:
                os.rmdir(temp_dir)
            except Exception:
                pass
