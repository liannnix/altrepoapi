import pytest
from flask import url_for


SRC_PACKAGE_IN_DB = "curl"
BIN_PACKAGE_IN_DB = "grep"
PACKAGE_NOT_IN_DB = "fakepackage"
MAINTAINER_IN_DB = "rider"
MAINTAINER_NOT_IN_DB = "fakemaintainer"
EDITION_IN_DB = 'slinux'
EDITION_NOT_DB = 'fake'
BRANCH_IN_DB = 'p10'
BRANCH_NOT_DB = 'fake'



@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "package_name": SRC_PACKAGE_IN_DB,
            "package_type": "source",
            "status_code": 200,
        },
        {
            "package_name": BIN_PACKAGE_IN_DB,
            "package_type": "binary",
            "status_code": 200,
        },
        {"package_name": PACKAGE_NOT_IN_DB, "package_type": None, "status_code": 404},
        {"package_name": None, "package_type": None, "status_code": 400},
        {"package_name": SRC_PACKAGE_IN_DB, "package_type": "abc", "status_code": 400},
    ],
)
def test_bugzilla_by_package(client, kwargs):
    url = url_for("api.bug_route_bugzilla_by_package")
    params = {}
    for k, v in kwargs.items():
        if k in ("status_code",):
            continue
        if v is not None:
            params[k] = v
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["length"] != 0
        assert data["bugs"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"maintainer_nickname": MAINTAINER_IN_DB, "by_acl": None, "status_code": 200},
        {"maintainer_nickname": MAINTAINER_IN_DB, "by_acl": "none", "status_code": 200},
        {
            "maintainer_nickname": MAINTAINER_IN_DB,
            "by_acl": "by_nick",
            "status_code": 200,
        },
        {
            "maintainer_nickname": MAINTAINER_IN_DB,
            "by_acl": "by_nick_leader",
            "status_code": 200,
        },
        {
            "maintainer_nickname": MAINTAINER_IN_DB,
            "by_acl": "by_nick_or_group",
            "status_code": 200,
        },
        {
            "maintainer_nickname": MAINTAINER_IN_DB,
            "by_acl": "by_nick_leader_and_group",
            "status_code": 200,
        },
        {"maintainer_nickname": None, "by_acl": None, "status_code": 400},
        {"maintainer_nickname": MAINTAINER_IN_DB, "by_acl": "abc", "status_code": 400},
        {
            "maintainer_nickname": MAINTAINER_NOT_IN_DB,
            "by_acl": None,
            "status_code": 404,
        },
    ],
)
def test_bugzilla_by_maintainer(client, kwargs):
    url = url_for("api.bug_route_bugzilla_by_maintainer")
    params = {}
    for k, v in kwargs.items():
        if k in ("status_code",):
            continue
        if v is not None:
            params[k] = v
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["length"] != 0
        assert data["bugs"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"branch": BRANCH_IN_DB, "edition": EDITION_IN_DB, "status_code": 200},
        {"branch": BRANCH_NOT_DB, "edition": EDITION_IN_DB, "status_code": 400},
        {"branch": BRANCH_IN_DB, "edition": EDITION_NOT_DB, "status_code": 400},
        {"branch": 'sisyphus', "edition": EDITION_IN_DB, "status_code": 404},
    ],
)
def test_bugzilla_by_image_edition(client, kwargs):
    url = url_for("api.bug_route_bugzilla_by_image_edition")
    params = {}
    for k, v in kwargs.items():
        if k in ("status_code",):
            continue
        if v is not None:
            params[k] = v
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["length"] != 0
        assert data["bugs"] != []
