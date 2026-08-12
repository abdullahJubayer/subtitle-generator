import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def format_timestamp(seconds: float) -> str:
    """Format seconds into HH:MM:SS,mmm timestamp format for SRT files.

    Args:
        seconds: Time in seconds.

    Returns:
        Formatted string in HH:MM:SS,mmm format.
    """
    total_ms = int(round(float(seconds) * 1000))
    hours = total_ms // (3600 * 1000)
    total_ms %= (3600 * 1000)
    minutes = total_ms // (60 * 1000)
    total_ms %= (60 * 1000)
    secs = total_ms // 1000
    ms = total_ms % 1000
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def generate_srt(
    segments: list[dict[str, float | int | str]], output_path: str
) -> str:
    """Generate an SRT file from timestamped subtitle segments.

    Args:
        segments: List of segment dicts containing 'id', 'start', 'end', and 'text'.
        output_path: Target path for saving the .srt file.

    Returns:
        The output file path as a string.
    """
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    content_lines: list[str] = []
    for seg in segments:
        seg_id = seg["id"]
        start_fmt = format_timestamp(float(seg["start"]))
        end_fmt = format_timestamp(float(seg["end"]))
        text = str(seg["text"])

        content_lines.append(f"{seg_id}\n{start_fmt} --> {end_fmt}\n{text}\n\n")

    full_text = "".join(content_lines)

    with open(out_file, "w", encoding="utf-8") as f:
        f.write(full_text)

    logger.info(f"SRT file successfully written to {out_file.resolve()}")
    print(f"SRT file generated successfully at: {out_file.resolve()}")
    return str(out_file)
