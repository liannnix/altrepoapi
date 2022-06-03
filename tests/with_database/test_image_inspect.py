import pytest


FAKE_BRANCH = "fakebranch"
TEST_BRANCH = "p10"
PKG_INVALID = {"fake": 0}
PKG_REGULAR_IN_DB = {
    "pkg_hash": "2688766808674986712",
    "pkg_name": "bash4",
    "pkg_epoch": 0,
    "pkg_version": "4.4.23",
    "pkg_release": "alt1",
    "pkg_arch": "x86_64",
    "pkg_disttag": "sisyphus+278099.100.1.1",
    "pkg_buildtime": 1626027306,
}
PKG_REGULAR_IN_TASK = {
    # "pkg_hash": "2758010506349322063",
    # "pkg_name": "curl",
    # "pkg_epoch": 0,
    # "pkg_version": "1.0",
    # "pkg_release": "alt1",
    # "pkg_arch": "i586",
    # "pkg_disttag": "sisyphus+275725.100.1.1",
    # "pkg_buildtime": 1626030376
}
PKG_REGULAR_NOT_IN_DB = {
    "pkg_hash": "2758010506349322063",
    "pkg_name": "curl",
    "pkg_epoch": 0,
    "pkg_version": "1.0",
    "pkg_release": "alt1",
    "pkg_arch": "i586",
    "pkg_disttag": "sisyphus+275725.100.1.1",
    "pkg_buildtime": 1626030376,
}


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "payload": PKG_INVALID,
            "branch": TEST_BRANCH,
            "not_in_branch": 0,
            "found_in_tasks": 0,
            "not_found_in_db": 0,
            "status_code": 400,
        },
        {
            "payload": PKG_REGULAR_NOT_IN_DB,
            "branch": TEST_BRANCH,
            "not_in_branch": 1,
            "found_in_tasks": 0,
            "not_found_in_db": 1,
            "status_code": 200,
        },
        {
            "payload": PKG_REGULAR_IN_DB,
            "branch": TEST_BRANCH,
            "not_in_branch": 0,
            "found_in_tasks": 0,
            "not_found_in_db": 0,
            "status_code": 200,
        },
        {
            "payload": PKG_REGULAR_IN_DB,
            "branch": FAKE_BRANCH,
            "not_in_branch": 0,
            "found_in_tasks": 0,
            "not_found_in_db": 0,
            "status_code": 400,
        },
    ],
)
def test_image_inspect_regular(client, kwargs):
    url = "api/image/inspect/regular"
    payload = {
        "branch": kwargs["branch"],
        "packages": [
            kwargs["payload"],
        ],
    }
    response = client.post(url, json=payload, content_type="application/json")
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["not_in_branch"] == kwargs["not_in_branch"]
        assert data["found_in_tasks"] == kwargs["found_in_tasks"]
        assert data["not_found_in_db"] == kwargs["not_found_in_db"]
        if data["found_in_tasks"] != 0:
            assert data["packages_in_tasks"] != []
        if data["not_found_in_db"] != 0:
            assert data["packages_not_in_db"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "payload": PKG_INVALID,
            "branch": TEST_BRANCH,
            "in_branch": 0,
            "not_in_branch": 0,
            "found_in_tasks": 0,
            "not_found_in_db": 0,
            "status_code": 400,
        },
        {
            "payload": PKG_REGULAR_NOT_IN_DB,
            "branch": TEST_BRANCH,
            "in_branch": 0,
            "not_in_branch": 1,
            "found_in_tasks": 0,
            "not_found_in_db": 1,
            "status_code": 200,
        },
        {
            "payload": PKG_REGULAR_IN_DB,
            "branch": TEST_BRANCH,
            "in_branch": 1,
            "not_in_branch": 0,
            "found_in_tasks": 0,
            "not_found_in_db": 0,
            "status_code": 200,
        },
        {
            "payload": PKG_REGULAR_IN_DB,
            "branch": FAKE_BRANCH,
            "in_branch": 0,
            "not_in_branch": 0,
            "found_in_tasks": 0,
            "not_found_in_db": 0,
            "status_code": 400,
        },
    ],
)
def test_image_inspect_sp(client, kwargs):
    url = "api/image/inspect/sp"
    payload = {
        "branch": kwargs["branch"],
        "packages": [
            kwargs["payload"],
        ],
    }
    response = client.post(url, json=payload, content_type="application/json")
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["in_branch"] == kwargs["in_branch"]
        assert data["not_in_branch"] == kwargs["not_in_branch"]
        assert data["found_in_tasks"] == kwargs["found_in_tasks"]
        assert data["not_found_in_db"] == kwargs["not_found_in_db"]
        assert data["packages"] != []
