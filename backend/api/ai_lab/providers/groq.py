"""One HTTP request per call, with no tools, fallbacks or implicit retries."""
import json
import os
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import httpx

from ..contracts import ProviderFailure

MODELS = ("openai/gpt-oss-120b", "qwen/qwen3.8-27b")
GENERATION = {"reasoning_effort": "low", "max_completion_tokens": 4096}
SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["rating", "tags", "justification"],
    "properties": {
        "rating": {"type": "integer"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "justification": {"type": "string"},
    },
}


def generation_parameters(model: str) -> dict:
    # Qwen JSON mode requires separated/hidden reasoning; GPT-OSS rejects this field.
    return {**GENERATION, **({"reasoning_format": "hidden"} if model == "qwen/qwen3.8-27b" else {})}


def generate(prepared: dict, prompt: str, model: str, *, client=None) -> dict:
    if model not in MODELS:
        raise ValueError("Unreviewed Groq model")
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        raise ProviderFailure("authentication")
    if client is None:
        with httpx.Client(timeout=45, transport=httpx.HTTPTransport(retries=0)) as owned:
            return generate(prepared, prompt, model, client=owned)
    try:
        response = client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={"model": model, "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps(prepared, ensure_ascii=False)},
            ], "response_format": {"type": "json_schema", "json_schema": {
                "name": "classification", "strict": True, "schema": SCHEMA,
            }}, **generation_parameters(model)},
        )
    except (httpx.TimeoutException, httpx.TransportError):
        raise ProviderFailure("timeout") from None
    if response.status_code != 200:
        code = response.status_code
        category = ("authentication" if code in (401, 403) else "rate_limit" if code == 429
                    else "server_error" if code >= 500 else "provider_error")
        delay = None
        header = response.headers.get("Retry-After")
        if header:
            try:
                delay = float(header)
            except ValueError:
                try:
                    delay = max(0, (parsedate_to_datetime(header) - datetime.now(timezone.utc)).total_seconds())
                except (ValueError, TypeError):
                    delay = 31
        raise ProviderFailure(category, retry_after=delay)
    try:
        data = response.json()
        choice = data["choices"][0]
        if choice["finish_reason"] != "stop":
            raise ValueError("Incomplete response")
        prediction = json.loads(choice["message"]["content"])
        if not isinstance(prediction, dict):
            raise ValueError("Expected object")
        usage = data.get("usage") or {}
        tokens = {name: usage[field] for name, field in (
            ("input_tokens", "prompt_tokens"), ("output_tokens", "completion_tokens"),
            ("total_tokens", "total_tokens")) if type(usage.get(field)) is int}
        return {**prediction, "_usage": tokens} if tokens else prediction
    except (ValueError, TypeError, KeyError, IndexError):
        raise ProviderFailure("parsing", responded=True) from None
