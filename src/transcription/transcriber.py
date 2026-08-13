import logging
import os
import time
from typing import Callable, Optional
from faster_whisper import WhisperModel
from src.schemas import SegmentDict, WhisperModelSize

logger = logging.getLogger(__name__)


def format_duration(seconds: float) -> str:
    """Format duration in seconds to HH:MM:SS format."""
    secs = max(0, int(seconds))
    m, s = divmod(secs, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def transcribe_audio(
    audio_path: str,
    model_size: WhisperModelSize = "small",
    progress_callback: Optional[Callable[[float, str], None]] = None,
) -> list[SegmentDict]:
    """Transcribe an audio file into timestamped text segments using faster-whisper.

    Args:
        audio_path: Path to the input audio file.
        model_size: Whisper model size (default "small").
        progress_callback: Optional callback emitting (progress_percent, status_message).

    Returns:
        List of dictionaries strictly following the schema:
        [{"id": 1, "start": 0.0, "end": 2.5, "text": "Raw text..."}, ...]

    Raises:
        FileNotFoundError: If input audio file does not exist.
        RuntimeError: If transcription fails or faster-whisper model raises an error.
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Input audio file not found: {audio_path}")

    logger.info("Transcribing audio file '%s' with model '%s'", audio_path, model_size)
    try:
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        start_time = time.time()
        segments, info = model.transcribe(audio_path, beam_size=5)

        total_duration = info.duration if hasattr(info, "duration") and info.duration else 0.0
        results: list[SegmentDict] = []
        last_log_time = 0.0

        for index, segment in enumerate(segments, start=1):
            results.append({
                "id": index,
                "start": float(segment.start),
                "end": float(segment.end),
                "text": segment.text.strip(),
            })

            now = time.time()
            elapsed = now - start_time
            if total_duration > 0 and (now - last_log_time >= 1.5 or index == 1):
                last_log_time = now
                pct = min(99.0, (segment.end / total_duration) * 100.0)
                speed = segment.end / elapsed if elapsed > 0 else 1.0
                remaining_secs = (total_duration - segment.end) / speed if speed > 0 else 0.0

                cur_str = format_duration(segment.end)
                tot_str = format_duration(total_duration)
                eta_str = format_duration(remaining_secs)

                status_msg = (
                    f"Transcribing audio ({cur_str} / {tot_str}) - {pct:.1f}% "
                    f"[{speed:.1f}x speed, ETA: {eta_str}]"
                )
                logger.info("[Whisper Progress] %s", status_msg)
                if progress_callback:
                    overall_pct = 20.0 + (pct * 0.70)
                    progress_callback(overall_pct, status_msg)

        logger.info("Successfully transcribed %d segments", len(results))
        return results
    except Exception as e:
        if isinstance(e, FileNotFoundError):
            raise
        raise RuntimeError(
            f"Transcription failed for audio file '{audio_path}': {e}"
        ) from e
