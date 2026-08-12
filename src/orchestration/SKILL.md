---
name: pipeline-orchestration
description: Chains core modules together into a complete Video-to-Subtitle CLI application with error handling and logging.
---

# Pipeline Orchestration & CLI Workflow

## Requirements
Use standard Python `argparse`, `logging`, `pathlib`, and `sys`.

## Execution Steps
1. Parse command-line arguments (e.g., `--input`, `--output`, `--model`, `--language`).
2. Validate input video file existence and extension (.mp4, .mkv, .mov, etc.).
3. Execute Phase 2 modules sequentially:
   - Module A: Extract audio track to temporary WAV/AAC file.
   - Module B: Transcribe audio to timestamped segments.
   - Module C: Correct grammar of segments using Ollama local LLM.
   - Module D: Format and output corrected segments into an `.srt` file.
4. Wrap module invocations in try/except blocks with clear console logging and status updates.
5. Clean up temporary audio files upon exit or error.
6. Print summary metrics (e.g., total segments processed, output file path).
