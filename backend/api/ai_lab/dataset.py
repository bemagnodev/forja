"""Dataset preparation. References never belong to model input."""

import hashlib
import json
import random
import re
from collections import Counter
from datetime import datetime, timezone

from api.services.scrapers.codeforces import CodeforcesScraper
from api.services.scrapers.preparation import INPUT_FIELDS, prepare_input as prepare_classification_input

from .contracts import normalize_tags, TAXONOMY_VERSION

BANDS = ((800, 1100), (1200, 1500), (1600, 1900), (2000, 2400))


def validate_version(version: str) -> str:
    if (not isinstance(version, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}", version)
            or ".." in version or version.endswith(".")):
        raise ValueError("Invalid dataset version")
    return version


def require_dataset_version(manifest: dict, version: str) -> None:
    if manifest.get("version") != validate_version(version):
        raise ValueError("Dataset version does not match requested version")


def content_hash(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def select_items(catalog: dict, per_band: int, seed: int = 42, exclude_contests=(), *, exclude_problems=()) -> list:
    """Stable stratified draw, capped at two problems per contest overall."""
    if type(per_band) is not int or per_band < 1:
        raise ValueError("per_band must be positive")
    unique = {}
    for problem in catalog["problems"]:
        rating, contest = problem.get("rating"), problem.get("contestId")
        if (type(rating) is not int or rating % 100 or not 800 <= rating <= 2400
                or type(contest) is not int or not 0 < contest < 100000
                or contest in exclude_contests or not isinstance(problem.get("index"), str)
                or not re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", problem["index"])
                or not problem.get("tags") or "interactive" in problem["tags"]
                or problem.get("type", "PROGRAMMING") != "PROGRAMMING"):
            continue
        key = (contest, problem["index"])
        if key in unique and unique[key] != problem:
            raise ValueError(f"Conflicting duplicate: {key}")
        unique[key] = problem
    candidates = [unique[key] for key in sorted(unique)]
    random.Random(seed).shuffle(candidates)
    counts, contests, selected = Counter(), Counter(), []
    for problem in candidates:
        if (problem["contestId"], problem["index"]) in exclude_problems:
            continue
        band = next(i for i, (lo, hi) in enumerate(BANDS) if lo <= problem["rating"] <= hi)
        contest = problem["contestId"]
        if counts[band] < per_band and contests[contest] < 2:
            selected.append(problem.copy())
            counts[band] += 1
            contests[contest] += 1
    if any(counts[i] != per_band for i in range(4)):
        raise ValueError(f"insufficient candidates: selected per band {dict(counts)}")
    return selected


def prepare_input(statement: dict) -> dict:
    return prepare_classification_input(statement, strict=True)


def require_reviewed(item: dict) -> None:
    review, value = item.get("review", {}), item.get("input", {})
    if value.get("images"):
        raise ValueError("Visual content requires a multimodal benchmark protocol")
    if (not review.get("reviewer") or not review.get("reviewed_at")
            or review.get("hash") != content_hash(value)
            or prepare_input(value) != value):
        raise ValueError("Input requires review for its current hash")


def record_review(item: dict, reviewer: str, reviewed_at: str) -> None:
    if not reviewer.strip():
        raise ValueError("reviewer required")
    datetime.fromisoformat(reviewed_at)
    item["review"] = {"reviewer": reviewer, "reviewed_at": reviewed_at, "hash": content_hash(item["input"])}


def freeze_manifest(manifest: dict) -> None:
    validate_manifest_shape(manifest)
    for item in manifest["items"]:
        require_reviewed(item)
    manifest["state"] = "frozen"
    manifest["hash"] = content_hash({k: v for k, v in manifest.items() if k != "hash"})


def require_frozen(manifest: dict) -> None:
    if manifest.get("state") != "frozen":
        raise ValueError("Dataset requires review and freezing")
    expected = content_hash({k: v for k, v in manifest.items() if k != "hash"})
    if manifest.get("hash") != expected:
        raise ValueError("Dataset hash changed")
    validate_manifest_shape(manifest)
    for item in manifest["items"]:
        require_reviewed(item)


def validate_manifest_shape(manifest: dict) -> None:
    from .contracts import validate_prediction

    split = manifest.get("split")
    expected_per_band = {"development": 3, "final": 15}.get(split)
    items = manifest.get("items", [])
    if not expected_per_band or len(items) != 4 * expected_per_band:
        raise ValueError("Dataset count does not match split")
    counts, contests = Counter(), Counter()
    keys = set()
    for item in items:
        reference = validate_prediction(item["reference"])
        if reference["rating_status"] != "valid" or reference["tags_status"] != "valid":
            raise ValueError("Invalid reference")
        rating = reference["rating"]
        counts[next(i for i, (lo, hi) in enumerate(BANDS) if lo <= rating <= hi)] += 1
        contests[item["contest_id"]] += 1
        keys.add(item["key"])
        if item["input_hash"] != content_hash(item["input"]):
            raise ValueError("Input hash changed; recollect and review")
    if len(keys) != len(items) or max(contests.values()) > 2 or any(counts[i] != expected_per_band for i in range(4)):
        raise ValueError("Dataset count, quotas or contest limit violated")


def build_manifest(catalog: dict, fetch_html, split="development", seed=42, development=None, version="cf-rating-v1") -> dict:
    validate_version(version)
    if split not in ("development", "final"):
        raise ValueError("Unknown split")
    excluded_contests = set()
    if split == "final":
        if not development or development.get("split") != "development":
            raise ValueError("Frozen development dataset required")
        require_dataset_version(development, version)
        require_frozen(development)
        excluded_contests = {item["contest_id"] for item in development["items"]}
    excluded_problems = set()
    cached, exclusions = {}, []
    while True:
        selected = select_items(catalog, 3 if split == "development" else 15, seed, excluded_contests,
                                exclude_problems=excluded_problems)
        failed = set()
        for p in selected:
            key = f'{p["contestId"]}{p["index"]}'
            if key in cached:
                continue
            url = f'https://codeforces.com/contest/{p["contestId"]}/problem/{p["index"]}'
            # A transport failure must stop the collection, not bias it toward accessible items.
            html = fetch_html(url)
            try:
                value = prepare_input(CodeforcesScraper.parse_html(html, url))
                if value.get("images"):
                    raise ValueError("Visual content requires a multimodal benchmark protocol")
                tags = normalize_tags(p["tags"])
            except ValueError as exc:
                failed.add((p["contestId"], p["index"]))
                exclusions.append({"key": key, "url": url, "reason": str(exc)})
                continue
            cached[key] = {"key": key, "contest_id": p["contestId"], "source_url": url,
                           "input": value, "input_hash": content_hash(value),
                           "reference": {"rating": p["rating"], "tags": tags}, "review": {}}
        if not failed:
            break
        excluded_problems.update(failed)
    return {"version": version, "split": split, "state": "collected", "seed": seed,
            "algorithm": "stratified-v2-stable-replacement", "catalog_hash": content_hash(catalog),
            "taxonomy": TAXONOMY_VERSION, "collected_at": datetime.now(timezone.utc).isoformat(),
            "development_hash": development["hash"] if development else None,
            "excluded": exclusions,
            "items": [cached[f'{p["contestId"]}{p["index"]}'] for p in selected]}


def parse_statement(html: str) -> dict:
    """Compatibility entry point; parsing belongs to CodeforcesScraper."""
    return CodeforcesScraper.parse_html(html)
