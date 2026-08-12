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
