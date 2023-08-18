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

PU_ERRATA_ID_IN_DB_1 = "ALT-PU-2023-2000-1"
PU_ERRATA_ID_IN_DB_2 = "ALT-PU-2013-1000-1"
PU_ERRATA_ID_NOT_IN_DB = "ALT-PU-2999-1000-1"
PU_ERRATA_ID_NOT_VALID_1 = "ALT-PU-123-1000-1"
PU_ERRATA_ID_NOT_VALID_2 = "ALT-XX-2000-9999-9"

BU_ERRATA_ID_IN_DB = "ALT-BU-2023-3800-1"
BU_ERRATA_ID_NOT_IN_DB = "ALT-BU-2999-1000-1"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"input": TASK_IN_DB, "branch": BRANCH_IN_DB, "status_code": 200},
        {"input": TASK_IN_DB, "status_code": 200},
        {"input": TASK_IN_DB2, "status_code": 200},
        {"input": f"#{TASK_IN_DB}", "status_code": 200},
        {"input": f"bug:47017", "status_code": 200},
        {"input": VULN_IN_DB, "status_code": 200},
        {"input": VULN_IN_DB2, "status_code": 200},
        {"input": PU_ERRATA_ID_IN_DB_1, "status_code": 200},
        {"input": PU_ERRATA_ID_IN_DB_2, "status_code": 200},
        {"input": PU_ERRATA_ID_NOT_IN_DB, "status_code": 404},
        {"input": PU_ERRATA_ID_NOT_VALID_1, "status_code": 404},
        {"input": PU_ERRATA_ID_NOT_VALID_2, "status_code": 404},
        {"input": BU_ERRATA_ID_IN_DB, "status_code": 404},
        {"input": BU_ERRATA_ID_NOT_IN_DB, "status_code": 404},
        {"input": TASK_IN_DB, "branch": "p10", "status_code": 404},
        {"input": "32291", "branch": BRANCH_IN_DB, "status_code": 200},
        {"input": TASK_IN_DB, "branch": BRANCH_NOT_IN_DB, "status_code": 400},
        {"input": f"{TASK_IN_DB},@rider", "status_code": 200},
        {"input": f"{TASK_IN_DB},rider", "status_code": 200},
        {"input": f"{TASK_IN_DB},@rider,p10", "status_code": 404},
        {"input": TASK_NOT_IN_DB, "status_code": 404},
        {"input": OWNER_IN_DB, "branch": BRANCH_IN_DB, "status_code": 200},
        {"input": OWNER_IN_DB, "branch": BRANCH_NOT_IN_DB, "status_code": 400},
        {"input": OWNER_NOT_IN_DB, "status_code": 404},
        {"input": OWNER_NOT_IN_DB, "status_code": 404},
        {"input": None, "limit": 10, "status_code": 200},
    ],
)
def test_task_list(client, kwargs):
    params = {k: v for k, v in kwargs.items() if k not in ("status_code",)}
    url = url_for("api.management_route_task_list")
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
        {"id": TASK_IN_DB, "status_code": 200},
        {"id": TASK_IN_DB2, "status_code": 200},
        {"id": TASK_DEL_PACKAGES_IN_DB, "status_code": 404},
        {"id": TASK_NOT_IN_DB, "status_code": 404},
        {"id": DELETED_TASK_IN_DB, "status_code": 404},
    ]
)
def test_task_info(client, kwargs):
    params = {k: v for k, v in kwargs.items() if k not in ("status_code",)}
    url = url_for("api.management_route_task_info", **{"id": kwargs["id"]})
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
