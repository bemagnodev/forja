"""Safe classification error payloads shared by product and Explore."""
from ninja.errors import HttpError


class ClassificationFailure(HttpError):
    def __init__(self, status, message, *, stage, code, model, platform, upstream_status=None):
        super().__init__(status, message)
        self.diagnostic = {'stage': stage, 'code': code, 'model': model,
                           'platform': platform, 'upstream_status': upstream_status}
