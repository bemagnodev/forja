"""Local-only experiment execution and environment checks."""

from pathlib import Path
import json
import time
import random
import math
import builtins
from datetime import datetime, timezone
from django.core.management import BaseCommand, CommandError

from .classification import load_prompt
from .contracts import ProviderFailure, validate_prediction
from .dataset import content_hash, require_frozen, validate_version


class LocalDatasetCommand(BaseCommand):
    """Shared local dataset options; preserve Django's built-in --version."""
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument("--dataset-version", default="cf-rating-v1", help="Dataset version (default: cf-rating-v1)")


def command_version(options: dict) -> str:
    try:
        return validate_version(options["dataset_version"])
    except ValueError as exc:
        raise CommandError(str(exc)) from None


def require_local_environment(settings_name: str, database: dict, root: Path) -> None:
    if settings_name != "core.settings_ai_lab_local":
        raise ValueError("Explicit local AI Lab settings required")
    path = Path(str(database.get("NAME", "")))
    if (database.get("ENGINE") != "django.db.backends.sqlite3" or database.get("HOST")
            or not path.is_absolute() or not path.resolve().is_relative_to(root.resolve())
            or path.suffix != ".sqlite3"):
        raise ValueError("Explicit local SQLite file under AI Lab root required")


def guarded_root(options: dict) -> Path:
    from django.conf import settings
    from django.core.management import CommandError

    try:
        if settings.SETTINGS_MODULE != options.get("settings"):
            raise ValueError("Explicit local settings required")
        root = Path(settings.BASE_DIR) / "var" / "ai_lab"
        require_local_environment(options.get("settings"), settings.DATABASES["default"], root)
    except ValueError as exc:
        raise CommandError(str(exc)) from None
    return root


def save_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def _record_unexpected_error(run, exc):
    name = type(exc).__name__
    # Custom exception class names can also contain untrusted data.
    safe_type = name if getattr(builtins, name, None) is type(exc) else "Exception"
    run.update(stop_reason="unexpected_error", unexpected_error={
        "type": safe_type, "at": datetime.now(timezone.utc).isoformat()})


