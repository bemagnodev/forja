"""Read only explicitly selected runs; never expose source texts or raw responses."""
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from .catalog import MODELS
from .dataset import content_hash, require_frozen, validate_version
from .metrics import compare_runs, compare_by_band, LEGACY_TAG_SCORING

# Explicitly reviewed instructions, not permission to publish arbitrary run config.
REVIEWED_PROMPTS = {
    "classification_v1": {
        "label": "Classificação direta",
        "description": "Zero-shot: classificação sem exemplos, com instruções diretas.",
        "hash": "5576561769e942d91809d84b8f5f302d3e675bf382be34c83ac6ffa8a9a5bb59",
    },
    "classification_v2": {
        "label": "Classificação com rubrica",
        "description": "Rubric prompting: critérios explícitos e referências de dificuldade. Também é zero-shot, sem exemplos.",
        "hash": "00530909483497aca36c87770e3c85874d7602b2602e3a1212dc8e8980f7515b",
    },
}

PRIVATE_PROMPTS = {
    "classification_v3": {
        "label": "C · Exemplos",
        "description": "Few-shot: quatro exemplos revisados, separados das questões e dos contests avaliados.",
        "hash": "bc18e8aa0bbb54625d255de6ca04f205513a9ab53a553fc3d3104d9a1294d392",
    },
}


def _identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", value):
        raise ValueError("Invalid artifact identifier")
    return value


