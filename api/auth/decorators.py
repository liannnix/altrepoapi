from functools import wraps
from flask import request

from .exceptions import ApiUnauthorized, ApiForbidden
from .auth import check_auth


def auth_required(f):
    """Execute function if request contains valid access token."""

    @wraps(f)
    def decorated(*args, **kwargs):
        token_payload = _check_access_auth(admin_only=False)
        # for name, val in token_payload.items():
        #     setattr(decorated, name, val)
        return f(*args, **kwargs)

    return decorated


def admin_auth_required(f):
    """Execute function if request contains valid access token AND user is admin."""

    @wraps(f)
    def decorated(*args, **kwargs):
        token_payload = _check_access_auth(admin_only=True)
        if not token_payload["admin"]:
            raise ApiForbidden()
        for name, val in token_payload.items():
            setattr(decorated, name, val)
        return f(*args, **kwargs)

    return decorated


def _check_access_auth(admin_only=False):
    token = request.headers.get("Authorization")
    if not token:
        raise ApiUnauthorized(description="Unauthorized", admin_only=admin_only)
    result = check_auth(token)
    if not result.verified:
        raise ApiUnauthorized(
            description=result.error,
            admin_only=admin_only,
            error="invalid_token",
            error_description=result.error,
        )
    return result.value
