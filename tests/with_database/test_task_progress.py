import pytest
from flask import url_for


BRANCH_IN_DB = "sisyphus"
BRANCH_NOT_IN_DB = "fakebranch"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"branch": BRANCH_IN_DB, "status_code": 200},
        {"branch": BRANCH_IN_DB, "tasks_limit": 10, "status_code": 200},
        {"branch": BRANCH_IN_DB, "tasks_limit": -1, "status_code": 400},
        {"branch": BRANCH_NOT_IN_DB, "status_code": 400},
    ],
)
def test_last_tasks(client, kwargs):
    params = {k: v for k, v in kwargs.items() if k not in ("status_code",)}
    url = url_for("api.task/progress_route_last_tasks")
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        if params.get("tasks_limit", ""):
            assert data["length"] == params["tasks_limit"]
        assert data["length"] != 0
        assert data["tasks"] != []
