import pytest
import zipfile
from io import BytesIO
from flask import url_for

BRANCH_IN_DB = "sisyphus"
BRANCH_IN_DB2 = "p10"
BRANCH_IN_DB3 = "sisyphus_e2k"
BRANCH_NOT_IN_DB = "fakebranch"
BRANCH_IN_DB_NO_ERRATA = "4.0"

ERRATA_TYPES_IN_DB = ["packages", "repository", "bug", "vuln"]

PKG_NAME_IN_DB = "curl"
PKG_NAME_IN_DB2 = "libcurl"
PKG_NAME_NOT_IN_DB = "fakepackage"

PU_ERRATA_ID_IN_DB_1 = "ALT-PU-2023-2000-2"
PU_ERRATA_ID_IN_DB_2 = "ALT-PU-2013-1000-1"
PU_ERRATA_ID_IN_DB_3 = "ALT-PU-2023-6266-3"
PU_ERRATA_ID_NOT_IN_DB = "ALT-PU-2999-1000-1"
PU_ERRATA_ID_NOT_VALID_1 = "ALT-PU-123-1000-1"
PU_ERRATA_ID_NOT_VALID_2 = "ALT-XX-2000-9999-9"

BU_ERRATA_ID_IN_DB_1 = "ALT-BU-2023-3800-1"
BU_ERRATA_ID_IN_DB_2 = "ALT-BU-2013-1350-1"
BU_ERRATA_ID_IN_DB_3 = "ALT-BU-2023-4441-1"
BU_ERRATA_ID_NOT_IN_DB = "ALT-BU-2999-1000-1"
BU_ERRATA_ID_NOT_VALID_1 = "ALT-BU-123-1000-1"
BU_ERRATA_ID_NOT_VALID_2 = "ALT-XX-2000-9999-9"

VUILN_ID_CVE_IN_DB = "CVE-2022-22576"
VUILN_ID_CVE_IN_DB2 = "CVE-2022-34903"
VUILN_ID_BDU_IN_DB = "BDU:2022-03036"
VUILN_ID_BDU_IN_DB2 = "BDU:2024-07527"
VUILN_ID_BUG_IN_DB = "45281"
VUILN_ID_BUG_IN_DB2 = "45305"
VULN_ID_BAD = "ABC-123"

BUG_IN_ERRATA = "46487"
BUG_NOT_IN_ERRATA = "11111"

