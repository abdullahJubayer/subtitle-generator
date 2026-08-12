"""Audio extractor module using FFmpeg subprocess."""

import logging
import os
import subprocess

logger = logging.getLogger(__name__)


def extract_audio(video_path: str, audio_path: str) -> str:
    """Extract audio track from video file using FFmpeg.

    Args:
        video_path: Path to input video file.
        audio_path: Path where output audio file should be saved.

    Returns:
        Absolute path to the extracted audio file.

    Raises:
        FileNotFoundError: If input video file does not exist.
        RuntimeError: If FFmpeg process fails or raises an error.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Input video file not found: {video_path}")

    logger.info("Extracting audio from '%s' to '%s'", video_path, audio_path)
    cmd = ["ffmpeg", "-i", video_path, "-q:a", "0", "-map", "a", audio_path, "-y"]
    try:
        subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        stderr_output = e.stderr or ""
        raise RuntimeError(
            f"FFmpeg audio extraction failed for '{video_path}': {stderr_output.strip()}"
        ) from e
    except Exception as e:
        raise RuntimeError(
            f"Failed to execute FFmpeg command for '{video_path}': {e}"
        ) from e

    return os.path.abspath(audio_path)
