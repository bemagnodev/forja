import json
import os
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import httpx
from google import genai
from google.genai import errors, types

from ..contracts import ProviderFailure


def generate(prepared: dict, prompt: str, model: str, *, client=None) -> dict:
    if client is None:
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            raise ProviderFailure("authentication")
        client = genai.Client(api_key=key, http_options=types.HttpOptions(
            timeout=30000, retry_options=types.HttpRetryOptions(attempts=1)))
    config = types.GenerateContentConfig(
        system_instruction=prompt, response_mime_type="application/json",
        response_schema={"type": "OBJECT", "required": ["rating", "tags", "justification"],
                         "properties": {"rating": {"type": "INTEGER"},
                                        "tags": {"type": "ARRAY", "items": {"type": "STRING"}},
                                        "justification": {"type": "STRING"}}},
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
                                            ("total_tokens", "total_token_count"))
              if type(value := getattr(usage, attr, None)) is int}
    if isinstance(parsed, dict) and tokens:
        parsed = {**parsed, "_usage": tokens}
    return parsed
