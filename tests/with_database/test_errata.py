import pytest
import zipfile
from io import BytesIO
from flask import url_for

BRANCH_IN_DB = "sisyphus"
BRANCH_IN_DB2 = "p10"
BRANCH_NOT_IN_DB = "fakebranch"

PKG_NAME_IN_DB = "curl"
PKG_NAME_NOT_IN_DB = "fakepackage"

PU_ERRATA_ID_IN_DB_1 = "ALT-PU-2023-2000-1"
PU_ERRATA_ID_IN_DB_2 = "ALT-PU-2013-1000-1"
PU_ERRATA_ID_NOT_IN_DB = "ALT-PU-2999-1000-1"
PU_ERRATA_ID_NOT_VALID_1 = "ALT-PU-123-1000-1"
PU_ERRATA_ID_NOT_VALID_2 = "ALT-XX-2000-9999-9"

BU_ERRATA_ID_IN_DB_1 = "ALT-BU-2023-3800-1"
BU_ERRATA_ID_IN_DB_2 = "ALT-BU-2013-1350-1"
BU_ERRATA_ID_NOT_IN_DB = "ALT-BU-2999-1000-1"
BU_ERRATA_ID_NOT_VALID_1 = "ALT-BU-123-1000-1"
BU_ERRATA_ID_NOT_VALID_2 = "ALT-XX-2000-9999-9"


def test_errata_ids(client):
    url = url_for("api.errata_route_errata_ids")
    response = client.get(url)
    data = response.json
    assert response.status_code == 200
    assert data != {}
    assert data["errata_ids"] != []
    assert PU_ERRATA_ID_IN_DB_2 in data["errata_ids"]


def test_errata_export_oval_branches(client):
    url = url_for("api.errata_route_oval_export_branches")
    response = client.get(url)
    data = response.json
    assert response.status_code == 200
    assert data != {}
    assert data["branches"] != []
    assert BRANCH_IN_DB2 in data["branches"]
    assert BRANCH_IN_DB not in data["branches"]


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "branch": BRANCH_IN_DB2,
            "package_name": PKG_NAME_IN_DB,
            "one_file": None,
            "files": 1,
            "status_code": 200,
        },
        {
            "branch": BRANCH_IN_DB2,
            "package_name": PKG_NAME_IN_DB,
            "one_file": False,
            "files": 2,
            "status_code": 200,
        },
        {
            "branch": BRANCH_IN_DB,
            "package_name": PKG_NAME_IN_DB,
            "one_file": None,
            "files": 1,
            "status_code": 400,
        },
        {
            "branch": BRANCH_IN_DB2,
            "package_name": PKG_NAME_NOT_IN_DB,
            "one_file": None,
            "files": 1,
            "status_code": 404,
        },
    ],
)
def test_errata_export_oval(client, kwargs):
    url = url_for("api.errata_route_oval_export", **{"branch": kwargs["branch"]})
    params = {}
    for k, v in kwargs.items():
        if k in ("status_code", "branch", "files"):
            continue
        if v is not None:
            params[k] = v
    response = client.get(url, query_string=params)
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert response.content_type == "application/zip"
        data = BytesIO(response.get_data())
        zip = zipfile.ZipFile(file=data, mode="r")
        assert len(zip.filelist) >= kwargs["files"]


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "branch": BRANCH_IN_DB,
            "name": PKG_NAME_IN_DB,
            "errata_id": None,
            "status_code": 200,
        },
        {
            "branch": None,
            "name": None,
            "errata_id": PU_ERRATA_ID_IN_DB_1,
            "status_code": 200,
        },
        {
            "branch": None,
            "name": None,
            "errata_id": None,
            "status_code": 400,
        },
        {
            "branch": BRANCH_NOT_IN_DB,
            "name": None,
            "errata_id": None,
            "status_code": 400,
        },
        {
            "branch": BRANCH_IN_DB,
            "name": PKG_NAME_NOT_IN_DB,
            "errata_id": None,
            "status_code": 404,
        },
        {
            "branch": None,
            "name": None,
            "errata_id": PU_ERRATA_ID_NOT_IN_DB,
            "status_code": 404,
        },
    ],
)
def test_errata_search(client, kwargs):
    url = url_for("api.errata_route_search")
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
        assert data["erratas"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "payload": {"errata_ids": [PU_ERRATA_ID_IN_DB_1, PU_ERRATA_ID_IN_DB_2]},
            "status_code": 200,
        },
        {
            "payload": {"errata_ids": [PU_ERRATA_ID_NOT_VALID_1]},
            "status_code": 400,
        },
        {
            "payload": {"errata_ids": [PU_ERRATA_ID_NOT_VALID_2]},
            "status_code": 400,
        },
        {
            "payload": {"errata_ids": [PU_ERRATA_ID_NOT_IN_DB]},
            "status_code": 404,
        },
        {
            "payload": {"errata_ids": []},
            "status_code": 404,
        },
    ],
)
def test_errata_packages_updates(client, kwargs):
    url = url_for("api.errata_route_packages_updates")
    response = client.post(url, json=kwargs["payload"], content_type="application/json")
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["packages_updates"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "payload": {"errata_ids": [BU_ERRATA_ID_IN_DB_1, BU_ERRATA_ID_IN_DB_2]},
            "status_code": 200,
        },
        {
            "payload": {"errata_ids": [BU_ERRATA_ID_NOT_VALID_1]},
            "status_code": 400,
        },
        {
            "payload": {"errata_ids": [BU_ERRATA_ID_NOT_VALID_2]},
            "status_code": 400,
        },
        {
            "payload": {"errata_ids": [BU_ERRATA_ID_NOT_IN_DB]},
            "status_code": 404,
        },
        {
            "payload": {"errata_ids": []},
            "status_code": 404,
        },
    ],
)
def test_errata_branches_updates(client, kwargs):
    url = url_for("api.errata_route_branches_updates")
    response = client.post(url, json=kwargs["payload"], content_type="application/json")
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["branches_updates"] != []
        for bu in data["branches_updates"]:
            assert bu["packages_updates"] != []
