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
- [x] Test with a short (< 1 min) video.
- [x] Verify timestamp integrity post-LLM correction.
- [x] Optimize chunk sizes for the LLM payload to prevent context window overflow.

## Phase 5: Desktop GUI & Video Player Integration
- [x] **Task 5.1:** File Picker Dialog — Select any local video file via GUI.
- [x] **Task 5.2:** Live Progress Tracker — Visual progress bar & stage status (Extraction -> Transcription -> LLM -> SRT).
- [x] **Task 5.3:** Video Player & Subtitle Preview — Play input video with synced generated subtitle overlay.

## Phase 6: Multi-language Natural Translation Engine
- [x] **Task 6.1:** Ollama Natural Translation Module — Translate and rephrase subtitles into natural target language (e.g., Bangla / Bengali) using LLM.
- [x] **Task 6.2:** CLI Target Language Flag — Support `--target-language` (`-l` / `--language`) parameter.
- [x] **Task 6.3:** GUI Language Selection — Dropdown in PyQt6 interface for target language selection (Bangla, Spanish, French, German, etc.).

## Phase 7: Dynamic LLM Model Selector & Conditional UI Visibility
- [x] **Task 7.1:** Conditional Ollama Toggle & Visibility — Add "Enable LLM Grammar Correction & Translation" checkbox; show Ollama model selection dropdown dynamically when checked.
- [x] **Task 7.2:** Dynamic Installed Model Discovery & Custom Entry — Auto-populate local Ollama models dynamically via `ollama.list()` with custom model input capability.
- [x] **Task 7.3:** CLI & Pipeline Integration — Ensure pipeline conditionally activates LLM processing based on toggle state.

## Phase 8: Cloud LLM Provider Integration (Google Gemini & Puter.js API Support)
- [x] **Task 8.1:** Provider Abstraction Engine — Implement `src/grammar_correction/llm_providers.py` supporting `ollama` and `gemini` (Google Gemini API via `google-genai` with Pydantic JSON schema).
- [x] **Task 8.2:** GUI Provider Selector & API Key Field — Add LLM Provider selector dropdown and masked API Key field in PyQt6 settings panel.
- [x] **Task 8.3:** CLI Provider Flags & Pipeline Integration — Add `--llm-provider` and `--api-key` CLI flags and wire through `run_pipeline`.
- [x] **Task 8.4:** Puter.js AI Provider Integration — Add Puter.js AI REST/SDK provider (`puter`) with 500+ model support (GPT-4o-mini, Claude 3.5 Sonnet, DeepSeek, etc.) in GUI and CLI.