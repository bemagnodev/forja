"""Merge problem updates against the latest locked row, after external I/O."""
from django.db import transaction

from api.models import Problem


@transaction.atomic
def upsert_problem_metadata(*, platform, platform_id, metadata, fields=None):
    fields = fields or {}
    problem, created = Problem.objects.select_for_update().get_or_create(
        platform=platform, platform_id=platform_id,
        defaults={**fields, "platform_metadata": metadata},
    )
    if not created:
        # Submission payloads may omit official difficulty/tags already known.
        updates = {key: value for key, value in metadata.items()
                   if not (key == "rating" and value is None or key == "tags" and not value)}
        problem.platform_metadata = {**(problem.platform_metadata or {}), **updates}
        for name, value in fields.items():
            setattr(problem, name, value)
        problem.save(update_fields=["platform_metadata", *fields])
    return problem, created
