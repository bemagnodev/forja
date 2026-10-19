"""Validation shared by adapters; no coercion or synonym mapping."""

# Snapshot of Codeforces problemset tag vocabulary, version 2026-10-17.
# Source: https://codeforces.com/problemset (tag filter).
TAXONOMY_SOURCE = "https://codeforces.com/problemset"
TAXONOMY_VERSION = "cf-tags-2026-10-17"


class ProviderFailure(Exception):
    def __init__(self, category: str, retry_after=None, responded=False, http_status=None):
        super().__init__(category)
        self.category = category
        self.retry_after = retry_after
        self.responded = responded
        self.http_status = http_status if type(http_status) is int and 100 <= http_status <= 599 else None


TAGS = frozenset((
    "2-sat", "binary search", "bitmasks", "brute force", "chinese remainder theorem",
    "combinatorics", "constructive algorithms", "data structures", "dfs and similar",
    "divide and conquer", "dp", "dsu", "expression parsing", "fft", "flows", "games",
    "geometry", "graph matchings", "graphs", "greedy", "hashing", "implementation",
    "interactive", "math", "matrices", "meet-in-the-middle", "number theory",
    "probabilities", "schedules", "shortest paths", "sortings", "string suffix structures",
    "strings", "ternary search", "trees", "two pointers", "*special", "communication",
))


def normalize_tags(value) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError("Tags must be a nonempty array")
    normalized = set()
    for tag in value:
        if not isinstance(tag, str):
            raise ValueError("Tag must be a string")
        canonical = " ".join(tag.lower().split())
        if canonical not in TAGS:
            raise ValueError(f"Unknown Codeforces tag: {tag!r}")
        normalized.add(canonical)
    return sorted(normalized)


def validate_prediction(raw) -> dict:
    data = raw if isinstance(raw, dict) else {}
    rating = data.get("rating")
    status = "valid"
    if type(rating) is not int:
        status = "invalid_output"
    elif not 800 <= rating <= 2400:
        status = "out_of_domain"
    elif rating % 100:
        status = "invalid_output"
    try:
        tags, tags_status = normalize_tags(data.get("tags")), "valid"
    except ValueError:
        tags, tags_status = None, "invalid_output"
    return {"raw": raw, "rating": rating if status == "valid" else None,
            "rating_status": status, "tags": tags, "tags_status": tags_status,
            "justification": data.get("justification") if isinstance(data.get("justification"), str) else ""}