def run_local(manifest: dict, configuration: dict, path: Path, generate, *, sleep=time.sleep, max_requests=None, retry_failures=False, examples_path=None, development=None) -> dict:
    require_frozen(manifest)
    if configuration.get("execution_policy") == "managed-v1":
        if retry_failures:
            raise ValueError("Managed runs recover automatically; omit --retry-failures")
        return _run_managed(manifest, configuration, path, generate, sleep, max_requests, examples_path, development)
    if examples_path is not None:
        raise ValueError("Legacy runs do not accept examples")
    prompt = load_prompt()
    if max_requests is not None and (type(max_requests) is not int or max_requests < 1):
        raise ValueError("Positive request cap required")
    if retry_failures and (max_requests is None or not path.exists()):
        raise ValueError("Recovery requires an existing run and explicit request cap")
    config = {**configuration, "prompt": prompt, "prompt_hash": content_hash(prompt), "dataset_hash": manifest["hash"]}
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix(".lock")
    with lock.open("x"):
        pass
    executing = False
    try:
        if path.exists():
            run = json.loads(path.read_text(encoding="utf-8"))
            if run["configuration"] != config:
                raise ValueError("Run configuration changed; use a new run")
            previous_limit = run["authorized_request_limit"]
            if ((previous_limit is not None and (max_requests is None or max_requests < previous_limit))
                    or (max_requests is not None and max_requests < run["request_count"])):
                raise ValueError("Authorized request limit cannot decrease or discard consumed requests")
            run["authorized_request_limit"] = max_requests
        else:
            run = {"dataset_hash": manifest["hash"], "configuration": config, "predictions": {},
                   "request_count": 0, "authorized_request_limit": max_requests}
        executing = True
        save_json(path, run)
        for item in manifest["items"]:
            if max_requests is not None and run["request_count"] >= max_requests:
                return run
            key = item["key"]
            previous = run["predictions"].get(key)
            history = run.setdefault("attempt_history", {}).setdefault(key, [])
            if retry_failures:
                if (not previous or previous.get("error") not in ("timeout", "rate_limit", "server_error")
                        or max(previous.get("attempts", 1), len(history)) >= 2):
                    continue
                if not history:
                    history.append({**previous, "legacy": True})
            elif previous:
                continue
            wait_until = max(run.get("next_request_at", 0), previous.get("retry_not_before", 0) if retry_failures else 0)
            wait = max(0, wait_until - time.time())
            if wait > 30:
                return run
            if wait:
                sleep(wait)
            started = time.perf_counter()
            attempts = 0
            while True:
                attempts += 1
                # Persist before I/O: a crash cannot reset the authorized request budget.
                run["request_count"] += 1
                event = {"state": "started", "requested_at": time.time()}
                history.append(event)
                # Reserve the item as well as the budget: an unknown response must
                # not become an automatic duplicate request after a process crash.
                run["predictions"][key] = {
                    "rating": None, "tags": None, "rating_status": "transport_error",
                    "tags_status": "transport_error", "responded": False, "error": "interrupted",
                    "attempts": (previous.get("attempts", 1) if retry_failures else 0) + attempts,
                }
                save_json(path, run)
                try:
                    raw = generate(item["input"], prompt, config["model"])
                    prediction = {**validate_prediction(raw), "responded": True}
                    json.dumps(prediction, allow_nan=False)
                    break
                except ProviderFailure as exc:
                    delay = exc.retry_after if exc.retry_after is not None else 2 ** (attempts - 1)
                    status = "invalid_output" if exc.responded else "transport_error"
                    prediction = {"rating": None, "tags": None, "rating_status": status, "tags_status": status,
                                  "responded": exc.responded, "error": exc.category,
                                  "retry_not_before": time.time() + max(0, delay)}
                    if exc.http_status is not None:
                        prediction["http_status"] = exc.http_status
                    if config.get("max_attempts") == 1 and (exc.category == "rate_limit" or exc.retry_after is not None):
                        run["next_request_at"] = prediction["retry_not_before"]
                    event.update(prediction, state="finished")
                    under_cap = max_requests is None or run["request_count"] < max_requests
                    if not retry_failures and exc.category in ("timeout", "rate_limit", "server_error") and attempts < config.get("max_attempts", 3) and 0 <= delay <= 30 and under_cap:
                        save_json(path, run)
                        sleep(delay)
                        continue
                    break
            event.update(prediction, state="finished")
            prediction.update(duration=time.perf_counter() - started,
                              attempts=(previous.get("attempts", 1) if retry_failures else 0) + attempts)
            run["predictions"][key] = prediction
            save_json(path, run)
            if config.get("max_attempts") == 1 and prediction.get("error") in ("authentication", "provider_error", "rate_limit"):
                return run
        return run
    except Exception as exc:
        if executing:
            _record_unexpected_error(run, exc)
            save_json(path, run)
            raise RuntimeError("Unexpected benchmark error; inspect the saved run status") from None
        raise
    finally:
        lock.unlink()


def summarize_run(run: dict, total: int) -> dict:
    predictions = run["predictions"]
    history = run.get("attempt_history", {})
    return {"total": total, "processed": len(predictions), "pending": total - len(predictions),
            "requests": run.get("request_count", 0), "authorized_limit": run.get("authorized_request_limit"),
            "rating_valid": sum(p.get("rating_status") == "valid" for p in predictions.values()),
            "tags_valid": sum(p.get("tags_status") == "valid" for p in predictions.values()),
            "first_attempt_valid": sum(bool(events) and events[0].get("rating_status") == "valid"
                                       for events in history.values()) if "attempt_history" in run else None,
            "stop_reason": run.get("stop_reason", "legacy"), "next_request_at": run.get("next_request_at")}


