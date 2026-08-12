import logging
import os
from faster_whisper import WhisperModel
from src.schemas import SegmentDict, WhisperModelSize

logger = logging.getLogger(__name__)


def transcribe_audio(
    audio_path: str, model_size: WhisperModelSize = "small"
) -> list[SegmentDict]:
    """Transcribe an audio file into timestamped text segments using faster-whisper.

    Args:
        audio_path: Path to the input audio file.
        model_size: Whisper model size (default "small").

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
        segments, _ = model.transcribe(audio_path, beam_size=5)

        results: list[SegmentDict] = []
        for index, segment in enumerate(segments, start=1):
            results.append({
                "id": index,
                "start": float(segment.start),
                "end": float(segment.end),
                "text": segment.text.strip(),
            })
        logger.info("Successfully transcribed %d segments", len(results))
        return results
    except Exception as e:
        if isinstance(e, FileNotFoundError):
            raise
        raise RuntimeError(
            f"Transcription failed for audio file '{audio_path}': {e}"
        ) from e
