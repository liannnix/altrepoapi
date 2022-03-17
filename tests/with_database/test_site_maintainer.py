import pytest
from flask import url_for

BRANCH_IN_DB = "sisyphus"
BRANCH_NOT_IN_DB = "fakebranch"
MAINTAINER_IN_DB = "rider"
MAINTAINER_NOT_IN_DB = "fakemaintainer"

@pytest.mark.parametrize(
    "kwargs",
    [
        {"branch": BRANCH_IN_DB, "status_code": 200},
        {"branch": BRANCH_NOT_IN_DB, "status_code": 400},
    ],
)
def test_all_maintainers(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("status_code",):
            continue
        if v is not None:
            params[k] = v
    url = url_for("api.site_route_maintainers_all")
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["length"] != 0
        assert data["maintainers"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"branch": BRANCH_IN_DB, "maintainer_nickname": MAINTAINER_IN_DB, "status_code": 200},
        {"branch": BRANCH_NOT_IN_DB, "maintainer_nickname": MAINTAINER_IN_DB, "status_code": 400},
        {"branch": BRANCH_IN_DB, "maintainer_nickname": MAINTAINER_NOT_IN_DB, "status_code": 404},
    ],
)
def test_maintainer_info(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("status_code",):
            continue
        if v is not None:
            params[k] = v
    url = url_for("api.site_route_maintainers_info")
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["information"] != {}
        assert data["information"]["packager_name"] != ""
        assert data["information"]["count_source_pkg"] > 0
        assert data["information"]["packager_nickname"] == kwargs["maintainer_nickname"]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"branch": BRANCH_IN_DB, "maintainer_nickname": MAINTAINER_IN_DB, "by_acl": None, "status_code": 200},
        {"branch": BRANCH_IN_DB, "maintainer_nickname": MAINTAINER_IN_DB, "by_acl": "none", "status_code": 200},
        {"branch": BRANCH_IN_DB, "maintainer_nickname": MAINTAINER_IN_DB, "by_acl": "by_nick", "status_code": 200},
        {"branch": BRANCH_IN_DB, "maintainer_nickname": MAINTAINER_IN_DB, "by_acl": "by_nick_leader", "status_code": 200},
        {"branch": BRANCH_IN_DB, "maintainer_nickname": MAINTAINER_IN_DB, "by_acl": "by_nick_or_group", "status_code": 200},
        {"branch": BRANCH_IN_DB, "maintainer_nickname": MAINTAINER_IN_DB, "by_acl": "by_nick_leader_and_group", "status_code": 200},
        {"branch": BRANCH_NOT_IN_DB, "maintainer_nickname": MAINTAINER_IN_DB, "by_acl": None, "status_code": 400},
        {"branch": BRANCH_IN_DB, "maintainer_nickname": MAINTAINER_IN_DB, "by_acl": "abc", "status_code": 400},
        {"branch": BRANCH_IN_DB, "maintainer_nickname": MAINTAINER_NOT_IN_DB, "by_acl": None, "status_code": 404},
    ],
)
def test_maintainer_packages(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("status_code",):
            continue
        if v is not None:
            params[k] = v
    url = url_for("api.site_route_maintainer_packages")
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["length"] != 0
        assert data["packages"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"maintainer_nickname": MAINTAINER_IN_DB, "status_code": 200},
        {"maintainer_nickname": MAINTAINER_NOT_IN_DB, "status_code": 404},
    ],
)
def test_maintainer_branches(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("status_code",):
            continue
        if v is not None:
            params[k] = v
    url = url_for("api.site_route_maintainer_branches")
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["length"] != 0
        assert data["branches"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"branch": BRANCH_IN_DB, "maintainer_nickname": MAINTAINER_IN_DB, "by_acl": None, "status_code": 200},
        {"branch": BRANCH_IN_DB, "maintainer_nickname": MAINTAINER_IN_DB, "by_acl": "none", "status_code": 200},
        {"branch": BRANCH_IN_DB, "maintainer_nickname": MAINTAINER_IN_DB, "by_acl": "by_nick", "status_code": 200},
        {"branch": BRANCH_IN_DB, "maintainer_nickname": MAINTAINER_IN_DB, "by_acl": "by_nick_leader", "status_code": 200},
        {"branch": BRANCH_IN_DB, "maintainer_nickname": MAINTAINER_IN_DB, "by_acl": "by_nick_or_group", "status_code": 200},
        {"branch": BRANCH_IN_DB, "maintainer_nickname": MAINTAINER_IN_DB, "by_acl": "by_nick_leader_and_group", "status_code": 200},
        {"branch": BRANCH_NOT_IN_DB, "maintainer_nickname": MAINTAINER_IN_DB, "by_acl": None, "status_code": 400},
        {"branch": BRANCH_IN_DB, "maintainer_nickname": MAINTAINER_IN_DB, "by_acl": "abc", "status_code": 400},
        {"branch": BRANCH_IN_DB, "maintainer_nickname": MAINTAINER_NOT_IN_DB, "by_acl": None, "status_code": 404},
    ],
)
def test_repocop_by_maintainer(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("status_code",):
            continue
        if v is not None:
            params[k] = v
    url = url_for("api.site_route_repocop_by_maintainer")
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["length"] != 0
        assert data["packages"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"branch": BRANCH_IN_DB, "maintainer_nickname": MAINTAINER_IN_DB, "by_acl": None, "status_code": 200},
        {"branch": BRANCH_IN_DB, "maintainer_nickname": MAINTAINER_IN_DB, "by_acl": "none", "status_code": 200},
        {"branch": BRANCH_IN_DB, "maintainer_nickname": MAINTAINER_IN_DB, "by_acl": "by_nick", "status_code": 200},
        {"branch": BRANCH_IN_DB, "maintainer_nickname": MAINTAINER_IN_DB, "by_acl": "by_nick_leader", "status_code": 200},
        {"branch": BRANCH_IN_DB, "maintainer_nickname": MAINTAINER_IN_DB, "by_acl": "by_nick_or_group", "status_code": 200},
        {"branch": BRANCH_IN_DB, "maintainer_nickname": MAINTAINER_IN_DB, "by_acl": "by_nick_leader_and_group", "status_code": 200},
        {"branch": BRANCH_NOT_IN_DB, "maintainer_nickname": MAINTAINER_IN_DB, "by_acl": None, "status_code": 400},
        {"branch": BRANCH_IN_DB, "maintainer_nickname": MAINTAINER_IN_DB, "by_acl": "abc", "status_code": 400},
        {"branch": BRANCH_IN_DB, "maintainer_nickname": MAINTAINER_NOT_IN_DB, "by_acl": None, "status_code": 404},
    ],
)
def test_beehive_errors_by_maintainer(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("status_code",):
            continue
        if v is not None:
            params[k] = v
    url = url_for("api.site_route_beehive_by_maintainer")
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["length"] != 0
        assert data["beehive"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"maintainer_nickname": MAINTAINER_IN_DB, "by_acl": None, "status_code": 200},
        {"maintainer_nickname": MAINTAINER_IN_DB, "by_acl": "none", "status_code": 200},
        {"maintainer_nickname": MAINTAINER_IN_DB, "by_acl": "by_nick", "status_code": 200},
        {"maintainer_nickname": MAINTAINER_IN_DB, "by_acl": "by_nick_leader", "status_code": 200},
        {"maintainer_nickname": MAINTAINER_IN_DB, "by_acl": "by_nick_or_group", "status_code": 200},
        {"maintainer_nickname": MAINTAINER_IN_DB, "by_acl": "by_nick_leader_and_group", "status_code": 200},
        {"maintainer_nickname": MAINTAINER_IN_DB, "by_acl": "abc", "status_code": 400},
        {"maintainer_nickname": MAINTAINER_NOT_IN_DB, "by_acl": None, "status_code": 404},
    ],
)
def test_watch_by_maintainer(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("status_code",):
            continue
        if v is not None:
            params[k] = v
    url = url_for("api.site_route_watch_by_maintainer")
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["length"] != 0
        assert data["packages"] != []
