import json
import os
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import httpx
from google import genai
from google.genai import errors, types

from ..contracts import ProviderFailure


def generation_parameters(model: str, thinking_level=None) -> dict:
    parameters = {"response_mime_type": "application/json", "schema_version": 1}
    if thinking_level is not None:
        if model != "gemini-3.5-flash-lite" or thinking_level not in ("minimal", "low", "medium", "high"):
            raise ValueError("Thinking level requires Gemini 3.5 Flash-Lite and a supported level")
        parameters["thinking_level"] = thinking_level
    return parameters


def request_timeout_seconds(value=30):
    if type(value) not in (int, float) or not 0 < value <= 120:
        raise ValueError("Timeout must be a finite number greater than 0 and at most 120 seconds")
    return value


def generate(prepared: dict, prompt: str, model: str, *, client=None, thinking_level=None, timeout_seconds=30) -> dict:
    generation_parameters(model, thinking_level)
    timeout_seconds = request_timeout_seconds(timeout_seconds)
    if client is None:
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            raise ProviderFailure("authentication")
        client = genai.Client(api_key=key, http_options=types.HttpOptions(
            timeout=int(timeout_seconds * 1000), retry_options=types.HttpRetryOptions(attempts=1)))
    thinking = {} if thinking_level is None else {
        "thinking_config": types.ThinkingConfig(thinking_level=types.ThinkingLevel(thinking_level.upper()))}
    config = types.GenerateContentConfig(
        system_instruction=prompt, response_mime_type="application/json",
        response_schema={"type": "OBJECT", "required": ["rating", "tags", "justification"],
                         "properties": {"rating": {"type": "INTEGER"},
                                        "tags": {"type": "ARRAY", "items": {"type": "STRING"}},
                                        "justification": {"type": "STRING"}}},
        **thinking,
    )
    try:
        response = client.models.generate_content(model=model, contents=json.dumps(prepared, ensure_ascii=False), config=config)
    except errors.APIError as exc:
        code = exc.code
        category = "rate_limit" if code == 429 else "server_error" if code and code >= 500 else "authentication" if code in (401, 403) else "provider_error"
        retry_after = None
        header = exc.response.headers.get("Retry-After") if exc.response is not None else None
        if header:
            try:
                retry_after = float(header)
            except ValueError:
                try:
                    retry_after = max(0, (parsedate_to_datetime(header) - datetime.now(timezone.utc)).total_seconds())
                except (ValueError, TypeError):
                    retry_after = 31  # Fail closed rather than retry early on an unknown wait.
        raise ProviderFailure(category, retry_after=retry_after, responded=False, http_status=code) from None
    except (httpx.TimeoutException, httpx.TransportError):
        raise ProviderFailure("timeout") from None
    parsed = response.parsed
    if not isinstance(parsed, dict):
        try:
            parsed = json.loads(response.text)
        except (TypeError, ValueError):
            raise ProviderFailure("parsing", responded=True) from None
    usage = getattr(response, "usage_metadata", None)
    tokens = {name: value for name, attr in (("input_tokens", "prompt_token_count"),
                                            ("output_tokens", "candidates_token_count"),
                                            ("total_tokens", "total_token_count"),
                                            ("thinking_tokens", "thoughts_token_count"))
              if type(value := getattr(usage, attr, None)) is int}
    if isinstance(parsed, dict) and tokens:
        parsed = {**parsed, "_usage": tokens}
    candidates = getattr(response, "candidates", None)
    if isinstance(parsed, dict) and isinstance(candidates, (list, tuple)) and candidates:
        reason = getattr(candidates[0], "finish_reason", None)
        reason = getattr(reason, "value", reason)
        if isinstance(reason, str) and len(reason) <= 64:
            parsed = {**parsed, "_finish_reason": reason}
    return parsed
