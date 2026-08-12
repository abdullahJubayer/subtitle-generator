---
name: srt-generation
description: Formats timestamped text segments into a standard .srt subtitle file. Use this for the final output stage.
---

# SRT Generation Workflow

## Requirements
Use standard Python file I/O operations. 

## SubRip Format Rules
An SRT entry must follow this exact format:
[Segment ID]
[Start Time] --> [End Time]
[Text]
(Blank Line)

## Execution Steps
1. Create a helper function `format_timestamp(seconds: float) -> str` that converts raw seconds into the `HH:MM:SS,mmm` format (e.g., `00:01:23,450`).
2. Accept the corrected segments list and an `output_path`.
3. Open the file in `w` mode with `utf-8` encoding.
4. Loop through the segments.
5. Format the start and end times.
6. Write the ID, time range, text, and a trailing newline to the file.
7. Print a success message to the console.
