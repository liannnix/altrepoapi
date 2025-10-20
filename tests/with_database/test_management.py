import pytest
from flask import url_for

BRANCH_IN_DB = "sisyphus"
BRANCH_NOT_IN_DB = "fakebranch"
TASK_IN_DB = "310692"
TASK_IN_DB2 = "326814"
TASK_DEL_PACKAGES_IN_DB = "327131"
TASK_NOT_IN_DB = "123456789"
DELETED_TASK_IN_DB = "307229"
OWNER_IN_DB = "rider"
OWNER_NOT_IN_DB = "fakeowner"
PACKAGE_IN_DB = "python3"
PACKAGE_NOT_IN_DB = "fakepackagename"
PACKAGE_UNMAPPED_IN_DB = "python-module-Draco"
PACKAGE_UNMAPPED_IN_DB2 = "python,draco"
PACKAGE_UNMAPPED_NOT_IN_DB = "fakepackagename"

VULN_IN_DB = "CVE-2019-18276"
VULN_FIXED_IN_DB = "CVE-2024-4368"
VULN_IN_DB2 = "BDU:2020-03946"
VULN_IN_DB3 = "GHSA-q34m-jh98-gwm2"
VULN_IN_DB3 = "BDU:2015-05839"  # BDU that contains mulyiple CVE references
VULN_NOT_IN_DB = "CVE-1111-11111"
VULN_NOT_IN_DB2 = "BDU:1111-11111"
VULN_NOT_IN_DB3 = "GHSA-2222-2222-2222"

BUG_IN_DB = "36250"
BUG_NOT_IN_DB = "11111111"

PU_ERRATA_ID_IN_DB_1 = "ALT-PU-2023-2000-2"
PU_ERRATA_ID_IN_DB_2 = "ALT-PU-2013-1000-1"
PU_ERRATA_ID_NOT_IN_DB = "ALT-PU-2999-1000-1"
PU_ERRATA_ID_NOT_VALID_1 = "ALT-PU-123-1000-1"
PU_ERRATA_ID_NOT_VALID_2 = "ALT-XX-2000-9999-9"

CH_PU_ERRATA_ID_IN_DB_1 = "ALT-PU-2025-1942-2"
CH_BU_ERRATA_ID_IN_DB_1 = "ALT-BU-2013-1467-1"

CH_USER_IN_DB = "altrepodb"
CH_USER_NOT_IN_DB = "test_user"

CH_MODULE_IN_DB_1 = "errata"
CH_MODULE_IN_DB_2 = "pnc"
CH_MODULE_NOT_IN_DB = "test"

CH_CHANGE_TYPE_IN_DB_1 = "create"
CH_CHANGE_TYPE_IN_DB_2 = "discard"
CH_CHANGE_TYPE_IN_DB_3 = "update"
CH_CHANGE_TYPE_NOT_IN_DB = "test_change_type"

BU_ERRATA_ID_IN_DB = "ALT-BU-2013-1338-1"
BU_ERRATA_ID_NOT_IN_DB = "ALT-BU-2999-1000-1"

VALID_ACCESS_TOKEN = "valid_token"
INVALID_ACCESS_TOKEN = "invalid_token"

CPE_IN_DB = "cpe:2.3:a:curl:curl:*:*:*:*:*:*:*:*"
CPE_IN_DB2 = "cpe:2.3:a:curl:curl:8.5.0:*:*:*:*:*:*:*"
CPE_NOT_IN_DB = "cpe:2.3:a:test:test:*:*:*:*:*:*:*:*"

PROJECT_NAME_IN_DB = "mongo-c-driver"
PROJECT_NAME_NOT_IN_DB = "test_project_name"

IMG_IN_DB = "alt-kworkstation-10.2.1-install-x86_64.iso"
IMG_NOT_IN_DB = "test_image"

