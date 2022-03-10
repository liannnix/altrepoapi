import os
import pytest

os.environ["ALTREPO_API_CONFIG"] = "./tests/api.conf"
from altrepo_api.app import app as test_api


@pytest.fixture
def app():
    app = test_api
    return app
