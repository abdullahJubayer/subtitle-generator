"""LLM Provider abstraction layer supporting Ollama, Google Gemini, and Puter.js APIs."""

import json
import logging
import os
from typing import Any
import urllib.error
import urllib.request
import ollama
from src.schemas import SubtitleResponse

logger = logging.getLogger(__name__)


def get_available_gemini_models(api_key: str | None = None) -> list[str]:
    """Dynamically fetch and verify available non-deprecated Gemini models.

    Args:
        api_key: Optional API key. If None, reads from GEMINI_API_KEY env var.

    Returns:
        List of verified working Gemini model names.
    """
    key = api_key or os.environ.get("GEMINI_API_KEY")
    default_models = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-3.1-pro-preview", "gemini-pro-latest"]
    if not key:
        return default_models

    candidates: list[str] = []
    try:
        from google import genai
        client = genai.Client(api_key=key)
        for m in client.models.list():
            name = getattr(m, "name", "") or str(m)
            clean_name = name.replace("models/", "")
            if "gemini" in clean_name.lower() and not any(
                dep in clean_name.lower()
                for dep in ["deprecated", "audio", "embedding", "robotics", "computer-use", "image", "tts"]
            ):
                candidates.append(clean_name)
    except Exception as e:
        logger.debug("Failed listing models with google.genai: %s", e)

    if not candidates:
        candidates = default_models

    # Perform lightweight test call verification to exclude 404 NOT_FOUND deprecated models
    verified: list[str] = []
    try:
        from google import genai
        client = genai.Client(api_key=key)
        for m in candidates:
            try:
                res = client.models.generate_content(model=m, contents="hi")
                if res:
                    verified.append(m)
            except Exception as err:
                err_str = str(err)
                # Exclude if 404 NOT_FOUND / no longer available for new users
                if "404" in err_str or "no longer available" in err_str:
                    logger.debug("Excluding deprecated Gemini model '%s': %s", m, err_str)
                else:
                    # Keep models that failed due to temporary 429 quota rate limits but are valid active models
                    verified.append(m)
    except Exception as e:
        logger.debug("Model verification ping failed: %s", e)

    if not verified:
        verified = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-3.1-pro-preview"]

    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for m in verified:
        if m not in seen:
            seen.add(m)
            deduped.append(m)

    return deduped


