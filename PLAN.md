# Implementation Plan: Video-to-Subtitle AI Pipeline

## Overview
A Python-based pipeline that extracts audio from video, transcribes it with timestamps, corrects grammar using a local LLM, and outputs an `.srt` file.

## Phase 1: Environment Setup
- [ ] Initialize Python virtual environment.
- [ ] Create `requirements.txt` (`faster-whisper`, `ollama`, `pydantic`).
- [ ] Verify system-level installation of FFmpeg.

## Phase 2: Core Pipeline Modules
- [ ] **Module A:** Audio Extraction. Implement FFmpeg subprocess to strip audio track.
- [ ] **Module B:** Transcription. Integrate `faster-whisper` to generate timestamped segments.
- [ ] **Module C:** Grammar Correction. Implement Ollama/Llama 3.1 integration with Pydantic for structured JSON outputs.
- [ ] **Module D:** SRT Generation. Create formatter to convert raw segments into SubRip format.

## Phase 3: Orchestration & CLI
- [ ] Create `main.py` to chain Modules A through D.
- [ ] Implement `argparse` for command-line inputs (e.g., `python main.py --input video.mp4`).
- [ ] Add robust error handling and progress logging to the console.

## Phase 4: Testing & Refinement
- [ ] Test with a short (< 1 min) video.
- [ ] Verify timestamp integrity post-LLM correction.
- [ ] Optimize chunk sizes for the LLM payload to prevent context window overflow.