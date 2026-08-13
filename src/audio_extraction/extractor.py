import json
import logging
import os
import subprocess

logger = logging.getLogger(__name__)


def get_audio_tracks(video_path: str) -> list[dict]:
    """Inspect input video file using ffprobe and return list of audio track metadata dicts."""
    if not os.path.exists(video_path):
        return []

    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a",
        "-show_entries",
        "stream=index,codec_name,channels:stream_tags=language,title",
        "-of",
        "json",
        video_path,
    ]
    try:
        res = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True
        )
        data = json.loads(res.stdout)
        streams = data.get("streams", [])
        tracks = []
        for i, s in enumerate(streams):
            codec = s.get("codec_name", "unknown")
            tags = s.get("tags", {}) or {}
            lang = tags.get("language", "und")
            title = tags.get("title", "")
            ch = s.get("channels", 2)
            desc = f"Track {i+1}: "
            if title:
                desc += f"{title} "
            if lang and lang != "und":
                desc += f"[{lang.upper()}] "
            desc += f"({codec}, {ch}ch)"
            tracks.append(
                {
                    "audio_index": i,
                    "stream_index": s.get("index", i),
                    "codec": codec,
                    "language": lang,
                    "title": title,
                    "label": desc.strip(),
                }
            )
        return tracks
    except Exception as e:
        logger.warning("ffprobe audio track discovery failed: %s", e)
        return [{"audio_index": 0, "label": "Track 1: Default Audio"}]


def extract_audio(video_path: str, audio_path: str, audio_track: int = 0) -> str:
    """Extract specified audio track from video file using FFmpeg.

    Args:
        video_path: Path to input video file.
        audio_path: Path where output audio file should be saved.
        audio_track: 0-based index of target audio stream (default 0).

    Returns:
        Absolute path to the extracted audio file.

    Raises:
        FileNotFoundError: If input video file does not exist.
        RuntimeError: If FFmpeg process fails or raises an error.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Input video file not found: {video_path}")

    logger.info("Extracting audio track %d from '%s' to '%s'", audio_track, video_path, audio_path)
    cmd = [
        "ffmpeg",
        "-i",
        video_path,
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-map",
        f"0:a:{audio_track}?",
        audio_path,
        "-y",
    ]
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
