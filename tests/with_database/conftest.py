import os
import pytest

from altrepo_api.api.auth import decorators
from altrepo_api.api.auth.exceptions import ApiUnauthorized

os.environ["ALTREPO_API_CONFIG"] = "./tests/api.conf"
from altrepo_api.app import app as test_api


@pytest.fixture
def app():
    app = test_api
    return app


@pytest.fixture(scope="function")
def mocked_check_access_token(monkeypatch):

    def _check_access_token(role: str, validate_role: bool):
        VALID_TOKEN = "valid_token"
        if not fetch_result.headers:
            raise ApiUnauthorized(description="Authentication token is required")
        token = fetch_result.headers.get("Authorization")
        if not token:
            raise ApiUnauthorized(description="Authentication token is required")
        if token != VALID_TOKEN:
            raise ApiUnauthorized(description="Invalid token.")

        return {"name": "testuser", "roles": [role], "token": token}

    monkeypatch.setattr(decorators, "_check_access_token", _check_access_token)

    class FetchResult:
        pass

    fetch_result = FetchResult()
    fetch_result.headers = {}
    return fetch_result