DEFAULT_REASON_IN_DB = (
    "Incorrect CPE mapping; this CVE was assigned too broadly and does not apply here."
)
DEFAULT_REASON_NOT_IN_DB = "test_default_reasons"


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "input": TASK_IN_DB,
            "branch": BRANCH_IN_DB,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": TASK_IN_DB,
            "branch": BRANCH_IN_DB,
            "state": "DONE",
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": TASK_IN_DB,
            "branch": BRANCH_IN_DB,
            "state": "all",
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": TASK_IN_DB,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": TASK_IN_DB2,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": f"#{TASK_IN_DB}",
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": "bug:47017",
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": VULN_FIXED_IN_DB,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": VULN_IN_DB2,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": PU_ERRATA_ID_IN_DB_1,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": PU_ERRATA_ID_IN_DB_2,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": VULN_IN_DB,
            "branch": BRANCH_IN_DB,
            "state": "fakestate",
            "status_code": 400,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": PU_ERRATA_ID_NOT_IN_DB,
            "status_code": 404,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": PU_ERRATA_ID_NOT_VALID_1,
            "status_code": 404,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": PU_ERRATA_ID_NOT_VALID_2,
            "status_code": 404,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": BU_ERRATA_ID_IN_DB,
            "status_code": 404,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": BU_ERRATA_ID_NOT_IN_DB,
            "status_code": 404,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": TASK_IN_DB,
            "branch": "p10",
            "status_code": 404,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": "32291",
            "branch": BRANCH_IN_DB,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": TASK_IN_DB,
            "branch": BRANCH_NOT_IN_DB,
            "status_code": 400,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": f"{TASK_IN_DB},@rider",
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": f"{TASK_IN_DB},rider",
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": f"{TASK_IN_DB},@rider",
            "branch": "p10",
            "status_code": 404,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": TASK_NOT_IN_DB,
            "status_code": 404,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": OWNER_IN_DB,
            "branch": BRANCH_IN_DB,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": OWNER_IN_DB,
            "branch": BRANCH_NOT_IN_DB,
            "status_code": 400,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": OWNER_NOT_IN_DB,
            "status_code": 404,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": OWNER_NOT_IN_DB,
            "status_code": 404,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": None,
            "limit": 10,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": TASK_IN_DB,
            "status_code": 401,
        },
        {
            "input": TASK_IN_DB,
            "status_code": 401,
            "headers": {"Authorization": INVALID_ACCESS_TOKEN},
        },
    ],
)
def test_task_list(client, kwargs, mocked_check_access_token):
    params = {k: v for k, v in kwargs.items() if k not in ("status_code", "headers")}
    url = url_for("manage.manage_route_task_list")
    mocked_check_access_token.headers = kwargs.get("headers", {})
    mocked_check_access_token.status_code = kwargs["status_code"]
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["length"] != 0
        assert data["tasks"] != []
        for task in data["tasks"]:
            if params.get("branch", ""):
                assert task["branch"] == params["branch"]
            if params.get("state", "") and params["state"] != "all":
                assert task["state"] == params["state"]
            if params["input"] == OWNER_IN_DB:
                assert task["owner"] == OWNER_IN_DB
            if params["input"] == PU_ERRATA_ID_IN_DB_1:
                assert PU_ERRATA_ID_IN_DB_1 in task["erratas"]
            if params["input"] == PU_ERRATA_ID_IN_DB_2:
                assert PU_ERRATA_ID_IN_DB_2 in task["erratas"]
            if params["input"] == VULN_IN_DB:
                assert VULN_IN_DB in [el["id"] for el in task["vulnerabilities"]]
            if params["input"] == VULN_IN_DB2:
                assert VULN_IN_DB2 in [el["id"] for el in task["vulnerabilities"]]
            if params["input"] is not None and params["input"].isdigit():
                assert params["input"] in str(task["task_id"])
        if params.get("limit", ""):
            assert params["limit"] == data["length"]


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "id": TASK_IN_DB,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "id": TASK_IN_DB2,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "id": TASK_IN_DB2,
            "status_code": 401,
            "headers": {"Authorization": INVALID_ACCESS_TOKEN},
        },
        {
            "id": TASK_IN_DB2,
            "status_code": 401,
        },
        {
            "id": TASK_DEL_PACKAGES_IN_DB,
            "status_code": 404,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "id": TASK_NOT_IN_DB,
            "status_code": 404,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "id": DELETED_TASK_IN_DB,
            "status_code": 404,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
    ],
)
def test_task_info(client, kwargs, mocked_check_access_token):
    params = {k: v for k, v in kwargs.items() if k not in ("status_code", "headers")}
    url = url_for("manage.manage_route_task_info", **{"id": kwargs["id"]})
    mocked_check_access_token.headers = kwargs.get("headers", {})
    mocked_check_access_token.status_code = kwargs["status_code"]
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["task_state"] == "DONE"
        assert data["subtasks"] != []
        for sub in data["subtasks"]:
            if sub["errata_id"] != "":
                assert sub["vulnerabilities"] != []
            else:
                assert sub["vulnerabilities"] == []


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "payload": {"vuln_ids": [VULN_IN_DB, VULN_IN_DB2, BUG_IN_DB]},
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "payload": {"vuln_ids": [VULN_IN_DB, VULN_IN_DB3]},
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "payload": {"vuln_ids": [VULN_IN_DB, VULN_IN_DB2]},
            "status_code": 401,
            "headers": {"Authorization": INVALID_ACCESS_TOKEN},
        },
        {
            "payload": {"vuln_ids": [BUG_IN_DB, BUG_NOT_IN_DB]},
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "payload": {"vuln_ids": [VULN_NOT_IN_DB, VULN_NOT_IN_DB2]},
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "payload": {"vuln_ids": [BUG_NOT_IN_DB, VULN_NOT_IN_DB2]},
            "status_code": 404,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "payload": {"vuln_ids": [VULN_NOT_IN_DB3]},
            "status_code": 404,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "payload": {"vuln_ids": []},
            "status_code": 404,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "payload": {"vuln_ids": ["test"]},
            "status_code": 400,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "payload": {"vuln_ids": [VULN_IN_DB, VULN_IN_DB2, BUG_IN_DB]},
            "status_code": 401,
        },
    ],
)
def test_vulns(client, kwargs, mocked_check_access_token):
    url = url_for("manage.manage_route_vulns_info")
    mocked_check_access_token.headers = kwargs.get("headers", {})
    mocked_check_access_token.status_code = kwargs["status_code"]
    response = client.post(url, json=kwargs["payload"], content_type="application/json")
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}

        if BUG_NOT_IN_DB in kwargs["payload"]["vuln_ids"]:
            assert data["not_found"] != []
        if VULN_NOT_IN_DB2 in kwargs["payload"]["vuln_ids"]:
            assert data["not_found"] != []
        if VULN_NOT_IN_DB in kwargs["payload"]["vuln_ids"]:
            assert data["vulns"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "errata_id": PU_ERRATA_ID_IN_DB_1,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "errata_id": PU_ERRATA_ID_IN_DB_1,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "errata_id": BU_ERRATA_ID_IN_DB,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "errata_id": BU_ERRATA_ID_IN_DB,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "errata_id": BU_ERRATA_ID_NOT_IN_DB,
            "status_code": 404,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "errata_id": PU_ERRATA_ID_NOT_IN_DB,
            "status_code": 404,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "errata_id": PU_ERRATA_ID_NOT_VALID_1,
            "status_code": 400,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "errata_id": BU_ERRATA_ID_NOT_IN_DB,
            "status_code": 404,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "errata_id": PU_ERRATA_ID_IN_DB_2,
            "status_code": 401,
            "headers": {"Authorization": INVALID_ACCESS_TOKEN},
        },
        {
            "errata_id": PU_ERRATA_ID_IN_DB_2,
            "status_code": 401,
        },
    ],
)
def test_errata_change_history(client, kwargs, mocked_check_access_token):
    params = {k: v for k, v in kwargs.items() if k not in ("status_code", "headers")}
    url = url_for("manage.manage_route_errata_change_history")
    mocked_check_access_token.headers = kwargs.get("headers", {})
    mocked_check_access_token.status_code = kwargs["status_code"]
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["history"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "status_code": 200,
            "limit": 10,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "is_images": "true",
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "branch": BRANCH_IN_DB,
            "limit": 10,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "severity": "HIGH",
            "limit": 10,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": VULN_IN_DB,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "img": IMG_IN_DB,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": VULN_IN_DB2,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": VULN_IN_DB3,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": PACKAGE_IN_DB,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "img": IMG_IN_DB,
            "branch": "p9",
            "status_code": 404,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": VULN_NOT_IN_DB,
            "status_code": 404,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": VULN_FIXED_IN_DB,
            "branch": "sisyphus",
            "status_code": 404,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": VULN_NOT_IN_DB2,
            "status_code": 404,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": PACKAGE_NOT_IN_DB,
            "status_code": 404,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": BRANCH_NOT_IN_DB,
            "status_code": 404,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "severity": "test",
            "status_code": 400,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "by_acl": "test",
            "status_code": 400,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "status_code": 401,
            "headers": {"Authorization": INVALID_ACCESS_TOKEN},
        },
        {
            "status_code": 401,
        },
    ],
)
def test_packages_open_vulns(client, kwargs, mocked_check_access_token):
    params = {k: v for k, v in kwargs.items() if k not in ("status_code", "headers")}
    url = url_for("manage.manage_route_packages_open_vulns")
    mocked_check_access_token.headers = kwargs.get("headers", {})
    mocked_check_access_token.status_code = kwargs["status_code"]
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["packages"] != []
        for pkg in data["packages"]:
            assert pkg["vulns"] != []
            if params.get("is_images") == "true":
                assert pkg["images"] != []
            if params.get("branch"):
                assert params.get("branch") == pkg["branch"]
            if params.get("input") == PACKAGE_IN_DB:
                assert params.get("input") in pkg["pkg_name"]
            if params.get("input") == VULN_IN_DB:
                assert params.get("input") in [el["id"] for el in pkg["vulns"]]
            if params.get("input") == VULN_IN_DB2:
                assert params.get("input") in [el["id"] for el in pkg["vulns"]]
            if params.get("severity"):
                assert params.get("severity") in [el["severity"] for el in pkg["vulns"]]
            if params.get("img"):
                assert any(
                    [
                        params["img"].lower() == img["file"].lower()
                        for img in pkg["images"]
                    ]
                )

        if params.get("limit", ""):
            assert params["limit"] <= data["length"]


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "status_code": 200,
            "limit": 10,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "branch": BRANCH_IN_DB,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": BRANCH_NOT_IN_DB,
            "status_code": 400,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "status_code": 401,
            "headers": {"Authorization": INVALID_ACCESS_TOKEN},
        },
        {
            "status_code": 401,
        },
    ],
)
def test_packages_maintainer_list(client, kwargs, mocked_check_access_token):
    params = {k: v for k, v in kwargs.items() if k not in ("status_code", "headers")}
    url = url_for("manage.manage_route_packages_maintainer_list")
    mocked_check_access_token.headers = kwargs.get("headers", {})
    mocked_check_access_token.status_code = kwargs["status_code"]
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["maintainers"] != []
        if params.get("limit", ""):
            assert params["limit"] <= data["length"]


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": PACKAGE_IN_DB,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": CPE_IN_DB,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "status_code": 200,
            "limit": 10,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": PACKAGE_NOT_IN_DB,
            "status_code": 404,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": CPE_NOT_IN_DB,
            "status_code": 404,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "status_code": 401,
            "headers": {"Authorization": INVALID_ACCESS_TOKEN},
        },
        {
            "status_code": 401,
        },
    ],
)
def test_cpe_list(client, kwargs, mocked_check_access_token):
    params = {k: v for k, v in kwargs.items() if k not in ("status_code", "headers")}
    url = url_for("manage.manage_route_cpe_list")
    mocked_check_access_token.headers = kwargs.get("headers", {})
    mocked_check_access_token.status_code = kwargs["status_code"]
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["cpes"] != []
        if params.get("limit", ""):
            assert params["limit"] <= data["length"]

        for el in data["cpes"]:
            if params.get("input", "") == PACKAGE_IN_DB:
                for pkg in el["packages"]:
                    assert params["input"] in pkg["name"]
            if params.get("input", "") == CPE_IN_DB:
                assert params["input"] in el["cpe"]


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": PACKAGE_IN_DB,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": PROJECT_NAME_IN_DB,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "status_code": 200,
            "limit": 10,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": PACKAGE_NOT_IN_DB,
            "status_code": 404,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": PROJECT_NAME_NOT_IN_DB,
            "status_code": 404,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "status_code": 401,
            "headers": {"Authorization": INVALID_ACCESS_TOKEN},
        },
        {
            "status_code": 401,
        },
    ],
)
def test_pnc_list(client, kwargs, mocked_check_access_token):
    params = {k: v for k, v in kwargs.items() if k not in ("status_code", "headers")}
    url = url_for("manage.manage_route_pnc_list")
    mocked_check_access_token.headers = kwargs.get("headers", {})
    mocked_check_access_token.status_code = kwargs["status_code"]
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["pncs"] != []
        if params.get("limit", ""):
            assert params["limit"] <= len(data["pncs"])

        for el in data["pncs"]:
            if params.get("input", "") == PACKAGE_IN_DB:
                assert any(
                    [
                        params["input"].lower() in pkg["pkg_name"].lower()
                        for pkg in el["packages"]
                    ]
                )
            if params.get("input", "") == PROJECT_NAME_IN_DB:
                assert params["input"].lower() in el["pnc_result"].lower()
            if params.get("state", "") == "active":
                assert params["state"] == el["pnc_state"]


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "name": PACKAGE_UNMAPPED_IN_DB,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "name": PACKAGE_UNMAPPED_IN_DB2,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "name": PACKAGE_UNMAPPED_NOT_IN_DB,
            "status_code": 404,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "status_code": 401,
            "headers": {"Authorization": INVALID_ACCESS_TOKEN},
        },
        {
            "status_code": 401,
        },
    ],
)
def test_packages_unmapped(client, kwargs, mocked_check_access_token):
    params = {k: v for k, v in kwargs.items() if k not in ("status_code", "headers")}
    url = url_for("manage.manage_route_packages_unmapped")
    mocked_check_access_token.headers = kwargs.get("headers", {})
    mocked_check_access_token.status_code = kwargs["status_code"]
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["packages"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "input": None,
            "limit": 10,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": VULN_IN_DB,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": VULN_IN_DB2,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": VULN_IN_DB3,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": VULN_NOT_IN_DB2,
            "status_code": 404,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": PU_ERRATA_ID_IN_DB_1,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": CPE_IN_DB2,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "severity": "CRITICAL",
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "is_errata": True,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": CPE_NOT_IN_DB,
            "status_code": 404,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "is_errata": True,
            "our": False,
            "status_code": 404,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": BU_ERRATA_ID_IN_DB,
            "status_code": 404,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": BU_ERRATA_ID_NOT_IN_DB,
            "status_code": 404,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": "GHSA-",
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "status_code": 401,
            "headers": {"Authorization": INVALID_ACCESS_TOKEN},
        },
        {
            "status_code": 401,
        },
    ],
)
def test_vuln_list(client, kwargs, mocked_check_access_token):
    params = {k: v for k, v in kwargs.items() if k not in ("status_code", "headers")}
    url = url_for("manage.manage_route_vuln_list")
    mocked_check_access_token.headers = kwargs.get("headers", {})
    mocked_check_access_token.status_code = kwargs["status_code"]
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]

    if response.status_code == 200:
        assert data != {}
        assert data["vulns"] != []
        if params.get("limit", ""):
            assert params["limit"] <= len(data["vulns"])

        for el in data["vulns"]:
            if params.get("input", "") == VULN_IN_DB:
                assert params["input"] == el["id"]
            if params.get("input", "") == PU_ERRATA_ID_IN_DB_1:
                assert any(
                    [
                        params["input"].lower() == errata["id"].lower()
                        for errata in el["erratas"]
                    ]
                )
            if params.get("severity", ""):
                assert params["severity"] == el["severity"]
            if params.get("is_errata", False):
                assert el["erratas"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "limit": 10,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": CH_PU_ERRATA_ID_IN_DB_1,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": CH_BU_ERRATA_ID_IN_DB_1,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "user": CH_USER_IN_DB,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "module": CH_MODULE_IN_DB_1,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "module": CH_MODULE_IN_DB_2,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "change_type": CH_CHANGE_TYPE_IN_DB_1,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "change_type": CH_CHANGE_TYPE_IN_DB_2,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "change_type": CH_CHANGE_TYPE_IN_DB_3,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "event_start_date": "2024-09-09",
            "event_end_date": "2024-09-10",
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": PU_ERRATA_ID_NOT_IN_DB,
            "status_code": 404,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": BU_ERRATA_ID_NOT_IN_DB,
            "status_code": 404,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "user": CH_USER_NOT_IN_DB,
            "status_code": 404,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "module": CH_MODULE_NOT_IN_DB,
            "status_code": 400,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "change_type": CH_CHANGE_TYPE_NOT_IN_DB,
            "status_code": 400,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "status_code": 401,
            "headers": {"Authorization": INVALID_ACCESS_TOKEN},
        },
        {
            "status_code": 401,
        },
    ],
)
def test_change_history(client, kwargs, mocked_check_access_token):
    params = {k: v for k, v in kwargs.items() if k not in ("status_code", "headers")}
    url = url_for("manage.manage_route_change_history")
    mocked_check_access_token.headers = kwargs.get("headers", {})
    mocked_check_access_token.status_code = kwargs["status_code"]
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["change_history"] != []
        if params.get("limit", ""):
            assert params["limit"] <= len(data["change_history"])
        for el in data["change_history"]:
            if params.get("input", "") == CH_PU_ERRATA_ID_IN_DB_1:
                assert any(
                    [
                        params["input"].lower() == change["errata_id"].lower()
                        for change in el["changes"]
                    ]
                )
            if params.get("user", ""):
                assert params["user"] == el["author"]
            if params.get("module", ""):
                assert params["module"] in [
                    change["module"] for change in el["changes"]
                ]
            if params.get("change_type", ""):
                assert params["change_type"] in [
                    change["change_type"] for change in el["changes"]
                ]
            if params.get("event_start_date", ""):
                assert params["event_start_date"] <= el["event_date"]
            if params.get("event_end_date", ""):
                assert params["event_end_date"] >= el["event_date"]


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "entity_link": VULN_IN_DB,
            "entity_type": "vuln",
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
            "status_code": 200,
        },
        {
            "entity_link": VULN_NOT_IN_DB,
            "entity_type": "vuln",
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
            "status_code": 404,
        },
        {
            "entity_link": VULN_IN_DB,
            "entity_type": "qwe",
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
            "status_code": 400,
        },
        {
            "entity_link": VULN_IN_DB,
            "entity_type": "vuln",
            "headers": {"Authorization": INVALID_ACCESS_TOKEN},
            "status_code": 401,
        },
    ],
)
def test_comments_list(client, kwargs, mocked_check_access_token):
    params = {k: v for k, v in kwargs.items() if k not in ("status_code", "headers")}
    url = url_for("manage.manage_route_list_comments")
    mocked_check_access_token.headers = kwargs.get("headers", {})
    mocked_check_access_token.status_code = kwargs["status_code"]
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "text": DEFAULT_REASON_IN_DB,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
            "status_code": 200,
        },
        {
            "text": DEFAULT_REASON_NOT_IN_DB,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
            "status_code": 404,
        },
        {
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
            "status_code": 200,
        },
        {
            "source": "qwe",
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
            "status_code": 400,
        },
        {
            "text": DEFAULT_REASON_IN_DB,
            "source": "exclusion",
            "is_active": "true",
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
            "status_code": 200,
        },
        {
            "text": DEFAULT_REASON_IN_DB,
            "headers": {"Authorization": INVALID_ACCESS_TOKEN},
            "status_code": 401,
        },
        {
            "text": DEFAULT_REASON_IN_DB,
            "headers": {},
            "status_code": 401,
        },
    ],
)
def test_default_reasons_list(client, kwargs, mocked_check_access_token):
    """Test default reasons list endpoint with various parameters."""

    mocked_check_access_token.headers = kwargs.get("headers", {})
    mocked_check_access_token.status_code = kwargs["status_code"]

    params = {k: v for k, v in kwargs.items() if k not in ("status_code", "headers")}

    url = url_for("manage.manage_route_list_default_reasons")

    response = client.get(url, query_string=params, headers=kwargs.get("headers", {}))

    assert response.status_code == kwargs["status_code"]

    if response.status_code == 200:
        data = response.json
        assert "reasons" in data
        assert "length" in data
        assert "request_args" in data
        assert isinstance(data["reasons"], list)
        assert isinstance(data["length"], int)
        assert isinstance(data["request_args"], dict)
