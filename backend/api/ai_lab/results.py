"""Read only explicitly selected runs; never expose source texts or raw responses."""
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from .catalog import MODELS
from .dataset import content_hash, require_frozen, validate_version
from .metrics import compare_runs, compare_by_band


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
    if len(prompt_hashes) > 1:
        raise ValueError("Compare one prompt at a time")
    references = {item["key"]: item["reference"] for item in manifest["items"]}
    report = compare_runs(references, {key: run["predictions"] for key, run in loaded.items()})
    runs = []
    for run_id, run in loaded.items():
        config = run["configuration"]
        attempts, failures = _operation_history(root, run_id, run)
        runs.append({"id": run_id, "provider": config["provider"], "model": config["model"],
                     "label": "Baseline · mediana" if config["provider"] == "baseline" else MODELS.get(config["model"], {}).get("label", config["model"]),
                     "metrics": report["runs"][run_id], "generation_attempts": attempts,
                     "historical_failures": failures})
    problems = []
    fields = ("rating", "rating_status", "tags", "tags_status", "justification", "responded", "duration", "error")
    for key, reference in references.items():
        predictions = {}
        for run_id, run in loaded.items():
            prediction = run["predictions"].get(key)
            predictions[run_id] = ({field: prediction.get(field) for field in fields} if prediction else {
                "rating_status": "pending", "tags_status": "pending", "responded": False})
        problems.append({"key": key, "reference": reference, "predictions": predictions})
    return {**listing[benchmark_id], "dataset": {"version": version, "split": split,
            "hash": manifest["hash"], "seed": manifest["seed"], "total": len(keys)},
            "prompt": {"hash": next(iter(prompt_hashes), None)}, "runs": runs, "problems": problems,
            "bands": compare_by_band(references, {key: run["predictions"] for key, run in loaded.items()}),
            "intersections": {"rating": report["rating_intersection"], "tags": report["tags_intersection"]}}


def _pick(value, fields):
    return {key: value[key] for key in fields if key in value}


def export_snapshot(root: Path, benchmark_id: str, output: Path, *, include_justifications=False) -> None:
    """Explicit export, never inference. Review the resulting file before publishing."""
    source = read_benchmark(root, benchmark_id)
    data = _pick(source, ("id", "label", "version", "split"))
    data["dataset"] = _pick(source["dataset"], ("version", "split", "hash", "seed", "total"))
    data["prompt"] = _pick(source["prompt"], ("hash",))
    data["intersections"] = _pick(source["intersections"], ("rating", "tags"))
    metrics = ("mae", "within_200", "tags_micro_f1", "pending", "responded", "latency_median",
               "rating_valid", "rating_coverage", "rating_failure_rate", "rating_failures",
               "tags_valid", "tags_coverage", "tags_failure_rate", "tags_failures")
    data["runs"] = [{**_pick(run, ("id", "label", "provider", "model", "generation_attempts", "historical_failures")),
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
    return [_pick(read_snapshot(root, path.stem), ("id", "label", "version", "split"))
            for path in sorted(root.glob("*.json"))]
