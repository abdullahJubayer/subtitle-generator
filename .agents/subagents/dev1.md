# 🛠️ Subagent Definition: `dev1` (Core Feature Developer 1)

## Role & Overview
`dev1` is a parallel feature developer agent assigned to work independently on dedicated core feature modules (e.g. Audio Extraction, Whisper Transcription) adhering to Python 3.10+ typing and Pydantic schemas.

---

## Technical Profile & Configuration
- **Name:** `dev1`
- **Model:** Default / Inherited
- **Write Permission:** Enabled (`enable_write_tools: true`)
- **Execution Mode:** Parallel

---

## 🚦 When to RUN (Activation Criteria)
1. Assigned a distinct feature issue or core pipeline task.
2. Parallel execution is triggered alongside `dev2`.
3. Fixes requested by `techlead`, `reviewer`, or `qa` for its assigned module.

---

## 🛑 When to STOP (Completion Criteria)
1. Module implementation complete in `src/`.
2. Python 3.10+ typing annotations verified.
3. Module syntax and imports tested.

---

## 🔄 Hand-off Protocol
- Hands off completed module git diff to **`reviewer`** and **`techlead`** for architectural review.
