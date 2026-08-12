#!/usr/bin/env python3
"""CLI entry point for Video-to-Subtitle AI Pipeline."""

import argparse
import logging
import sys
from src.orchestration.pipeline import run_pipeline


def setup_logging(verbose: bool = False) -> None:
    """Configure console logging level and format."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def main() -> int:
    """CLI Entry point parser and execution handler."""
    parser = argparse.ArgumentParser(
        description="Video-to-Subtitle AI Pipeline: Extract audio, transcribe with Whisper, correct grammar with local LLM, and output .srt subtitles."
    )
    parser.add_argument(
        "-i",
        "--input",
        required=True,
        help="Path to input video file (.mp4, .mkv, .mov, etc.)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Path to target output .srt file (default: same name as input video)",
    )
    parser.add_argument(
        "--model",
        default="small",
        choices=["tiny", "base", "small", "medium", "large"],
        help="Whisper model size (default: small)",
    )
    parser.add_argument(
        "--ollama-model",
        default="llama3.1",
        help="Local Ollama LLM model name for grammar correction (default: llama3.1)",
    )
    parser.add_argument(
        "--skip-grammar",
        action="store_true",
        help="Skip LLM grammar correction stage",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose debug logging",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    try:
        output_srt = run_pipeline(
            video_path=args.input,
            output_path=args.output,
            model_size=args.model,
            skip_grammar=args.skip_grammar,
            ollama_model=args.ollama_model,
        )
        print(f"\n✨ Subtitle generation complete! File saved at:\n   {output_srt}")
        return 0
    except FileNotFoundError as e:
        logging.error("File Error: %s", e)
        return 1
    except RuntimeError as e:
        logging.error("Pipeline Execution Error: %s", e)
        return 2
    except Exception as e:
        logging.error("Unexpected Error: %s", e, exc_info=True)
        return 3


if __name__ == "__main__":
    sys.exit(main())
