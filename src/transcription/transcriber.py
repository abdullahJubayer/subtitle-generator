"""Audio transcription module using faster-whisper."""

from faster_whisper import WhisperModel


def transcribe_audio(
    audio_path: str, model_size: str = "small"
) -> list[dict[str, float | int | str]]:
    """Transcribe an audio file into timestamped text segments using faster-whisper.

    Args:
        audio_path: Path to the input audio file.
        model_size: Whisper model size (default "small").

    Returns:
        List of dictionaries strictly following the schema:
        [{"id": 1, "start": 0.0, "end": 2.5, "text": "Raw text..."}, ...]

    Raises:
        RuntimeError: If transcription fails or faster-whisper model raises an error.
    """
    try:
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        segments, _ = model.transcribe(audio_path, beam_size=5)

        results: list[dict[str, float | int | str]] = []
        for index, segment in enumerate(segments, start=1):
            results.append({
                "id": index,
                "start": float(segment.start),
                "end": float(segment.end),
                "text": segment.text.strip(),
            })
        return results
    except Exception as e:
        raise RuntimeError(
            f"Transcription failed for audio file '{audio_path}': {e}"
        ) from e
