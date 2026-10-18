"""Local-only experiment execution and environment checks."""

from pathlib import Path
import json
import time
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


def run_local(manifest: dict, configuration: dict, path: Path, generate, *, sleep=time.sleep, max_requests=None, retry_failures=False) -> dict:
    require_frozen(manifest)
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
                    break
                except ProviderFailure as exc:
                    delay = exc.retry_after if exc.retry_after is not None else 2 ** (attempts - 1)
                    status = "invalid_output" if exc.responded else "transport_error"
                    prediction = {"rating": None, "tags": None, "rating_status": status, "tags_status": status,
                                  "responded": exc.responded, "error": exc.category,
                                  "retry_not_before": time.time() + max(0, delay)}
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
    finally:
        lock.unlink()
