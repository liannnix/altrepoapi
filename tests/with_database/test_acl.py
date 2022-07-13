import pytest
from flask import url_for

BRANCH_IN_DB = "sisyphus"
BRANCH_NOT_IN_DB = "fakebranch"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"branch": BRANCH_IN_DB, "name": None, "status_code": 200},
        {"branch": BRANCH_IN_DB, "name": "core", "status_code": 200},
        {"branch": BRANCH_IN_DB, "name": "@python", "status_code": 200},
        {"branch": BRANCH_NOT_IN_DB, "name": None, "status_code": 400},
        {"branch": BRANCH_IN_DB, "name": "abc+", "status_code": 400},
        {"branch": BRANCH_IN_DB, "name": "fake_group", "status_code": 404},
    ],
)
def test_acl_groups(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("status_code",):
            continue
        if v is not None:
            params[k] = v
    url = url_for("api.acl_route_acl_groups")
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["length"] > 0
        assert data["groups"] != []
        assert data["request_args"]["branch"] == kwargs["branch"]
