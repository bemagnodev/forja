import json
from datetime import datetime, timezone

from django.core.management import CommandError

from api.ai_lab.dataset import content_hash, freeze_manifest, record_review, require_reviewed, require_dataset_version
from api.ai_lab.runner import LocalDatasetCommand, command_version, guarded_root, save_json


class Command(LocalDatasetCommand):
    help = "Record explicit human input reviews, then freeze a private dataset."
    requires_system_checks = []

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument("--split", choices=("development", "final"), default="development")
        parser.add_argument("--approve", help="One problem key, after inspecting its input")
        parser.add_argument("--reviewer")
        parser.add_argument("--expected-hash")
        parser.add_argument("--freeze", action="store_true")

    def handle(self, *args, **options):
        version = command_version(options)
        root = guarded_root(options)
        path = root / "datasets" / version / options["split"] / "manifest.json"
        if not path.exists():
            raise CommandError("Prepare the dataset first")
        manifest = json.loads(path.read_text(encoding="utf-8"))
        try:
            require_dataset_version(manifest, version)
            if options["approve"]:
                if manifest["state"] == "frozen":
                    raise ValueError("Frozen dataset is immutable")
                item = next((i for i in manifest["items"] if i["key"] == options["approve"]), None)
                if not item or not options["reviewer"] or options["expected_hash"] != content_hash(item["input"]):
                    raise ValueError("review requires key, reviewer and current expected hash")
                record_review(item, options["reviewer"], datetime.now(timezone.utc).isoformat())
                save_json(path, manifest)
            failures = []
            for item in manifest["items"]:
                try:
                    require_reviewed(item)
                except ValueError:
                    failures.append(item["key"])
            save_json(path.parent / "validation.json", {"review_required": failures, "count": len(manifest["items"])})
            if options["freeze"]:
                freeze_manifest(manifest)
                save_json(path, manifest)
        except ValueError as exc:
            raise CommandError(str(exc)) from None
        self.stdout.write(f"Items: {len(manifest['items'])}; review required: {len(failures)}; state: {manifest['state']}")
