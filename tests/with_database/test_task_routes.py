import pytest
from flask import url_for

TASKID_IN_DB = 200000
TASKID_NOT_IN_DB = 100000
TASKID_CURL_PKG = 290333
TASKID_SYSLINUX_PKG = 284193


@pytest.mark.parametrize(
    "kwargs",
    [
        {"id": TASKID_IN_DB, "try": None, "iteration": None, "status_code": 200},
        {"id": TASKID_IN_DB, "try": 1, "iteration": 1, "status_code": 200},
        {"id": TASKID_IN_DB, "try": "1", "iteration": None, "status_code": 400},
        {"id": TASKID_IN_DB, "try": None, "iteration": "1", "status_code": 400},
        {"id": TASKID_NOT_IN_DB, "try": None, "iteration": None, "status_code": 404},
        {"id": TASKID_NOT_IN_DB, "try": 1, "iteration": 1, "status_code": 404},
    ],
)
def test_task_info(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("id", "status_code"):
            continue
        if v is not None:
            params[k] = v

    url = url_for("api.task_route_task_info", **{"id": kwargs["id"]})
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["branch"] != ""
        assert data["subtasks"] != []
        assert data["plan"] != {}
        assert data["prev"] != 0


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "branch": "sisyphus",
            "start_task": TASKID_IN_DB - 1,
            "end_task": TASKID_IN_DB,
            "start_date": None,
            "end_date": None,
            "status_code": 200,
        },
        {
            "branch": "sisyphus",
            "start_task": 0,
            "end_task": 0,
            "start_date": "2018-02-06",
            "end_date": "2018-02-07",
            "status_code": 200,
        },
        {
            "branch": "sisyphus",
            "start_task": 0,
            "end_task": TASKID_IN_DB,
            "start_date": "2018-02-06",
            "end_date": None,
            "status_code": 200,
        },
        {
            "branch": "xxx",
            "start_task": 0,
            "end_task": 0,
            "start_date": None,
            "end_date": None,
            "status_code": 400,
        },
        {
            "branch": "sisyphus",
            "start_task": 0,
            "end_task": 0,
            "start_date": None,
            "end_date": None,
            "status_code": 400,
        },
        {
            "branch": "sisyphus",
            "start_task": TASKID_NOT_IN_DB - 1,
            "end_task": TASKID_NOT_IN_DB,
            "start_date": None,
            "end_date": None,
            "status_code": 400,
        },
    ],
)
def test_task_history(client, kwargs):
    # build URL arguments
    params = {}
    for k, v in kwargs.items():
        if k == "status_code":
            continue
        if v is not None:
            params[k] = v

    url = url_for("api.task_route_task_history")
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["length"] != 0
        assert data["tasks"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"id": TASKID_IN_DB, "status_code": 200},
        {"id": TASKID_NOT_IN_DB, "status_code": 404},
    ],
)
def test_task_diff(client, kwargs):
    url = url_for("api.task_route_task_diff", **{"id": kwargs["id"]})
    response = client.get(url)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["task_have_plan"] is True
        assert data["task_diff"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"id": TASKID_IN_DB, "status_code": 200},
        {"id": TASKID_NOT_IN_DB, "status_code": 404},
    ],
)
def test_find_packageset(client, kwargs):
    url = url_for("api.task_route_task_find_packageset", **{"id": kwargs["id"]})
    response = client.get(url)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["length"] != 0
        assert data["task_packages"] != []
        assert data["packages"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"id": TASKID_IN_DB, "include_task_packages": None, "status_code": 200},
        {"id": TASKID_IN_DB, "include_task_packages": "true", "status_code": 200},
        {"id": TASKID_NOT_IN_DB, "include_task_packages": None, "status_code": 404},
    ],
)
def test_task_repo(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("id", "status_code"):
            continue
        if v is not None:
            params[k] = v

    url = url_for("api.task_route_task_repo", **{"id": kwargs["id"]})
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["base_repository"] != {}
        assert data["task_diff_list"] != []
        assert data["archs"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"id": TASKID_CURL_PKG, "depth": None, "status_code": 200},
        {"id": TASKID_CURL_PKG, "depth": 2, "status_code": 200},
        {"id": TASKID_NOT_IN_DB, "depth": None, "status_code": 404},
    ],
)
def test_task_wds(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("id", "status_code"):
            continue
        if v is not None:
            params[k] = v

    url = url_for("api.task_route_task_build_dependency", **{"id": kwargs["id"]})
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["length"] >= 300
        if data["request_args"]["depth"] == 2:
            assert data["length"] >= 2500
        assert data["dependencies"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"id": TASKID_CURL_PKG, "status_code": 200},
        {"id": TASKID_NOT_IN_DB, "status_code": 404},
    ],
)
def test_build_dependency_set(client, kwargs):
    url = url_for("api.task_route_task_build_dependency_set", **{"id": kwargs["id"]})
    response = client.get(url)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["length"] != 0
        assert data["request_args"]["branch"] == "sisyphus"
        assert data["packages"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"id": TASKID_SYSLINUX_PKG, "archs": "x86_64", "status_code": 200},
        {"id": TASKID_CURL_PKG, "archs": None, "status_code": 200},
        {"id": TASKID_NOT_IN_DB, "archs": None, "status_code": 404},
    ],
)
def test_task_misconflict(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("id", "status_code"):
            continue
        if v is not None:
            params[k] = v

    url = url_for("api.task_route_task_misconflict_packages", **{"id": kwargs["id"]})
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        if data["id"] == TASKID_SYSLINUX_PKG:
            assert data["length"] != 0
            assert data["conflicts"] != []
        else:
            assert data["length"] == 0
            assert data["conflicts"] == {
                "input_package": None,
                "conflict_package": None,
                "version": None,
                "release": None,
                "epoch": None,
                "archs": None,
                "files_with_conflict": None,
            }
        assert data["request_args"]["packages"] != 0
