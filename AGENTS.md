# AGENTS.md

## Context
This project is a Python-based video processing pipeline that generates AI-corrected subtitles. 

## Setup Commands
- Install dependencies: `pip install -r requirements.txt`
- System prerequisites: FFmpeg must be installed and available in the system PATH.
- Run main app: `python main.py`

## Code Style & Architecture
- **Language:** Python 3.10+
- **Typing:** Strict type hinting is required for all function signatures.
- **Modularity:** Do not write monolithic scripts. Each step (extraction, transcription, correction, generation) must be a standalone function that accepts inputs and returns structured data.
- **Error Handling:** Use `try/except` blocks for all external system calls (FFmpeg, local LLM, file I/O). Do not let the program crash silently.
- **No Hallucinations:** When generating data schemas, strictly follow the provided `pydantic` models. 

## Data Handoff Standard
All modules must pass subtitle data using this structure (List of Dictionaries):
```python
[
    {"id": 1, "start": 0.0, "end": 2.5, "text": "Raw or corrected text"},
    {"id": 2, "start": 2.5, "end": 5.0, "text": "Raw or corrected text"}
]

---

### 3. Feature-Wise Agent Skills
Create the following folders and files inside the `skills/` directory. The AI agent will load these instructions on-demand when tasked with building a specific feature.

#### `skills/audio-extraction/SKILL.md`
```markdown
---
name: audio-extraction
description: Extracts an audio track from a video file using FFmpeg. Use this when building the first step of the pipeline or handling media files.
---

# Audio Extraction Workflow

## Requirements
Use the standard Python `subprocess` module. Do not use heavy wrapper libraries like `moviepy` or `ffmpeg-python`.

## Execution Steps
1. Accept an input `video_path` and an output `audio_path`.
2. Construct the FFmpeg command: `["ffmpeg", "-i", video_path, "-q:a", "0", "-map", "a", audio_path, "-y"]`.
3. Use `subprocess.run()`. Suppress stdout and stderr to keep the console clean.
4. Raise a `RuntimeError` if the subprocess fails.
5. Return the absolute path to the extracted audio file.