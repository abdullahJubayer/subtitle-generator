#!/usr/bin/env python3
"""CLI and GUI entry point for Video-to-Subtitle AI Pipeline."""

import argparse
import logging
import sys


def setup_logging(verbose: bool = False) -> None:
    """Configure console logging level and format."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def launch_gui() -> int:
    """Launch PyQt6 Desktop GUI application."""
    from PyQt6.QtWidgets import QApplication
    from src.gui.app import SubtitleGeneratorApp

    setup_logging(verbose=True)
    app = QApplication(sys.argv)
    window = SubtitleGeneratorApp()
    window.show()
    return app.exec()


def main() -> int:
    """CLI / GUI Entry point parser and execution handler."""
    # If no arguments provided, default to launching desktop GUI
    if len(sys.argv) == 1:
        return launch_gui()

    parser = argparse.ArgumentParser(
        description="Video-to-Subtitle AI Pipeline: Extract audio, transcribe with Whisper, correct grammar with local LLM, and output .srt subtitles."
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Launch PyQt6 Desktop GUI application",
    )
    parser.add_argument(
        "-i",
        "--input",
        required=False,
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
        default="llama3.2:3b",
        help="Local Ollama LLM model name for grammar correction (default: llama3.2:3b)",
    )
    parser.add_argument(
        "--skip-grammar",
        action="store_true",
        help="Skip LLM grammar correction stage",
    )
    parser.add_argument(
        "-l",
        "--target-language",
        default="English",
        help="Target language for subtitles (default: English)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose debug logging",
    )

    args = parser.parse_args()

    if args.gui:
        return launch_gui()

    if not args.input:
        parser.error("the following arguments are required: -i/--input (or launch with --gui)")

    setup_logging(args.verbose)

    from src.orchestration.pipeline import run_pipeline

    try:
        output_srt = run_pipeline(
            video_path=args.input,
            output_path=args.output,
            model_size=args.model,
            skip_grammar=args.skip_grammar,
            ollama_model=args.ollama_model,
            target_language=args.target_language,
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
