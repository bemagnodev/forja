"""Single-problem bridge to the benchmark adapters; never retries or falls back."""
from .catalog import MODELS
from .classification import get_generator, load_prompt
from .contracts import normalize_tags
from .product import PRODUCT_PROMPT_VERSION, PRODUCT_RATING_DOMAIN, validate_product_prediction
from .dataset import content_hash
from api.services.scrapers.preparation import prepare_input

DEFAULT_MODEL = "gemini-3.5-flash-lite"
DEFAULT_PROMPT_VERSION = PRODUCT_PROMPT_VERSION
EXPLORE_MODELS = (DEFAULT_MODEL, "openai/gpt-oss-120b", "openai/gpt-oss-20b")


def resolve_model(model_name=None):
    model = model_name or DEFAULT_MODEL
    if model not in EXPLORE_MODELS:
        raise ValueError("Modelo indisponível no Explorar")
    return model


def classify_problem(problem_data: dict, model_name=None) -> dict:
    model = resolve_model(model_name)
    prepared = prepare_input(problem_data)
    prompt = load_prompt(DEFAULT_PROMPT_VERSION)
    visual_status = "unprocessed" if prepared.get("images") else "not_applicable"
    textual_input = {key: value for key, value in prepared.items() if key != "images"}
    raw = get_generator(MODELS[model]["provider"], model)(textual_input, prompt, model)
    prediction = validate_product_prediction(raw)
    # Presentation may retain known tags; the benchmark validator remains strict.
    display_tags, discarded = set(), 0
    raw_tags = raw.get("tags") if isinstance(raw, dict) else None
    for tag in raw_tags if isinstance(raw_tags, list) else []:
        try:
            display_tags.update(normalize_tags([tag]))
        except ValueError:
            discarded += 1
    reasoning = prediction["justification"]
    if visual_status == "unprocessed":
        reasoning = "Avaliação parcial: imagem(ns) não processada(s) pelo modelo. " + reasoning
    return {"visual_status": visual_status, "predicted_rating": prediction["rating"], "predicted_tags": sorted(display_tags),
            "reasoning": reasoning, "model": model,
            "prompt_version": DEFAULT_PROMPT_VERSION, "prompt_hash": content_hash(prompt),
            "rating_domain": PRODUCT_RATING_DOMAIN,
            "rating_status": prediction["rating_status"], "tags_status": prediction["tags_status"],
            "discarded_tags_count": discarded}
