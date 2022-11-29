import pytest
from flask import url_for


BRANCH_IN_DB = "sisyphus"
BRANCH_NOT_IN_DB = "fakebranch"
TASK_IN_DB = "310692"
TASK_NOT_IN_DB = "9999999"
OWNER_IN_DB = "rider"
OWNER_NOT_IN_DB = "fakeowner"
COMPONENT_IN_DB = "curl"
COMPONENT_NOT_IN_DB = "fakecomponent"
STATE_IN_DB = "DONE"
STATE_NOT_IN_DB = "running"


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


def test_all_packagesets(client):
    url = url_for("api.task/progress_route_all_package_sets")
    response = client.get(url)
    data = response.json
    assert response.status_code == 200
    assert data["length"] != 0
    assert data["branches"] != []
    assert "sisyphus" in data["branches"]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"input": TASK_IN_DB, "branch": BRANCH_IN_DB, "status_code": 200},
        {"input": TASK_IN_DB, "status_code": 200},
        {"input": TASK_IN_DB, "branch": "p10", "status_code": 404},
        {"input": TASK_IN_DB, "branch": BRANCH_NOT_IN_DB, "status_code": 400},
        {"input": TASK_NOT_IN_DB, "status_code": 404},
        {"input": OWNER_IN_DB, "branch": BRANCH_IN_DB, "status_code": 200},
        {"input": OWNER_IN_DB, "tasks_limit": 10, "status_code": 200},
        {"input": OWNER_IN_DB, "branch": BRANCH_NOT_IN_DB, "status_code": 400},
        {"input": OWNER_NOT_IN_DB, "status_code": 404},
        {"input": COMPONENT_IN_DB, "branch": BRANCH_IN_DB, "status_code": 200},
        {"input": COMPONENT_IN_DB, "tasks_limit": 10, "status_code": 200},
        {"input": COMPONENT_NOT_IN_DB, "tasks_limit": 10, "status_code": 404},
        {"input": COMPONENT_IN_DB, "branch": BRANCH_NOT_IN_DB, "status_code": 400},
        {"input": COMPONENT_IN_DB, "tasks_limit": -1, "status_code": 400},
        {"input": None, "status_code": 400},
    ],
)
def test_fast_tasks_search_lookup(client, kwargs):
    params = {k: v for k, v in kwargs.items() if k not in ("status_code",)}
    url = url_for("api.task/progress_route_fast_tasks_search_lookup")
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        if params.get("tasks_limit", ""):
            assert data["length"] == params["tasks_limit"]
        assert data["length"] != 0
        assert data["tasks"] != []
        for task in data["tasks"]:
            if params["input"] == OWNER_IN_DB:
                assert task["task_owner"] == OWNER_IN_DB
            if params["input"].isdigit():
                assert params["input"] in str(task["task_id"])


@pytest.mark.parametrize(
    "kwargs",
    [
        {"input": TASK_IN_DB, "branch": BRANCH_IN_DB, "status_code": 200},
        {"input": TASK_IN_DB, "status_code": 200},
        {"input": TASK_IN_DB, "state": STATE_IN_DB, "status_code": 200},
        {"input": TASK_IN_DB, "owner": OWNER_IN_DB, "status_code": 200},
        {"input": TASK_IN_DB, "state": STATE_NOT_IN_DB, "status_code": 400},
        {"input": TASK_IN_DB, "owner": OWNER_NOT_IN_DB, "status_code": 404},
        {"input": TASK_IN_DB, "branch": "p10", "status_code": 404},
        {"input": TASK_IN_DB, "branch": BRANCH_NOT_IN_DB, "status_code": 400},
        {"input": TASK_NOT_IN_DB, "status_code": 404},
        {"input": OWNER_IN_DB, "branch": BRANCH_IN_DB, "status_code": 200},
        {"input": OWNER_IN_DB, "status_code": 200},
        {"input": OWNER_IN_DB, "branch": BRANCH_NOT_IN_DB, "status_code": 400},
        {"input": OWNER_NOT_IN_DB, "status_code": 404},
        {"input": COMPONENT_IN_DB, "branch": BRANCH_IN_DB, "status_code": 200},
        {"input": COMPONENT_IN_DB, "branch": BRANCH_IN_DB, "owner": OWNER_IN_DB, "status_code": 200},
        {"input": COMPONENT_IN_DB, "status_code": 200},
        {"input": COMPONENT_NOT_IN_DB, "status_code": 404},
        {"input": COMPONENT_IN_DB, "branch": BRANCH_NOT_IN_DB, "status_code": 400},
        {"input": None, "status_code": 400},
    ],
)
def test_find_tasks(client, kwargs):
    params = {k: v for k, v in kwargs.items() if k not in ("status_code",)}
    url = url_for("api.task/progress_route_find_tasks")
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["length"] != 0
        assert data["tasks"] != []
        for task in data["tasks"]:
            if params.get("state", ""):
                assert task["task_state"] == params.get("state")
            if params["input"] == OWNER_IN_DB or params.get("owner"):
                assert task["task_owner"] == OWNER_IN_DB
            if params["input"].isdigit():
                assert params["input"] in str(task["task_id"])
