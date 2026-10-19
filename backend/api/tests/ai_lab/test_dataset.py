import pytest


def test_statement_preserves_math_and_all_samples(statement_html):
    from api.ai_lab.dataset import parse_statement

    result = parse_statement(statement_html)

    assert r"\sum_{i=1}^{n}" in result["description"]
    assert r"\frac{x}{y}" in result["description"]
    assert r"\unknown{x}" in result["description"]
    assert r"10^5" in result["input_format"]
    assert result["testcases"] == [{"input": "2\n1 2", "output": "3"}, {"input": "1\n5", "output": "5"}]
    assert result["time_limit"] == "2 seconds"
    assert result["notes"] == ""


@pytest.mark.parametrize("html", [
    "<html>Checking your browser CAPTCHA</html>",
    '<div class="problem-statement"></div>',
])
def test_statement_rejects_blocked_or_incomplete_html(html):
    from api.ai_lab.dataset import parse_statement

    with pytest.raises(ValueError, match="statement"):
        parse_statement(html)


def test_statement_preserves_images_for_explicit_visual_handling(statement_html):
    from api.ai_lab.dataset import parse_statement

    result = parse_statement(statement_html.replace("Compute", '<img src="diagram.png">Compute'))
    assert result["images"][0]["url"].endswith("/diagram.png")
    assert "[image:1]" in result["description"]


def test_statement_rejects_unpaired_samples(statement_html):
    from api.ai_lab.dataset import parse_statement

    with pytest.raises(ValueError, match="sample"):
        parse_statement(statement_html.replace('<div class="output"><pre>5</pre></div>', ""))


def test_selection_is_reproducible_and_contests_are_disjoint(catalog):
    from api.ai_lab.dataset import select_items

    development = select_items(catalog, per_band=3, seed=42)
    reverse = {"problems": list(reversed(catalog["problems"]))}
    assert development == select_items(reverse, per_band=3, seed=42)
    assert len(development) == 12
    final = select_items(catalog, per_band=15, seed=42, exclude_contests={p["contestId"] for p in development})
    assert len(final) == 60
    assert not {p["contestId"] for p in development} & {p["contestId"] for p in final}
    assert [sum(lo <= p["rating"] <= hi for p in final) for lo, hi in ((800, 1100), (1200, 1500), (1600, 1900), (2000, 2400))] == [15] * 4


def test_selection_filters_duplicates_bad_types_and_ratings(catalog):
    from api.ai_lab.dataset import select_items

    catalog["problems"] += [catalog["problems"][0].copy(),
        {"contestId": 999, "index": "A", "rating": 2500, "tags": ["math"]},
        {"contestId": 998, "index": "A", "rating": 800, "tags": ["interactive"]}]
    selected = select_items(catalog, per_band=3)
    assert len({(p["contestId"], p["index"]) for p in selected}) == 12
    assert all(p["contestId"] not in (998, 999) for p in selected)


def test_selection_fails_on_deficit_instead_of_relaxing(catalog):
    from api.ai_lab.dataset import select_items

    with pytest.raises(ValueError, match="insufficient"):
        select_items(catalog, per_band=25)


def test_selection_caps_items_per_contest(catalog):
    from api.ai_lab.dataset import select_items

    for p in catalog["problems"]:
        p["index"] = "A" + str(p["contestId"])
        p["contestId"] = 1
    with pytest.raises(ValueError, match="insufficient"):
        select_items(catalog, per_band=3)


def test_review_hash_prevents_changed_input_and_leaked_references(statement_html):
    from api.ai_lab.dataset import prepare_input, content_hash, require_reviewed, parse_statement

    prepared = prepare_input({**parse_statement(statement_html),
                              "rating": 900, "tags": ["math"], "url": "https://example.org"})
    assert "rating" not in prepared and "tags" not in prepared and "url" not in prepared
    item = {"input": prepared, "review": {"reviewer": "mentor", "reviewed_at": "2026-10-17", "hash": content_hash(prepared)}}
    require_reviewed(item)
    item["input"]["description"] += "changed"
    with pytest.raises(ValueError, match="review"):
        require_reviewed(item)


def test_manifest_requires_review_then_freezes_and_detects_reference_change(catalog, statement_html):
    from api.ai_lab.dataset import build_manifest, record_review, freeze_manifest, require_frozen

    manifest = build_manifest(catalog, lambda url: statement_html, split="development", seed=42)
    assert len(manifest["items"]) == 12
    assert manifest["state"] == "collected"
    with pytest.raises(ValueError, match="review"):
        freeze_manifest(manifest)
    for item in manifest["items"]:
        record_review(item, "mentor", "2026-10-17T12:00:00-03:00")
    freeze_manifest(manifest)
    require_frozen(manifest)
    manifest["items"][0]["reference"]["rating"] = 2400
    with pytest.raises(ValueError, match="hash"):
        require_frozen(manifest)


def test_final_collection_requires_frozen_development(catalog, statement_html):
    from api.ai_lab.dataset import build_manifest

    with pytest.raises(ValueError, match="development"):
        build_manifest(catalog, lambda url: statement_html, split="final")


