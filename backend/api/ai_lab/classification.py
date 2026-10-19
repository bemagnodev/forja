from pathlib import Path
from statistics import median
import json

from .contracts import TAGS


def get_generator(provider: str, model: str):
    from .catalog import get_model

    get_model(provider, model)
    if provider == "gemini":
        from .providers.gemini import generate
    else:
        from .providers.groq import generate
    return generate


def load_prompt(version: str = "classification_v1", *, examples_path=None, development=None, evaluation=None, with_metadata=False):
    import re
    if not isinstance(version, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", version):
        raise ValueError("Invalid prompt version")
    template = (Path(__file__).parent / "prompts" / f"{version}.txt").read_text(encoding="utf-8")
    template = template.replace("{taxonomy}", ", ".join(sorted(TAGS)))
    metadata = {}
    if "{examples}" in template:
        if examples_path is None or development is None or evaluation is None:
            raise ValueError("Prompt examples require a private file, development and evaluation datasets")
        blocks, examples_hash = render_examples(examples_path, development, evaluation)
        template = template.replace("{examples}", blocks)
        metadata = {"examples_hash": examples_hash, "examples_development_hash": development["hash"]}
    elif examples_path is not None:
        raise ValueError("This prompt does not accept examples")
    return (template, metadata) if with_metadata else template


def render_examples(path, development: dict, evaluation: dict) -> tuple[str, str]:
    """Validate private demonstrations against reviewed references before rendering."""
    from .dataset import require_frozen, content_hash, BANDS
    from .contracts import validate_prediction
    require_frozen(development)
    require_frozen(evaluation)
    if (development["split"] != "development" or development["version"] != evaluation["version"]
            or (evaluation["split"] == "final" and evaluation["development_hash"] != development["hash"])):
        raise ValueError("Examples development/evaluation identity mismatch")
    artifact = json.loads(Path(path).read_text(encoding="utf-8"))
    if (not isinstance(artifact, dict) or type(artifact.get("schema_version")) is not int
            or artifact["schema_version"] != 1 or artifact.get("development_hash") != development["hash"]):
        raise ValueError("Invalid examples provenance")
    examples = artifact.get("examples")
    if not isinstance(examples, list) or len(examples) != 4:
        raise ValueError("Exactly four examples required")
    source = {item["key"]: item for item in development["items"]}
    evaluation_keys = {item["key"] for item in evaluation["items"]}
    evaluation_contests = {item["contest_id"] for item in evaluation["items"]}
    seen, bands, blocks = set(), [], []
    for example in examples:
        if not isinstance(example, dict) or not isinstance(example.get("key"), str):
            raise ValueError("Invalid example identity")
        key = example["key"]
        if key not in source or key in seen:
            raise ValueError("Unknown or duplicate example")
        seen.add(key)
        item = source[key]
        if key in evaluation_keys or item["contest_id"] in evaluation_contests:
            raise ValueError("Example overlap with evaluation dataset")
        output = example.get("output")
        if (example.get("input") != item["input"] or not isinstance(output, dict)
                or set(output) != {"rating", "tags", "justification"}):
            raise ValueError("Example input/output differs from reviewed contract")
        validated = validate_prediction(output)
        if (validated["rating_status"] != "valid" or validated["tags_status"] != "valid"
                or output["rating"] != item["reference"]["rating"]
                or validated["tags"] != sorted(item["reference"]["tags"])
                or not isinstance(output["justification"], str) or not output["justification"].strip()):
            raise ValueError("Example must use official references and a reviewed explanation")
        bands.append(next(i for i, (lo, hi) in enumerate(BANDS) if lo <= output["rating"] <= hi))
        # Preserve JSON semantics while preventing statement text from closing delimiters.
        def encode(value):
            return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e")
        blocks.append("<example>\n<input>\n" + encode(item["input"]) + "\n</input>\n<output>\n"
                      + encode(output) + "\n</output>\n</example>")
    if bands != [0, 1, 2, 3]:
        raise ValueError("Examples must contain one per rating band in ascending order")
    return "\n\n".join(blocks), content_hash(artifact)


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
