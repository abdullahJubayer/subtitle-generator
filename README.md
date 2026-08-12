# 🎬 Video-to-Subtitle AI Pipeline

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![GUI Framework](https://img.shields.io/badge/GUI-PyQt6-brightgreen.svg)](https://www.riverbankcomputing.com/software/pyqt/)
[![Speech Model](https://img.shields.io/badge/Whisper-faster--whisper-orange.svg)](https://github.com/SYSTRAN/faster-whisper)
[![Local LLM](https://img.shields.io/badge/LLM-Ollama%20%28Llama%203.2%2F3.1%29-purple.svg)](https://ollama.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

An end-to-end, privacy-focused Python application that extracts audio from video files, transcribes speech with precise millisecond timestamps using `faster-whisper`, corrects grammar using a local LLM via `Ollama` with `Pydantic` schema enforcement, and exports standard `.srt` subtitle files. 

Includes both a **Desktop GUI Application** (PyQt6) with real-time video playback & synchronized subtitle previews, and a powerful **CLI tool**.

---

## 🌟 Key Features

- **⚡ Fast Audio Extraction:** Uses native `FFmpeg` subprocess calls to cleanly strip audio tracks without heavy dependencies.
- **🎙️ High-Accuracy Speech Transcription:** Powered by `faster-whisper` (CPU `int8` quantization) for fast, lightweight speech-to-text with millisecond timestamps.
- **🧠 Local LLM Grammar Correction:** Integrates local LLMs via `Ollama` (`llama3.2:3b`, `llama3.1`, `mistral`, etc.) using structured `Pydantic` JSON schemas to refine transcription grammar without altering segment IDs or timing.
- **🛡️ Resilience & Safe Fallback:** Automatic model auto-detection and graceful fallback to original segment text if Ollama is offline or a model is missing.
- **📜 Standard SubRip (`.srt`) Export:** Formats timestamps into `HH:MM:SS,mmm` SubRip subtitle files.
- **🖥️ PyQt6 Desktop GUI:** 
  - Native file browser dialog (`.mp4`, `.mkv`, `.mov`, `.avi`, `.webm`).
  - Asynchronous worker thread (`QThread`) with live stage progress bar (0% - 100%) and scrollable log console.
  - Interactive media player with transport controls, volume slider, and live synchronized caption bar (`💬`).
  - Direct `.srt` export/download button.
- **💻 Full Command Line Interface (CLI):** Flexible CLI flags for headless automated processing and script integration.

---

## 📁 Architecture & Project Structure

The codebase is organized into modular Python packages with explicit type annotations:

```text
Subtitle Generator/
├── src/
│   ├── audio_extraction/   # Module A: FFmpeg subprocess audio extraction
│   │   ├── __init__.py
│   │   └── extractor.py
│   ├── transcription/      # Module B: faster-whisper speech-to-text engine
│   │   ├── __init__.py
│   │   └── transcriber.py
│   ├── grammar_correction/ # Module C: Ollama LLM batch correction + Pydantic schema
│   │   ├── __init__.py
│   │   └── corrector.py
│   ├── srt_generation/     # Module D: HH:MM:SS,mmm SubRip .srt file generator
│   │   ├── __init__.py
│   │   └── generator.py
│   ├── orchestration/      # Phase 3: Pipeline runner & temporary file cleanup
│   │   ├── __init__.py
│   │   └── pipeline.py
│   ├── gui/                # Phase 5: Desktop GUI & Video Player Application
│   │   ├── __init__.py
│   │   ├── app.py          # Main QMainWindow application window
│   │   ├── worker.py       # Asynchronous QThread worker emitting progress signals
│   │   └── player.py       # QMediaPlayer widget with live subtitle caption bar
│   └── schemas.py          # Shared Pydantic schemas & SegmentDict type aliases
├── subagents/              # Agentic workflow definitions (dev1, dev2, seniorDev, qa)
├── tests/                  # Headless unit test suite (100% pass coverage)
├── main.py                 # CLI / GUI entrypoint launcher
├── PLAN.md                 # Implementation plan & milestone tracking
├── AGENTS.md               # Project architecture & coding standards
└── requirements.txt        # Runtime dependencies
```

### Data Handoff Standard
All pipeline modules pass subtitle segments using a standardized `List[Dict]` layout:
```python
[
    {"id": 1, "start": 0.0, "end": 2.5, "text": "Raw or corrected subtitle text..."},
    {"id": 2, "start": 2.5, "end": 5.0, "text": "Next segment..."}
]
```

---

## ⚙️ Prerequisites & System Setup

### 1. System Prerequisites
- **Python:** 3.10 or higher
- **FFmpeg:** Must be installed and available in your system `PATH`.
  - **macOS:** `brew install ffmpeg`
  - **Ubuntu/Debian:** `sudo apt install ffmpeg`
  - **Windows:** Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add `bin/` to System PATH.

### 2. Local LLM Setup (Ollama)
Install [Ollama](https://ollama.com/) and pull a local model:
```bash
# Install Ollama and pull llama3.2:3b (Recommended)
ollama pull llama3.2:3b

# Or pull llama3.1 / mistral
ollama pull llama3.1
```

---

## 📥 Installation

```bash
# 1. Clone the repository
git clone https://github.com/abdullahJubayer/subtitle-generator.git
cd subtitle-generator

# 2. Create and activate a Python virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## 🚀 Running the Application

### 🖥️ 1. Desktop GUI Mode (Recommended)
Launch the interactive desktop interface:

```bash
# Launch GUI directly
python main.py --gui

# Or simply run without arguments
python main.py
```

#### GUI Workflow:
1. Click **Browse...** to select any video file (`.mp4`, `.mkv`, `.mov`, `.avi`, `.webm`).
2. Adjust Whisper model size (`tiny`, `base`, `small`, `medium`, `large`) or Ollama model name (`llama3.2:3b`).
3. Click **🚀 Start Subtitle Pipeline**. Watch live step-by-step progress bars and console logs.
4. When finished, the video automatically loads in the preview player with a **💬 Live Subtitle Caption Bar** updating in real time as the video plays!
5. Click **`💾 Export / Save .SRT File`** to download/save your `.srt` file anywhere on your computer.

---

### 💻 2. Command Line Interface (CLI) Mode
For headless batch processing and automated workflows:

```bash
# Basic usage (generates video_name.srt)
python main.py -i input_video.mp4

# Specify custom output SRT path and Whisper model size
python main.py -i input_video.mp4 -o custom_subtitles.srt --model medium

# Specify local Ollama model
python main.py -i input_video.mp4 --ollama-model llama3.2:3b

# Skip LLM grammar correction stage (faster execution)
python main.py -i input_video.mp4 --skip-grammar

# Enable verbose debug logging
python main.py -i input_video.mp4 -v
```

---

## 🤖 LLM Use Case & Pydantic Schema Workflow

### How the Local LLM is Utilized
Whisper transcription engines occasionally output minor grammatical errors, disfluencies, or missing punctuation. To fix these locally without sending data to external APIs:

1. **Timestamp Stripping (Context Window Optimization):**
   Timestamps (`start` and `end`) are stripped before constructing the LLM payload to save context tokens and eliminate hallucination risks. Only `id` and `text` are sent.
2. **Batch Processing:**
   Segments are processed in chunks of 40 segments max to prevent model memory exhaustion.
3. **Structured JSON Validation (Pydantic):**
   Ollama is invoked with `format=SubtitleResponse.model_json_schema()` using Pydantic models:

```python
class SubtitleSegment(BaseModel):
    id: int
    text: str

class SubtitleResponse(BaseModel):
    segments: list[SubtitleSegment]
```

4. **System Prompt:**
   > *"You are a subtitle editor. Correct grammar. DO NOT change IDs. Keep the exact same number of segments."*
5. **Re-mapping & Safe Fallback:**
   The corrected `text` strings are re-mapped back to original segment dictionaries by `id`. If Ollama is offline or the model is missing, the module logs a warning and safely falls back to the original text without crashing.

---

## 🧪 Testing & Verification

Run the full headless unit test suite:

```bash
python -m unittest discover -s tests
```

- **Test Suite Coverage:** 23/23 tests passing across module extractions, transcription mocks, Ollama structured responses, SRT formatting, and PyQt6 GUI components.

---

## 🤝 Agentic Workflow Architecture

This project was built using an autonomous agentic software development methodology:
- **`dev1` / `dev2`:** Parallel Developer Subagents implementing feature modules concurrently.
- **`seniorDev`:** Senior Architect Code Reviewer running on the high-reasoning **`pro` model**.
- **`qa`:** QA Automation Subagent executing empirical tests and managing GitHub board issue closures.

Detailed subagent roles are documented in [`AGENTS.md`](AGENTS.md) and [`subagents/`](subagents/).

---

## 📄 License

This project is open-source under the [MIT License](LICENSE).
