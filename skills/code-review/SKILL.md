---
name: code-review
description: Comprehensive code review workflow for inspecting code quality, plan alignment, type safety, Python PEP-8, error handling, and test coverage before merging or completing tasks.
---

# Code Review Protocol

Use this skill when conducting or participating in code reviews across Python pipeline modules.

## Review Objectives & Principles
1. **Plan Alignment:** Ensure code meets requirements in `PLAN.md` & `AGENTS.md`.
2. **Architecture & Typing:** Enforce strict type hints (`Python 3.10+`), clear modular boundaries, and structured data schemas.
3. **Robustness & Error Handling:** Verify `try/except` blocks around FFmpeg, Ollama LLM, and file I/O.
4. **No Hallucination / Schema Validation:** Enforce strict Pydantic schemas and schema integrity.

## Review Steps & Checklist

### 1. Plan & Scope Check
- [ ] Are all required requirements implemented without unnecessary creep?
- [ ] Is data passed using the standard list-of-dictionaries format (`[{"id": 1, "start": 0.0, "end": 2.5, "text": "..."}]`)?

### 2. Python Code Quality & Type Safety
- [ ] Every function signature has explicit type annotations.
- [ ] No unhandled exceptions or swallowed errors.
- [ ] Resources (files, temporary paths, models) are properly managed and cleaned up.

### 3. Execution & Test Verification
- [ ] Run test/verification commands explicitly (`pytest`, `python main.py`, etc.).
- [ ] Confirm no regressions or broken imports.

## Severity Categorization
- **Critical (Must Fix):** Unhandled exceptions, broken data schemas, security issues, missing type annotations.
- **Important (Should Fix):** Missing error logs, inefficient chunking, poor modularity.
- **Minor (Nice to Have):** Code formatting, docstring polishing, variable naming nits.