def test_collection_replaces_bad_statement_and_records_reason(catalog, statement_html):
    from api.ai_lab.dataset import build_manifest, select_items

    first = select_items(catalog, per_band=3)[0]
    bad_url = f'https://codeforces.com/contest/{first["contestId"]}/problem/{first["index"]}'
    manifest = build_manifest(catalog, lambda url: "blocked" if url == bad_url else statement_html)
    assert len(manifest["items"]) == 12
    assert manifest["excluded"][0]["url"] == bad_url
    assert not any(item["source_url"] == bad_url for item in manifest["items"])


@pytest.mark.parametrize("database", [{"ENGINE": "django.db.backends.postgresql", "NAME": "remote"}, {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}, {"ENGINE": "django.db.backends.sqlite3", "NAME": "relative.sqlite3"}])
def test_real_execution_guard_rejects_unsafe_database(database, tmp_path):
    from api.ai_lab.runner import require_local_environment

    with pytest.raises(ValueError, match="local"):
        require_local_environment("core.settings_ai_lab_local", database, tmp_path)


def test_real_execution_guard_requires_explicit_non_test_settings(tmp_path):
    from api.ai_lab.runner import require_local_environment

    database = {"ENGINE": "django.db.backends.sqlite3", "NAME": str(tmp_path / "pilot.sqlite3")}
    require_local_environment("core.settings_ai_lab_local", database, tmp_path)
    with pytest.raises(ValueError, match="settings"):
        require_local_environment("core.settings_test", database, tmp_path)


def test_no_review_and_unknown_fields_cannot_reach_model(statement_html):
    from api.ai_lab.dataset import parse_statement, require_reviewed

    item = {"input": parse_statement(statement_html), "review": {}}
    with pytest.raises(ValueError, match="review"):
        require_reviewed(item)


def test_preparation_rejects_nested_metadata_disguised_as_notes(statement_html):
    from api.ai_lab.dataset import parse_statement, prepare_input

    value = parse_statement(statement_html)
    value["notes"] = {"rating": 1200, "tags": ["math"]}
    with pytest.raises(ValueError, match="notes"):
        prepare_input(value)


def test_freeze_rejects_empty_or_incomplete_sets(catalog, statement_html):
    from api.ai_lab.dataset import build_manifest, record_review, freeze_manifest

    manifest = build_manifest(catalog, lambda url: statement_html)
    for item in manifest["items"]:
        record_review(item, "mentor", "2026-10-17")
    manifest["items"] = manifest["items"][:-1]
    with pytest.raises(ValueError, match="count"):
        freeze_manifest(manifest)


def test_unknown_split_or_unsafe_index_is_rejected(catalog):
    from api.ai_lab.dataset import select_items

    for item in catalog["problems"]:
        item["index"] = "../../bad"
    with pytest.raises(ValueError, match="insufficient"):
        select_items(catalog, 3)


def test_review_report_contains_only_readable_statement_and_prepared_input(reviewed_manifest, statement_html):
    from api.ai_lab.review import render_review

    manifest = reviewed_manifest()
    source = ('<html><head><script>Google Analytics secret</script><style>evilstylesheet</style>'
              '<meta name="csrf-token" content="csrf-secret"></head><body><nav>navigation-only' + 'x' * 100000 + '</nav>'
              + statement_html.replace('Compute', '<script>CSRF inline secret</script><style>internal-evil</style>Compute') + '</body></html>')
    page = render_review(manifest, {item["key"]: source for item in manifest["items"]})
    assert len(page.encode("utf-8")) < 60000
    for forbidden in ("<script", "CSRF", "csrf-secret", "Google Analytics", "evilstylesheet", "internal-evil", "navigation-only", "<nav"):
        assert forbidden not in page
    for text in (r"\sum_{i=1}^{n}", r"\frac{x}{y}", r"\unknown{x}", "10^5", "2 seconds", "256 megabytes", "1 2", "Print the sum."):
        assert text in page
    assert manifest["items"][0]["input_hash"] in page
    assert '"description"' in page or '&quot;description&quot;' in page
    assert "rating, tags, título e contest" in page


def test_review_report_escapes_external_content_and_unsafe_links(reviewed_manifest, statement_html):
    from api.ai_lab.review import render_review

    manifest = reviewed_manifest()
    manifest["items"][0]["key"] = '</pre><script>alert(1)</script>'
    manifest["items"][0]["source_url"] = "javascript:alert(1)"
    source = statement_html.replace("Compute", '&lt;/pre&gt;&lt;img src=x onerror=alert(1)&gt;Compute')
    page = render_review(manifest, {item["key"]: source for item in manifest["items"]})
    assert "<script" not in page and "<img" not in page and 'href="javascript:' not in page
    assert '&lt;/pre&gt;&lt;img' in page


def test_review_report_without_statement_fails_closed(reviewed_manifest):
    from api.ai_lab.review import render_review

    manifest = reviewed_manifest()
    with pytest.raises(ValueError, match="statement"):
        render_review(manifest, {item["key"]: '<html>navigation</html>' for item in manifest["items"]})
def test_excluding_unusable_problem_preserves_draw_order(catalog):
    from api.ai_lab.dataset import select_items
    original = select_items(catalog, 3, 42)
    excluded = (original[0]["contestId"], original[0]["index"])
    replacement = select_items(catalog, 3, 42, exclude_problems={excluded})
    expected = {(p["contestId"], p["index"]) for p in original[1:]}
    assert expected.issubset({(p["contestId"], p["index"]) for p in replacement})
