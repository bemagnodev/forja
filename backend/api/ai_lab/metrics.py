"""Pure metrics with separate validity intersections for rating and tags."""

from statistics import median

RATING_BANDS = ((800, 1100), (1200, 1500), (1600, 1900), (2000, 2400))


def compare_by_band(references: dict, runs: dict) -> list[dict]:
    result = []
    for low, high in RATING_BANDS:
        selected = {key: ref for key, ref in references.items() if low <= ref["rating"] <= high}
        report = compare_runs(selected, runs)
        result.append({"label": f"{low}–{high}", "total": len(selected),
                       "compared": len(report["rating_intersection"]),
                       "mae": {key: metrics["mae"] for key, metrics in report["runs"].items()}})
    return result


def compare_runs(references: dict, runs: dict) -> dict:
    keys, total = set(references), len(references)
    intersections = {}
    for task in ("rating", "tags"):
        valid = [{k for k, p in run.items() if k in keys and p.get(f"{task}_status") == "valid"}
                 for run in runs.values()
                 if not run or not all(p.get(f"{task}_status") == "not_applicable" for p in run.values())]
        intersections[task] = sorted(set.intersection(*valid)) if valid else []
    report = {"rating_intersection": intersections["rating"], "tags_intersection": intersections["tags"], "total": total, "runs": {}}
    for name, predictions in runs.items():
        rows = {k: predictions[k] for k in keys if k in predictions}
        rating_keys, tag_keys = intersections["rating"], intersections["tags"]
        errors = [abs(rows[k]["rating"] - references[k]["rating"]) for k in rating_keys]
        tp = fp = fn = 0
        tags_applicable = not rows or not all(p.get("tags_status") == "not_applicable" for p in rows.values())
        for key in tag_keys if tags_applicable else []:
            actual, predicted = set(references[key]["tags"]), set(rows[key]["tags"])
            tp += len(actual & predicted)
            fp += len(predicted - actual)
            fn += len(actual - predicted)
        durations = [p["duration"] for p in rows.values() if p.get("responded") and p.get("duration") is not None]
        result = {"mae": sum(errors) / len(errors) if errors else None,
                  "within_200": sum(e <= 200 for e in errors) / len(errors) if errors else None,
                  "tags_micro_f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None,
                  "pending": total - len(rows), "responded": sum(bool(p.get("responded")) for p in rows.values()),
                  "latency_median": median(durations) if durations else None}
        for task in ("rating", "tags"):
            if task == "tags" and not tags_applicable:
                result.update(tags_valid=None, tags_coverage=None, tags_failure_rate=None, tags_failures={})
                continue
            valid_count = sum(p.get(f"{task}_status") == "valid" for p in rows.values())
            failures = {}
            for row in rows.values():
                status = row.get(f"{task}_status", "invalid_output")
                if status != "valid":
                    failures[status] = failures.get(status, 0) + 1
            result.update({f"{task}_valid": valid_count,
                           f"{task}_coverage": valid_count / total if total else None,
                           f"{task}_failure_rate": (len(rows) - valid_count) / total if total else None,
                           f"{task}_failures": failures})
        report["runs"][name] = result
    return report
