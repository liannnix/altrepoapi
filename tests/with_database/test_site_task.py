import pytest
from flask import url_for

BRANCH_IN_DB = "sisyphus"
BRANCH_NOT_IN_DB = "fakebranch"
PACKAGE_IN_DB = "curl"
PACKAGE_NOT_IN_DB = "fakepackage"
MAINTAINER_IN_DB = "rider"
MAINTAINER_NOT_IN_DB = "fakemaintainer"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"name": PACKAGE_IN_DB, "status_code": 200},
        {"name": "", "status_code": 400},
        {"name": PACKAGE_NOT_IN_DB, "status_code": 404},
    ],
)
def test_tasks_by_package(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("status_code",):
            continue
        if v is not None:
            params[k] = v
    url = url_for("api.site_route_tasks_by_package")
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
        {"branch": BRANCH_IN_DB, "maintainer_nickname": MAINTAINER_IN_DB, "status_code": 200},
        {"branch": BRANCH_NOT_IN_DB, "maintainer_nickname": MAINTAINER_IN_DB, "status_code": 400},
        {"branch": BRANCH_IN_DB, "maintainer_nickname": "", "status_code": 400},
        {"branch": BRANCH_IN_DB, "maintainer_nickname": MAINTAINER_NOT_IN_DB, "status_code": 404},
    ],
)
def test_tasks_by_maintainer(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("status_code",):
            continue
        if v is not None:
            params[k] = v
    url = url_for("api.site_route_tasks_by_maintainer")
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
        {"name": PACKAGE_IN_DB, "branch": None, "status_code": 200},
        {"name": PACKAGE_IN_DB, "branch": BRANCH_IN_DB, "status_code": 200},
        {"name": PACKAGE_IN_DB, "branch": BRANCH_NOT_IN_DB, "status_code": 400},
        {"name": PACKAGE_NOT_IN_DB, "branch": None, "status_code": 404},
    ],
)
def test_package_versions_from_tasks(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("status_code",):
            continue
        if v is not None:
            params[k] = v
    url = url_for("api.site_route_package_versions_from_tasks")
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["length"] != 0
        assert data["versions"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"branch": BRANCH_IN_DB, "tasks_limit": 10, "task_owner": None, "status_code": 200},
        {"branch": BRANCH_IN_DB, "tasks_limit": 10, "task_owner": MAINTAINER_IN_DB, "status_code": 200},
        {"branch": BRANCH_NOT_IN_DB, "tasks_limit": 10, "task_owner": None, "status_code": 400},
        {"branch": BRANCH_IN_DB, "tasks_limit": 0, "task_owner": None, "status_code": 400},
        {"branch": BRANCH_IN_DB, "tasks_limit": -10, "task_owner": None, "status_code": 400},
        {"branch": BRANCH_IN_DB, "tasks_limit": 10, "task_owner": MAINTAINER_NOT_IN_DB, "status_code": 404},
    ],
)
def test_last_packages_by_tasks(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("status_code",):
            continue
        if v is not None:
            params[k] = v
    url = url_for("api.site_route_last_task_packages")
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["length"] != 0
        assert data["tasks"] != []
        for task in data["tasks"]:
            assert task["packages"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"branch": BRANCH_IN_DB, "tasks_limit": 10, "task_owner": None, "status_code": 200},
        {"branch": BRANCH_IN_DB, "tasks_limit": 10, "task_owner": MAINTAINER_IN_DB, "status_code": 200},
        {"branch": BRANCH_NOT_IN_DB, "tasks_limit": 10, "task_owner": None, "status_code": 400},
        {"branch": BRANCH_IN_DB, "tasks_limit": 0, "task_owner": None, "status_code": 400},
        {"branch": BRANCH_IN_DB, "tasks_limit": -10, "task_owner": None, "status_code": 400},
        {"branch": BRANCH_IN_DB, "tasks_limit": 10, "task_owner": MAINTAINER_NOT_IN_DB, "status_code": 404},
    ],
)
def test_last_packages(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("status_code",):
            continue
        if v is not None:
            params[k] = v
    url = url_for("api.site_route_last_task_packages")
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["length"] != 0
        assert data["tasks"] != []
        for task in data["tasks"]:
            assert task["packages"] != []