def _read(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Artifact outside showcase root")
    return json.loads(path.read_text(encoding="utf-8"))


def list_benchmarks(root: Path) -> list[dict]:
    if not (root / "showcase.json").exists():
        return []
    entries = _read(root, "showcase.json")["benchmarks"]
    result, seen = [], set()
    for entry in entries:
        identifier = _identifier(entry["id"])
        if identifier in seen or entry["split"] not in ("development", "final"):
            raise ValueError("Invalid showcase index")
        seen.add(identifier)
        result.append({"id": identifier, "label": str(entry["label"]),
                       "version": validate_version(entry["version"]), "split": entry["split"]})
    return result


def _operation_history(root, run_id, run):
    attempts, failures, seen = 0, Counter(), set()
    while True:
        if run_id in seen:
            raise ValueError("Cyclic run provenance")
        seen.add(run_id)
        attempts += run.get("request_count", 0)
        for key, prediction in run["predictions"].items():
            events = run.get("attempt_history", {}).get(key) or [prediction]
            failures.update(event["error"] for event in events if event.get("error"))
        provenance = run.get("provenance") or {}
        if not provenance.get("original_run"):
            return attempts, dict(failures)
        run_id = _identifier(provenance["original_run"])
        relative = f"runs/{run_id}/run.json"
        original = _read(root, relative)
        digest = hashlib.sha256((root / relative).read_bytes()).hexdigest()
        if (digest != provenance.get("original_run_sha256")
                or original["dataset_hash"] != run["dataset_hash"]
                or original["configuration"] != run["configuration"]):
            raise ValueError("Run provenance mismatch")
        run = original


def read_benchmark(root: Path, benchmark_id: str) -> dict:
    _identifier(benchmark_id)
    listing = {entry["id"]: entry for entry in list_benchmarks(root)}
    if benchmark_id not in listing:
        raise LookupError("Unknown benchmark")
    entry = next(e for e in _read(root, "showcase.json")["benchmarks"] if e["id"] == benchmark_id)
    version, split = listing[benchmark_id]["version"], entry["split"]
    manifest = _read(root, f"datasets/{version}/{split}/manifest.json")
    require_frozen(manifest)
    if manifest["version"] != version or manifest["split"] != split:
        raise ValueError("Dataset identity mismatch")
    run_ids = entry["runs"]
    if not run_ids or len(set(run_ids)) != len(run_ids):
        raise ValueError("Unique runs required")
    loaded, prompt_hashes = {}, set()
    keys = {item["key"] for item in manifest["items"]}
    for run_id in run_ids:
        _identifier(run_id)
        run = _read(root, f"runs/{run_id}/run.json")
        if run["dataset_hash"] != manifest["hash"] or not set(run["predictions"]).issubset(keys):
            raise ValueError("Incompatible run dataset")
        config = run["configuration"]
        if config["provider"] != "baseline":
            if content_hash(config["prompt"]) != config["prompt_hash"]:
                raise ValueError("Prompt hash mismatch")
            prompt_hashes.add(config["prompt_hash"])
        loaded[run_id] = run
    multiple_prompts = len(prompt_hashes) > 1
    if multiple_prompts and entry.get("compare_prompts") is not True:
        raise ValueError("Compare one prompt at a time")
    references = {item["key"]: item["reference"] for item in manifest["items"]}
    report = compare_runs(references, {key: run["predictions"] for key, run in loaded.items()},
                          tag_scoring=entry.get("tag_scoring", LEGACY_TAG_SCORING))
    labels = entry.get("run_labels", {})
    if (not isinstance(labels, dict) or not set(labels).issubset(run_ids)
            or any(not isinstance(label, str) or not label.strip() for label in labels.values())):
        raise ValueError("Invalid configuration labels")
    runs = []
    for run_id, run in loaded.items():
        config = run["configuration"]
        attempts, failures = _operation_history(root, run_id, run)
        runs.append({"id": run_id, "provider": config["provider"], "model": config["model"],
                     "label": "Baseline · mediana" if config["provider"] == "baseline" else MODELS.get(config["model"], {}).get("label", config["model"]),
                     "metrics": report["runs"][run_id], "generation_attempts": attempts,
                     "historical_failures": failures})
        if config["provider"] != "baseline":
            runs[-1].update(prompt_hash=config["prompt_hash"], prompt_version=config.get("prompt_version"))
            strategy = REVIEWED_PROMPTS.get(config.get("prompt_version")) or PRIVATE_PROMPTS.get(config.get("prompt_version"))
            if strategy:
                runs[-1]["strategy_label"] = strategy["label"]
            if multiple_prompts:
                runs[-1]["label"] += " · " + (strategy["label"] if strategy else config.get("prompt_version") or config["prompt_hash"][:8])
            level = config.get("generation", {}).get("thinking_level")
            if level in ("minimal", "low", "medium", "high"):
                parameters = {"thinking_level": level}
                timeout = config.get("timeout_seconds")
                if type(timeout) in (int, float) and 0 < timeout <= 120:
                    parameters["timeout_seconds"] = timeout
                runs[-1]["parameters"] = parameters
                tokens, available = Counter(), 0
                for key in report["rating_intersection"]:
                    usage = run["predictions"][key].get("raw", {}).get("_usage", {})
                    safe = {name: value for name, value in usage.items()
                            if name in ("input_tokens", "output_tokens", "total_tokens", "thinking_tokens")
                            and type(value) is int and value >= 0}
                    if "total_tokens" in safe:
                        tokens.update(safe)
                        available += 1
                if available:
                    runs[-1]["token_usage"] = {**tokens, "items_with_usage": available,
                                              "compared_items": len(report["rating_intersection"])}
        if run_id in labels:
            runs[-1]["label"] = labels[run_id]
    problems = []
    fields = ("rating", "rating_status", "tags", "tags_status", "justification", "responded", "duration", "error")
    for key, reference in references.items():
        predictions = {}
        for run_id, run in loaded.items():
            prediction = run["predictions"].get(key)
            predictions[run_id] = ({field: prediction.get(field) for field in fields} if prediction else {
                "rating_status": "pending", "tags_status": "pending", "responded": False})
        problems.append({"key": key, "reference": reference, "predictions": predictions})
    presentation = {}
    for name in ("description", "conclusion"):
        if name in entry:
            if not isinstance(entry[name], str):
                raise ValueError("Invalid presentation metadata")
            presentation[name] = entry[name]
    if "selection_note" in entry:
        if not isinstance(entry["selection_note"], str):
            raise ValueError("Invalid selection note")
        presentation["selection_note"] = entry["selection_note"]
    if entry.get("publish_prompts") is True:
        prompts = {}
        for run in loaded.values():
            config = run["configuration"]
            if config["provider"] == "baseline":
                continue
            prompt_version = config.get("prompt_version")
            private = prompt_version in PRIVATE_PROMPTS
            reviewed = PRIVATE_PROMPTS.get(prompt_version) if private else REVIEWED_PROMPTS.get(prompt_version)
            if reviewed is None or config["prompt_hash"] != reviewed["hash"]:
                raise ValueError("Publication requires an explicitly reviewed prompt")
            descriptor = {**reviewed, "version": prompt_version}
            descriptor.update({"private_examples": True} if private else {"text": config["prompt"]})
            prompts.setdefault(config["prompt_hash"], descriptor)
        presentation["prompts"] = list(prompts.values())
    return {**listing[benchmark_id], **presentation, "tag_scoring": report["tag_scoring"],
            "dataset": {"version": version, "split": split,
            "hash": manifest["hash"], "seed": manifest["seed"], "total": len(keys)},
            "prompt": {"hash": next(iter(prompt_hashes), None) if not multiple_prompts else None}, "runs": runs, "problems": problems,
            "bands": compare_by_band(references, {key: run["predictions"] for key, run in loaded.items()}),
            "intersections": {"rating": report["rating_intersection"], "tags": report["tags_intersection"]}}


def _pick(value, fields):
    return {key: value[key] for key in fields if key in value}


def export_snapshot(root: Path, benchmark_id: str, output: Path, *, include_justifications=False) -> None:
    """Explicit export, never inference. Review the resulting file before publishing."""
    source = read_benchmark(root, benchmark_id)
    data = _pick(source, ("id", "label", "version", "split", "selection_note", "prompts", "description", "conclusion", "tag_scoring"))
    data["dataset"] = _pick(source["dataset"], ("version", "split", "hash", "seed", "total"))
    data["prompt"] = _pick(source["prompt"], ("hash",))
    data["intersections"] = _pick(source["intersections"], ("rating", "tags"))
    metrics = ("mae", "within_200", "tags_micro_f1", "pending", "responded", "latency_median",
               "rating_valid", "rating_coverage", "rating_failure_rate", "rating_failures",
               "tags_valid", "tags_coverage", "tags_failure_rate", "tags_failures",
               "tags_true_positive", "tags_false_positive", "tags_false_negative", "tags_evaluated")
    data["runs"] = [{**_pick(run, ("id", "label", "provider", "model", "prompt_hash", "prompt_version", "strategy_label", "generation_attempts", "historical_failures", "parameters", "token_usage")),
                     "metrics": _pick(run["metrics"], metrics)} for run in source["runs"]]
    data["bands"] = [{**_pick(band, ("label", "total", "compared")),
                      "mae": {run["id"]: band["mae"][run["id"]] for run in data["runs"]}}
                     for band in source["bands"]]
    fields = ("rating", "rating_status", "tags", "tags_status", "responded")
    if include_justifications:
        fields += ("justification",)
    data["problems"] = [{"key": row["key"], "reference": _pick(row["reference"], ("rating", "tags")),
                         "predictions": {key: _pick(value, fields) for key, value in row["predictions"].items()}}
                        for row in source["problems"]]
    envelope = {"schema_version": 1, "content_hash": content_hash(data), "comparison": data}
    encoded = json.dumps(envelope, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as file:
        file.write(encoded + "\n")


def read_snapshot(root: Path, benchmark_id: str) -> dict:
    _identifier(benchmark_id)
    selected = _published_ids(root)
    if selected is not None and benchmark_id not in selected:
        raise LookupError("Benchmark outside published selection")
    if not (root / f"{benchmark_id}.json").exists():
        raise LookupError("Unknown benchmark")
    try:
        envelope = _read(root, f"{benchmark_id}.json")
        data = envelope["comparison"]
        if (envelope["schema_version"] != 1 or data["id"] != benchmark_id
                or content_hash(data) != envelope["content_hash"]):
            raise ValueError("Snapshot identity or integrity mismatch")
        return data
    except (KeyError, TypeError) as exc:
        raise ValueError("Invalid published snapshot") from exc


def list_snapshots(root: Path) -> list[dict]:
    selected = _published_ids(root)
    if selected is None:  # Legacy snapshot folders remain readable without a manifest.
        selected = [path.stem for path in sorted(root.glob("*.json"))]
    return [_pick(read_snapshot(root, identifier), ("id", "label", "version", "split")) for identifier in selected]


def _published_ids(root: Path):
    if not (root / "index.json").exists():
        return None
    index = _read(root, "index.json")
    if not isinstance(index, dict):
        raise ValueError("Invalid published index")
    ids = index.get("benchmarks")
    if not isinstance(ids, list):
        raise ValueError("Published index must list benchmark identifiers")
    ids = [_identifier(identifier) for identifier in ids]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate published benchmark")
    return ids
