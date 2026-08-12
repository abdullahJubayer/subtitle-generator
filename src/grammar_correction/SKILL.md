---
name: grammar-correction
description: Corrects the grammar of transcribed text using a local LLM via Ollama. Use this to refine raw speech-to-text outputs.
---

# LLM Grammar Correction Workflow

## Requirements
Use the `ollama` Python SDK and `pydantic` for structured output validation. 

## Core Constraint
The LLM must process the text without altering the `id` or losing any segments. Timestamps (`start` and `end`) should NOT be sent to the LLM to save context space.

## Execution Steps
1. Define a Pydantic schema: `SubtitleSegment(id: int, text: str)` and `SubtitleResponse(segments: list[SubtitleSegment])`.
2. Accept the list of raw segment dictionaries.
3. Chunk the list into batches of 40 segments to prevent LLM memory exhaustion.
4. For each chunk, map the data to only include `id` and `text`.
5. Call `ollama.chat(model="llama3.1", format=SubtitleResponse.model_json_schema())`.
6. Prompt the AI: "You are a subtitle editor. Correct grammar. DO NOT change IDs. Keep the exact same number of segments."
7. Parse the JSON response.
8. Re-map the newly corrected `text` back to the original dictionary items using the `id` as the primary key.
9. Return the fully updated list of dictionaries (now containing the corrected text and the original `start`/`end` times).
