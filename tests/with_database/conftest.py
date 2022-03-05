import os
import pytest

os.environ["ALTREPO_API_CONFIG"] = "./tests/api.conf"
from altrepo_api.app import app

@pytest.fixture
def client():
    """Test Flask App client."""
    
    with app.test_client() as client:
        yield client
