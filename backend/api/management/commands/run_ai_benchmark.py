import json
import os
import re
from pathlib import Path

from django.core.management import CommandError

from api.ai_lab.runner import LocalDatasetCommand, command_version, guarded_root, run_local, save_json
from api.ai_lab.metrics import compare_runs
from api.ai_lab.classification import BASELINE_MODEL, baseline_predictions, get_generator
from api.ai_lab.catalog import get_model
from api.ai_lab.dataset import require_dataset_version


class Command(LocalDatasetCommand):
    help = "Run a reviewed local pilot; defaults to the local baseline without AI."
    requires_system_checks = []

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument("--split", choices=("development", "final"), default="development")
        parser.add_argument("--run-id", default="gemini-pilot-v1")
        parser.add_argument("--model")
        parser.add_argument("--classifier", choices=("gemini", "groq", "baseline"), default="baseline")
        parser.add_argument("--allow-model", help="Exact model ID explicitly authorized by the user")
        parser.add_argument("--max-requests", type=int, help="Authorized cap including retries, preserved across resume")
        parser.add_argument("--retry-failures", action="store_true", help="Recover only transient failures, at most once per item")
        parser.add_argument("--export-showcase", help="Export an existing saved comparison without inference")
        parser.add_argument("--snapshot-output", help="Review destination; defaults to the private exports directory")
        parser.add_argument("--include-justifications", action="store_true", help="Include saved justification text for explicit publication review")

    def handle(self, *args, **options):
        version = command_version(options)
        root = guarded_root(options)
        if options["export_showcase"]:
            if options["model"] or options["allow_model"] or options["max_requests"] or options["retry_failures"] or options["classifier"] != "baseline":
                raise CommandError("Snapshot export cannot be combined with inference options")
            if not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", options["export_showcase"]):
                raise CommandError("Invalid export identifier")
            from api.ai_lab.results import export_snapshot
            output = Path(options["snapshot_output"]) if options["snapshot_output"] else root / "exports" / f"{options['export_showcase']}.json"
            try:
                export_snapshot(root, options["export_showcase"], output,
                                include_justifications=options["include_justifications"])
            except (OSError, ValueError, LookupError) as exc:
                raise CommandError(f"Snapshot export stopped: {type(exc).__name__}") from None
            self.stdout.write("Snapshot exported for review; no model called or publication performed")
            return
        if options["snapshot_output"] or options["include_justifications"]:
            raise CommandError("Snapshot options require --export-showcase")
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", options["run_id"]):
            raise CommandError("Invalid run ID")
        path = root / "datasets" / version / options["split"] / "manifest.json"
        if not path.exists():
            raise CommandError("Prepare and review dataset first")
        manifest = json.loads(path.read_text(encoding="utf-8"))
        try:
            require_dataset_version(manifest, version)
            output = root / "runs" / options["run_id"] / "run.json"
            development_path = root / "datasets" / version / "development/manifest.json"
            development = json.loads(development_path.read_text(encoding="utf-8"))
            require_dataset_version(development, version)
            if options["classifier"] == "baseline":
                if options["retry_failures"]:
                    raise ValueError("Baseline has no recoverable provider failures")
                run = {"dataset_hash": manifest.get("hash"),
                       "configuration": {"provider": "baseline", "model": BASELINE_MODEL, "development_hash": development.get("hash")},
                       "predictions": baseline_predictions(manifest, development)}
                if output.exists() and json.loads(output.read_text(encoding="utf-8")) != run:
                    raise ValueError("Run configuration changed; choose a new ID")
                save_json(output, run)
            else:
                if os.environ.get("AI_LAB_FREE_TIER_CONFIRMED") != "true":
                    raise CommandError("Confirm the API project uses the free-tier: AI_LAB_FREE_TIER_CONFIRMED=true")
                if (not options["model"] or options["allow_model"] != options["model"]
                        or not options["max_requests"] or options["max_requests"] < 1):
                    raise CommandError("Explicit authorization of exact model and positive --max-requests required")
                provider, model = options["classifier"], options["model"]
                entry = get_model(provider, model)
                if not os.environ.get(entry["key_env"]):
                    raise CommandError(f"Configure {entry['key_env']} privately; never paste it in chat")
                configuration = {"provider": provider, "model": model, "max_attempts": 1}
                if provider == "groq":
                    from api.ai_lab.providers.groq import generation_parameters
                    configuration.update(generation=generation_parameters(model), max_attempts=1)
                run = run_local(manifest, configuration, output, get_generator(provider, model),
                                max_requests=options["max_requests"], retry_failures=options["retry_failures"])
        except (ValueError, FileExistsError) as exc:
            raise CommandError(str(exc)) from None
        references = {item["key"]: item["reference"] for item in manifest["items"]}
        comparison = {options["run_id"]: run["predictions"]}
        if options["classifier"] != "baseline":
            comparison["baseline"] = baseline_predictions(manifest, development)
        report = compare_runs(references, comparison)
        save_json(root / "runs" / options["run_id"] / "metrics.json", report)
        self.stdout.write(json.dumps(report["runs"], indent=2))
