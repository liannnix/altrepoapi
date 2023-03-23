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


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "branch": "sisyphus",
            "packages_names": ["awesome"],
            "result": [
                {
                    "name": "awesome",
                    "updated": "2023-03-08T19:55:53",
                    "members": ["lakostis", "@everybody"],
                },
            ],
            "status_code": 200,
        },
        {
            "branch": "sisyphus",
            "packages_names": ["coreutils", "binutils"],
            "result": [
                {
                    "name": "binutils",
                    "updated": "2022-08-02T18:24:02",
                    "members": ["glebfm"],
                },
                {
                    "name": "coreutils",
                    "updated": "2021-09-14T12:19:00",
                    "members": ["@core"],
                },
            ],
            "status_code": 200,
        },
        {
            "branch": "sisyphus",
            "packages_names": ["non-existing-package-in-sisyphus"],
            "result": [],
            "status_code": 200,
        },
        {
            "branch": "non-existing-branch",
            "packages_names": ["placeholder"],
            "result": [],
            "status_code": 400,
        },
    ],
)
def test_acl_by_packages(client, kwargs):
    url = url_for(
        "api.acl_route_acl_by_packages",
        branch=kwargs["branch"],
        packages_names=",".join(kwargs["packages_names"]),
    )
    response = client.get(url)
    assert response.status_code == kwargs["status_code"]

    if response.status_code == 200:
        assert response.json["branch"] == kwargs["branch"]

        result = response.json["packages"]

        assert len(result) == len(kwargs["result"])
        for res, test in zip(result, kwargs["result"]):
            assert res["name"] == test["name"]
            assert res["updated"] == test["updated"]
            assert res["members"] == test["members"]


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "nickname": "amakeenk",
            "branches": [
                {
                    "name": "p10",
                    "groups": [
                        "@tester",
                    ],
                },
            ],
            "status_code": 200,
        },
        {
            "nickname": "ldv",
            "branches": [
                {
                    "name": "p10",
                    "groups": ["@core", "@cpan", "@kernel", "@maint", "@openldap"],
                },
                {
                    "name": "sisyphus",
                    "groups": ["@core", "@cpan", "@kernel", "@openldap"],
                },
            ],
            "status_code": 200,
        },
    ],
)
def test_acl_find_groups(client, kwargs):
    url = url_for(
        "api.acl_route_maintainer_groups",
        nickname=kwargs["nickname"],
        branch=",".join(branch["name"] for branch in kwargs["branches"]),
    )
    response = client.get(url)
    assert response.status_code == kwargs["status_code"]

    if response.status_code == 200:
        assert response.json["nickname"] == kwargs["nickname"]

        branches = response.json["branches"]

        assert len(branches) == len(kwargs["branches"])
        for res, test in zip(branches, kwargs["branches"]):
            assert res["name"] == test["name"]
            assert res["groups"] == test["groups"]
