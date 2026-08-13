"""LLM Provider abstraction layer supporting Ollama and Google Gemini APIs."""

import logging
import os
from typing import Any
import ollama
from src.schemas import SubtitleResponse

logger = logging.getLogger(__name__)


def call_llm_provider(
    provider: str,
    model_name: str,
    messages: list[dict[str, Any]],
    api_key: str | None = None,
) -> str:
    """Route LLM requests to the specified provider ('ollama' or 'gemini').

    Args:
        provider: Provider name ('ollama' or 'gemini').
        model_name: Name of model to call.
        messages: List of message dictionaries containing 'role' and 'content'.
        api_key: API key for cloud providers (optional, falls back to environment variable).

    Returns:
        JSON string response from the LLM provider.

    Raises:
        ValueError: If Gemini API key is missing.
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
                system_instruction=system_instruction if system_instruction else None,
            )
            response = client.models.generate_content(
                model=model_name,
                contents=user_content,
                config=config,
            )
            return response.text or ""
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
