"""Product contract; benchmark validation and its 800–2400 domain stay unchanged."""
from .contracts import normalize_tags

PRODUCT_PROMPT_VERSION = "product_classification_v1"
PRODUCT_RATING_DOMAIN = "cf-rating-800-3500-grid100-v1"


def validate_product_prediction(raw) -> dict:
    data = raw if isinstance(raw, dict) else {}
    rating = data.get("rating")
    if type(rating) is not int:
        status = "invalid_output"
    elif not 800 <= rating <= 3500:
        status = "out_of_domain"
    else:
        status = "invalid_output" if rating % 100 else "valid"
    try:
        tags, tags_status = normalize_tags(data.get("tags")), "valid"
    except ValueError:
        tags, tags_status = None, "invalid_output"
    return {"raw": raw, "rating": rating if status == "valid" else None,
            "rating_status": status, "tags": tags, "tags_status": tags_status,
            "justification": data.get("justification") if isinstance(data.get("justification"), str) else ""}
