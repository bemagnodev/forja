from pathlib import Path
from statistics import median

from .contracts import TAGS


def get_generator(provider: str, model: str):
    from .catalog import get_model

    get_model(provider, model)
    if provider == "gemini":
        from .providers.gemini import generate
    else:
        from .providers.groq import generate
    return generate


def load_prompt() -> str:
    template = (Path(__file__).parent / "prompts/classification_v1.txt").read_text(encoding="utf-8")
    return template.replace("{taxonomy}", ", ".join(sorted(TAGS)))


BASELINE_MODEL = "development-median-grid100-half-up-v2"


def median_baseline(development_ratings: list[int]) -> int:
    """Fit on development only; nearest 100, exact halfway ties upward."""
    if not development_ratings:
        raise ValueError("Development ratings required")
    return int((median(development_ratings) + 50) // 100) * 100


def baseline_predictions(manifest: dict, development: dict) -> dict:
    from .dataset import require_frozen

    require_frozen(manifest)
    require_frozen(development)
    if development["split"] != "development":
        raise ValueError("Baseline must be fitted on development")
    if manifest["split"] == "final" and manifest["development_hash"] != development["hash"]:
        raise ValueError("Baseline development version mismatch")
    rating = median_baseline([item["reference"]["rating"] for item in development["items"]])
    return {item["key"]: {"rating": rating, "rating_status": "valid", "tags": None,
                          "tags_status": "not_applicable", "responded": True, "duration": 0}
            for item in manifest["items"]}
