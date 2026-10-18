import json

import requests
from django.core.management import CommandError

from api.ai_lab.dataset import build_manifest, content_hash, require_dataset_version, require_frozen
from api.ai_lab.runner import LocalDatasetCommand, command_version, guarded_root, save_json
from api.ai_lab.review import render_review
from api.services.codeforces_client import CodeforcesClient


def fetch_catalog():
    # Public request: never attach the optional personal CF API credentials.
    catalog = CodeforcesClient(api_key="", api_secret="").get_problems()
    if not catalog.get("problems"):
        raise ValueError("Codeforces catalog unavailable")
    return catalog


def fetch_html(url):
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.text


class Command(LocalDatasetCommand):
    help = "Prepare private, unreviewed AI Lab input; never calls an AI model."
    requires_system_checks = []

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument("--split", choices=("development", "final"), default="development")
        parser.add_argument("--seed", type=int, default=42)

    def handle(self, *args, **options):
        version = command_version(options)
        root = guarded_root(options)
        split = options["split"]
        folder = root / "datasets" / version / split
        if folder.exists():
            raise CommandError("Dataset already exists; preserve it and use a separate version directory")
        development = None
        if split == "final":
            path = root / "datasets" / version / "development/manifest.json"
            if not path.exists():
                raise CommandError("Frozen development dataset required")
            development = json.loads(path.read_text(encoding="utf-8"))
            try:
                require_dataset_version(development, version)
                require_frozen(development)
            except ValueError as exc:
                raise CommandError(str(exc)) from None
        try:
            catalog = fetch_catalog()
            save_json(root / "catalogs" / (content_hash(catalog) + ".json"), catalog)
            def collect(url):
                self.stdout.write(f"Collecting {url}")
                text = fetch_html(url)
                target = folder / "raw" / (content_hash(url) + ".html")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, encoding="utf-8")
                return text
            manifest = build_manifest(catalog, collect, split, options["seed"], development, version=version)
        except (ValueError, requests.RequestException) as exc:
            raise CommandError(f"Collection stopped: {type(exc).__name__}; no model called") from None
        save_json(folder / "manifest.json", manifest)
        sources = {item["key"]: (folder / "raw" / (content_hash(item["source_url"]) + ".html")).read_text(encoding="utf-8")
                   for item in manifest["items"]}
        page = render_review(manifest, sources)
        (folder / "review.html").write_text(page, encoding="utf-8")
        self.stdout.write(f"Prepared {len(manifest['items'])} items. Review: {folder / 'review.html'}; no model called.")