def _run_managed(manifest, configuration, path, generate, sleep, max_requests, examples_path=None, development=None):
    """Versioned policy for new runs only; old pilots retain their original behavior."""
    if configuration.get("prompt_version", "").startswith("product_"):
        raise ValueError("Product prompts cannot be used in benchmark runs")
    if type(max_requests) is not int or max_requests < 1:
        raise ValueError("Positive request cap required")
    attempts_limit = configuration.get("max_attempts", 3)
    interval, max_wait = configuration.get("request_interval", 5), configuration.get("max_wait", 60)
    if type(attempts_limit) is not int or not 1 <= attempts_limit <= 3:
        raise ValueError("max_attempts must be between 1 and 3")
    if any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in (interval, max_wait)) or max_wait > 60:
        raise ValueError("Invalid interval or max_wait (0..60 seconds)")
    metadata = {}
    if examples_path is not None:
        prompt, metadata = load_prompt(configuration["prompt_version"], examples_path=examples_path,
                                       development=development, evaluation=manifest, with_metadata=True)
    else:
        prompt = load_prompt(configuration["prompt_version"])
    config = {**configuration, **metadata, "prompt": prompt, "prompt_hash": content_hash(prompt), "dataset_hash": manifest["hash"]}
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix(".lock")
    with lock.open("x"):
        pass
    executing = False
    try:
        if path.exists():
            run = json.loads(path.read_text(encoding="utf-8"))
            if run["configuration"] != config:
                raise ValueError("Run configuration changed; use a new run")
            if max_requests < max(run["authorized_request_limit"], run["request_count"]):
                raise ValueError("Authorized request limit cannot decrease")
            if run.get("stop_reason") in ("authentication", "provider_error"):
                return run
        else:
            run = {"dataset_hash": manifest["hash"], "configuration": config, "predictions": {},
                   "attempt_history": {}, "request_count": 0}
        run["authorized_request_limit"] = max_requests
        run["stop_reason"] = "running"
        executing = True
        save_json(path, run)
        for item in manifest["items"]:
            key = item["key"]
            history = run["attempt_history"].setdefault(key, [])
            previous = run["predictions"].get(key)
            transient = ("timeout", "rate_limit", "server_error")
            if previous and (previous.get("error") not in transient or len(history) >= attempts_limit):
                continue
            while len(history) < attempts_limit:
                if run["request_count"] >= max_requests:
                    run["stop_reason"] = "request_cap"
                    return run
                wait = max(0, run.get("next_request_at", 0) - time.time())
                if wait > max_wait:
                    run["stop_reason"] = "provider_pause"
                    return run
                if wait:
                    sleep(wait)
                run["request_count"] += 1
                event = {"state": "started", "requested_at": time.time()}
                history.append(event)
                prediction = {"rating": None, "tags": None, "rating_status": "transport_error",
                              "tags_status": "transport_error", "responded": False, "error": "interrupted",
                              "attempts": len(history)}
                run["predictions"][key] = prediction
                save_json(path, run)
                started = time.perf_counter()
                delay = interval
                try:
                    prediction = {**validate_prediction(generate(item["input"], prompt, config["model"])), "responded": True}
                    # Check before replacing the reserved uncertain attempt/history.
                    json.dumps(prediction, allow_nan=False)
                except ProviderFailure as exc:
                    status = "invalid_output" if exc.responded else "transport_error"
                    prediction = {"rating": None, "tags": None, "rating_status": status,
                                  "tags_status": status, "responded": exc.responded, "error": exc.category}
                    if exc.http_status is not None:
                        prediction["http_status"] = exc.http_status
                    backoff = min(30, 2 ** len(history)) + random.uniform(0, 1)
                    requested = exc.retry_after
                    if requested is not None and (not math.isfinite(requested) or requested < 0):
                        requested = 86400
                    delay = max(interval, backoff, requested or 0)
                    prediction["retry_not_before"] = time.time() + delay
                prediction.update(attempts=len(history), duration=time.perf_counter() - started)
                event.update(prediction, state="finished")
                run["predictions"][key] = prediction
                run["next_request_at"] = time.time() + delay
                save_json(path, run)
                error = prediction.get("error")
                if error in ("authentication", "provider_error"):
                    run["stop_reason"] = error
                    return run
                if error == "rate_limit" and (delay > max_wait or len(history) >= attempts_limit):
                    run["stop_reason"] = "provider_pause"
                    return run
                if error not in transient:
                    break
        run["stop_reason"] = "completed"
        return run
    except KeyboardInterrupt:
        if "run" in locals():
            run["stop_reason"] = "interrupted"
        raise
    except Exception as exc:
        if executing:
            _record_unexpected_error(run, exc)
            raise RuntimeError("Unexpected benchmark error; inspect the saved run status") from None
        raise
    finally:
        try:
            if "run" in locals() and run.get("configuration") == config:
                save_json(path, run)
        finally:
            lock.unlink()
