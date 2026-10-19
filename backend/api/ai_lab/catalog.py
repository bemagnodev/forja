"""Reviewed candidates, not permission to execute or proof of account quota."""
from copy import deepcopy

MODELS = {
    "gemini-3.5-flash-lite": {"provider": "gemini", "key_env": "GEMINI_API_KEY", "label": "Gemini 3.5 Flash-Lite"},
    "gemini-3.8-flash": {"provider": "gemini", "key_env": "GEMINI_API_KEY", "label": "Gemini 3.8 Flash"},
    "openai/gpt-oss-120b": {"provider": "groq", "key_env": "GROQ_API_KEY", "label": "GPT-OSS 120B"},
    "openai/gpt-oss-20b": {"provider": "groq", "key_env": "GROQ_API_KEY", "label": "GPT-OSS 20B"},
    "qwen/qwen3.8-27b": {"provider": "groq", "key_env": "GROQ_API_KEY", "label": "Qwen 3.8 27B (preview)"},
}


def get_model(provider: str, model: str) -> dict:
    entry = MODELS.get(model)
    if entry is None or entry["provider"] != provider:
        raise ValueError("Unreviewed provider/model combination")
    return deepcopy(entry)