def call_llm_provider(
    provider: str,
    model_name: str,
    messages: list[dict[str, Any]],
    api_key: str | None = None,
) -> str:
    """Route LLM requests to the specified provider ('ollama', 'gemini', or 'puter').

    Args:
        provider: Provider name ('ollama', 'gemini', or 'puter').
        model_name: Name of model to call.
        messages: List of message dictionaries containing 'role' and 'content'.
        api_key: API key for cloud providers (optional, falls back to environment variable).

    Returns:
        JSON string response from the LLM provider.

    Raises:
        ValueError: If Gemini or Puter API key is missing.
        RuntimeError / Exception: If LLM call fails.
    """
    provider_clean = (provider or "ollama").strip().lower()

    if provider_clean == "gemini":
        key = api_key or os.environ.get("GEMINI_API_KEY")
        if not key:
            raise ValueError(
                "Gemini API key is missing. Provide 'api_key' or set GEMINI_API_KEY environment variable."
            )

        if not model_name or model_name == "llama3.2:3b":
            model_name = "gemini-2.5-flash"

        system_instruction = ""
        user_content = ""
        for msg in messages:
            role = msg.get("role", "")
            content = str(msg.get("content", ""))
            if role == "system":
                system_instruction = (
                    f"{system_instruction}\n{content}" if system_instruction else content
                )
            else:
                user_content = f"{user_content}\n{content}" if user_content else content

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=key)
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=SubtitleResponse.model_json_schema(),
                system_instruction=system_instruction if system_instruction else None,
            )

            # Perform call with requested model or auto-fallback if deprecated/404
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=user_content,
                    config=config,
                )
            except Exception as model_err:
                logger.warning(
                    "Gemini API model '%s' failed (%s). Attempting auto-fallback...",
                    model_name,
                    model_err,
                )
                fallback_models = [m for m in get_available_gemini_models(key) if m != model_name]
                response = None
                for fb_model in fallback_models:
                    try:
                        response = client.models.generate_content(
                            model=fb_model,
                            contents=user_content,
                            config=config,
                        )
                        if response:
                            logger.warning(
                                "⚠️ Model '%s' is unavailable or deprecated. Automatically switched to working model '%s'. Please select a valid model in the dropdown.",
                                model_name,
                                fb_model,
                            )
                            break
                    except Exception:
                        continue
                if not response:
                    raise model_err

            res_text = getattr(response, "text", "") or ""
            if not res_text and hasattr(response, "candidates") and response.candidates:
                cand = response.candidates[0]
                if hasattr(cand, "content") and hasattr(cand.content, "parts"):
                    for p in cand.content.parts:
                        if hasattr(p, "text") and p.text:
                            res_text += p.text
            return res_text or ""
        except ImportError:
            try:
                import google.generativeai as genai_legacy

                genai_legacy.configure(api_key=key)
                model = genai_legacy.GenerativeModel(
                    model_name=model_name,
                    system_instruction=system_instruction if system_instruction else None,
                    generation_config={"response_mime_type": "application/json"},
                )
                response = model.generate_content(user_content)
                return response.text or ""
            except Exception as e:
                logger.error("Failed executing Gemini request with google.generativeai: %s", e)
                raise
        except Exception as e:
            logger.error("Failed executing Gemini request with google.genai: %s", e)
            raise

    elif provider_clean == "puter":
        key = api_key or os.environ.get("PUTER_API_KEY")
        if not key:
            raise ValueError(
                "Puter API key is missing. Provide 'api_key' or set PUTER_API_KEY environment variable."
            )

        if not model_name or model_name in ("llama3.2:3b", "llama3.1"):
            model_name = "gpt-4o-mini"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
            "X-Puter-API-Key": key,
        }
        payload = {
            "model": model_name,
            "messages": messages,
            "response_format": {"type": "json_object"},
        }

        try:
            req = urllib.request.Request(
                "https://api.puter.com/v2/ai/chat",
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(req) as response:
                response_bytes = response.read()
                res_data = json.loads(response_bytes.decode("utf-8"))
        except urllib.error.HTTPError as err:
            err_body = err.read().decode("utf-8", errors="replace")
            logger.error("Failed executing Puter request (HTTP %s): %s", err.code, err_body)
            raise RuntimeError(f"Puter API HTTP request failed ({err.code}): {err_body}") from err
        except Exception as e:
            logger.error("Failed executing Puter request: %s", e)
            raise RuntimeError(f"Puter API request failed: {e}") from e

        content = None
        if isinstance(res_data, dict):
            choices = res_data.get("choices")
            if isinstance(choices, list) and len(choices) > 0 and isinstance(choices[0], dict):
                first_choice = choices[0]
                msg = first_choice.get("message")
                if isinstance(msg, dict):
                    content = msg.get("content")
                elif isinstance(msg, str):
                    content = msg

            if not content:
                msg = res_data.get("message")
                if isinstance(msg, dict):
                    content = msg.get("content")
                elif isinstance(msg, str):
                    content = msg

            if not content:
                content = res_data.get("text")

            if not content:
                content = res_data.get("content")

        if isinstance(content, (dict, list)):
            content = json.dumps(content)

        if content is None or not str(content).strip():
            raise RuntimeError("Puter API returned empty response or content was invalid.")

        return str(content)

    else:
        # Default provider: ollama
        try:
            response = ollama.chat(
                model=model_name,
                format=SubtitleResponse.model_json_schema(),
                messages=messages,
            )
        except ollama.ResponseError as err:
            if getattr(err, "status_code", None) == 404:
                available = ollama.list()
                models_list = (
                    getattr(available, "models", [])
                    or (available.get("models", []) if isinstance(available, dict) else [])
                )
                if models_list:
                    first_model = (
                        models_list[0].model
                        if hasattr(models_list[0], "model")
                        else models_list[0].get("name", "")
                    )
                    logger.info(
                        "Model '%s' not found. Auto-switching to locally installed model '%s'",
                        model_name,
                        first_model,
                    )
                    response = ollama.chat(
                        model=first_model,
                        format=SubtitleResponse.model_json_schema(),
                        messages=messages,
                    )
                else:
                    raise
            else:
                raise

        content = ""
        if hasattr(response, "message") and hasattr(response.message, "content"):
            content = response.message.content
        elif isinstance(response, dict):
            content = response.get("message", {}).get("content", "")
        elif hasattr(response, "text"):
            content = response.text
        else:
            content = str(response)

        return content or ""

