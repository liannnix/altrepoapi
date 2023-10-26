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
PACKAGE_IN_DB = "curl"
PACKAGE_NOT_IN_DB = "fakepackagename"

VULN_IN_DB = "CVE-2019-17069"
VULN_IN_DB2 = "BDU:2021-04545"
VULN_NOT_IN_DB = "CVE-1111-11111"
VULN_NOT_IN_DB2 = "BDU:1111-11111"

BUG_IN_DB = "36250"
BUG_NOT_IN_DB = "11111111"

PU_ERRATA_ID_IN_DB_1 = "ALT-PU-2023-2000-1"
PU_ERRATA_ID_IN_DB_2 = "ALT-PU-2013-1000-1"
PU_ERRATA_ID_NOT_IN_DB = "ALT-PU-2999-1000-1"
PU_ERRATA_ID_NOT_VALID_1 = "ALT-PU-123-1000-1"
PU_ERRATA_ID_NOT_VALID_2 = "ALT-XX-2000-9999-9"

BU_ERRATA_ID_IN_DB = "ALT-BU-2013-1338-1"
BU_ERRATA_ID_NOT_IN_DB = "ALT-BU-2999-1000-1"

VALID_ACCESS_TOKEN = "valid_token"
INVALID_ACCESS_TOKEN = "invalid_token"


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
            "input": f"bug:47017",
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
            "input": f"{TASK_IN_DB},@rider,p10",
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
    url = url_for("manage._route_task_list")
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
    url = url_for("manage._route_task_info", **{"id": kwargs["id"]})
    mocked_check_access_token.headers = kwargs.get("headers", {})
    mocked_check_access_token.status_code = kwargs["status_code"]
    response = client.get(url, query_string=params)
    data = response.json
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
            "payload": {"vuln_ids": [VULN_IN_DB, VULN_IN_DB2]},
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
    url = url_for("manage._route_vulns_info")
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
    url = url_for("manage._route_errata_change_history")
    mocked_check_access_token.headers = kwargs.get("headers", {})
    mocked_check_access_token.status_code = kwargs["status_code"]
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["history"] != []