IMG_UUID_IN_DB = "4c27ea7d-cea7-4a8e-8fb3-452e680a3aca"
IMG_UUID_NOT_IN_DB = "4624e687-0ddb-4cbd-933a-111111111111"


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
            "vuln_id": None,
            "errata_id": None,
            "status_code": 200,
        },
        {
            "branch": None,
            "name": None,
            "vuln_id": None,
            "errata_id": PU_ERRATA_ID_IN_DB_1,
            "status_code": 200,
        },
        {
            "branch": BRANCH_IN_DB,
            "name": None,
            "vuln_id": VUILN_ID_CVE_IN_DB,
            "errata_id": None,
            "status_code": 200,
        },
        {
            "branch": BRANCH_IN_DB,
            "name": None,
            "vuln_id": VUILN_ID_BDU_IN_DB,
            "errata_id": None,
            "status_code": 200,
        },
        {
            "branch": BRANCH_IN_DB,
            "name": None,
            "vuln_id": VUILN_ID_BUG_IN_DB,
            "errata_id": None,
            "status_code": 200,
        },
        {
            "branch": None,
            "name": None,
            "vuln_id": None,
            "errata_id": None,
            "status_code": 400,
        },
        {
            "branch": BRANCH_NOT_IN_DB,
            "name": None,
            "vuln_id": None,
            "errata_id": None,
            "status_code": 400,
        },
        {
            "branch": None,
            "name": None,
            "vuln_id": VULN_ID_BAD,
            "errata_id": None,
            "status_code": 400,
        },
        {
            "branch": None,
            "name": None,
            "vuln_id": None,
            "errata_id": PU_ERRATA_ID_NOT_VALID_1,
            "status_code": 400,
        },
        {
            "branch": BRANCH_IN_DB,
            "name": PKG_NAME_NOT_IN_DB,
            "vuln_id": None,
            "errata_id": None,
            "status_code": 404,
        },
        {
            "branch": None,
            "name": None,
            "vuln_id": None,
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
            "status_code": 400,
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
            "status_code": 400,
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


@pytest.mark.parametrize(
    "kwargs",
    [
        {"input": BU_ERRATA_ID_IN_DB_3, "status_code": 200},
        {"input": BU_ERRATA_ID_IN_DB_3, "branch": BRANCH_IN_DB, "status_code": 200},
        {
            "input": BU_ERRATA_ID_IN_DB_3,
            "branch": BRANCH_IN_DB,
            "type": ERRATA_TYPES_IN_DB[1],
            "status_code": 200,
        },
        {
            "type": ERRATA_TYPES_IN_DB[2],
            "status_code": 200,
        },
        {
            "type": ERRATA_TYPES_IN_DB[3],
            "status_code": 200,
        },
        {
            "input": BU_ERRATA_ID_IN_DB_3,
            "branch": BRANCH_IN_DB,
            "type": ERRATA_TYPES_IN_DB[1],
            "status_code": 200,
        },
        {"type": ERRATA_TYPES_IN_DB[0], "page": 1, "limit": 10, "status_code": 200},
        {"input": PU_ERRATA_ID_IN_DB_1, "status_code": 200},
        {"input": BUG_IN_ERRATA, "status_code": 200},
        {"input": VUILN_ID_BDU_IN_DB, "status_code": 200},
        {"status_code": 200},
        {"page": 1, "limit": 10, "status_code": 200},
        {"page": 1, "limit": -1, "status_code": 400},
        {"page": -1, "limit": 10, "status_code": 400},
        {
            "input": VUILN_ID_BDU_IN_DB,
            "branch": BRANCH_IN_DB_NO_ERRATA,
            "status_code": 404,
        },
        {
            "input": BUG_NOT_IN_ERRATA,
            "branch": BRANCH_IN_DB_NO_ERRATA,
            "status_code": 404,
        },
        {"input": BU_ERRATA_ID_NOT_IN_DB, "status_code": 404},
        {"input": PU_ERRATA_ID_NOT_IN_DB, "status_code": 404},
    ],
)
def test_find_erratas(client, kwargs):
    url = url_for("api.errata_route_find_erratas")
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
        assert data["erratas"] != []

        for elem in data["erratas"]:
            if kwargs.get("input"):
                assert kwargs["input"].lower() in (
                    [elem["errata_id"].lower()]
                    + [vuln["id"].lower() for vuln in elem["vulnerabilities"]]
                )

            if kwargs.get("branch"):
                assert kwargs["branch"] == elem["branch"]

            if kwargs.get("type"):
                if kwargs.get("type") == ERRATA_TYPES_IN_DB[0]:
                    assert elem["eh_type"] in ("branch", "task")
                elif kwargs.get("type") == ERRATA_TYPES_IN_DB[1]:
                    assert elem["eh_type"] in ("bulletin",)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"uuid": IMG_UUID_IN_DB, "branch": BRANCH_IN_DB2, "status_code": 200},
        {
            "uuid": IMG_UUID_IN_DB,
            "branch": BRANCH_IN_DB2,
            "limit": 10,
            "status_code": 200,
        },
        {
            "uuid": IMG_UUID_IN_DB,
            "branch": BRANCH_IN_DB2,
            "input": PKG_NAME_IN_DB2,
            "status_code": 200,
        },
        {
            "uuid": IMG_UUID_IN_DB,
            "branch": BRANCH_IN_DB2,
            "input": VUILN_ID_CVE_IN_DB2,
            "status_code": 200,
        },
        {
            "uuid": IMG_UUID_IN_DB,
            "branch": BRANCH_IN_DB2,
            "input": VUILN_ID_BDU_IN_DB2,
            "status_code": 200,
        },
        {
            "uuid": IMG_UUID_IN_DB,
            "branch": BRANCH_IN_DB2,
            "input": VUILN_ID_BUG_IN_DB2,
            "status_code": 200,
        },
        {
            "uuid": IMG_UUID_IN_DB,
            "branch": BRANCH_IN_DB2,
            "input": PU_ERRATA_ID_IN_DB_3,
            "status_code": 200,
        },
        {
            "uuid": IMG_UUID_IN_DB,
            "branch": BRANCH_IN_DB2,
            "type": ERRATA_TYPES_IN_DB[1],
            "status_code": 404,
        },
        {
            "uuid": IMG_UUID_IN_DB,
            "branch": BRANCH_IN_DB2,
            "input": PKG_NAME_NOT_IN_DB,
            "status_code": 404,
        },
        {
            "uuid": IMG_UUID_IN_DB,
            "branch": BRANCH_IN_DB2,
            "page": 1,
            "limit": -1,
            "status_code": 400,
        },
        {
            "uuid": IMG_UUID_IN_DB,
            "branch": BRANCH_IN_DB2,
            "page": -1,
            "limit": 10,
            "status_code": 400,
        },
        {"uuid": IMG_UUID_IN_DB, "branch": BRANCH_IN_DB, "status_code": 404},
        {"uuid": IMG_UUID_IN_DB, "branch": BRANCH_IN_DB, "status_code": 404},
        {"uuid": IMG_UUID_NOT_IN_DB, "branch": BRANCH_IN_DB2, "status_code": 404},
    ],
)
def test_find_image_erratas(client, kwargs):
    url = url_for("api.errata_route_find_image_erratas")
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
        assert data["erratas"] != []

        for elem in data["erratas"]:
            if kwargs.get("input"):
                res = [elem["errata_id"].lower(), elem["pkg_name"].lower()] + [
                    vuln["id"].lower() for vuln in elem["vulnerabilities"]
                ]
                assert kwargs["input"].lower() in res

            assert kwargs["branch"] == elem["branch"]

            if kwargs.get("type"):
                if kwargs.get("type") == ERRATA_TYPES_IN_DB[0]:
                    assert elem["eh_type"] in ("branch", "task")
                elif kwargs.get("type") == ERRATA_TYPES_IN_DB[1]:
                    assert elem["eh_type"] in ("bulletin",)

            if kwargs.get("limit"):
                assert len(data["erratas"]) <= kwargs.get("limit")
