# 📋 Project Kanban Board: Video-to-Subtitle AI Pipeline

Track implementation progress across modules and phases.

---

## 📥 Backlog

- [ ] **Phase 4.1:** End-to-End Test with sample video (< 1 min)
- [ ] **Phase 4.2:** Timestamp Integrity Verification post-LLM correction
- [ ] **Phase 4.3:** LLM Payload Chunk Size Optimization

---

## ⏳ To Do

### 🔧 Phase 1: Environment & Prerequisites
- [ ] **Task 1.1:** Initialize Python virtual environment (`.venv`)
- [ ] **Task 1.2:** Create `requirements.txt` (`faster-whisper`, `ollama`, `pydantic`)
- [ ] **Task 1.3:** Verify system FFmpeg installation in PATH

### 🧩 Phase 2: Core Modules
- [ ] **Task 2.1 (Module A):** Audio Extraction (`src/audio_extraction/extractor.py`)
- [ ] **Task 2.2 (Module B):** Audio Transcription (`src/transcription/transcriber.py`)
- [ ] **Task 2.3 (Module C):** LLM Grammar Correction (`src/grammar_correction/corrector.py`)
- [ ] **Task 2.4 (Module D):** SRT Subtitle Generator (`src/srt_generation/generator.py`)

### 🚀 Phase 3: Orchestration & CLI
- [ ] **Task 3.1:** Main CLI Script (`main.py`) with `argparse`
- [ ] **Task 3.2:** Pipeline Integration (`src/orchestration/pipeline.py`)
- [ ] **Task 3.3:** Progress Logging & Error Handling

---

## 🏃 In Progress

- [/] **Architecture & Feature Setup:** Modular feature structure and skill integration

---

## ✅ Done

- [x] **Project Specification:** `PLAN.md` and `AGENTS.md` configuration
- [x] **Agent Skills Integration:** Superpower skills suite (14 skills)
- [x] **Feature Architecture:** `src/` feature folders (`audio_extraction`, `transcription`, `grammar_correction`, `srt_generation`, `orchestration`)
