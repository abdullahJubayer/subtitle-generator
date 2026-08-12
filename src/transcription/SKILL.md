---
name: transcription
description: Converts an audio file into timestamped text segments using faster-whisper. Use this when the agent needs to implement speech-to-text.
---

# Transcription Workflow

## Requirements
Use the `faster-whisper` library. 

## Execution Steps
1. Initialize `WhisperModel("small", device="cpu", compute_type="int8")`.
2. Call the `.transcribe(audio_path, beam_size=5)` method.
3. Iterate over the returned segments.
4. Extract the `start` (float), `end` (float), and `text` (string).
5. Map these into a Python list of dictionaries. You MUST assign an incrementing integer `id` to each segment starting at 1.
6. Strip leading and trailing whitespace from the `text`.
7. Return the list.
