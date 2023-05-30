import pytest
from flask import url_for

BRANCH_IN_DB = "sisyphus"
BRANCH_IN_DB2 = "p10"
BRANCH_NOT_IN_DB = "fakebranch"

BAD_CVE_ID = "CVE-1234-123"
CVE_IN_DB = "CVE-2023-0466"
CVE_NOT_IN_DB = "CVE-2000-99999"
LIST_CVES_IN_DB = ["CVE-2023-0466", "CVE-2023-0467", "CVE-2023-0468"]

BAD_BDU_ID = "BDU:1234-123"
BDU_IN_DB = "BDU:2019-01845"
BDU_NOT_IN_DB = "BDU:2000-00001"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"vuln_id": BDU_IN_DB, "status_code": 200},
        {"vuln_id": BDU_NOT_IN_DB, "status_code": 404},
        {"vuln_id": BAD_BDU_ID, "status_code": 400},
    ],
)
def test_vuln_bdu_info(client, kwargs):
    url = url_for("api.vuln_route_bdu_info")
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
        assert data["vuln_info"]["id"] == kwargs["vuln_id"]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"vuln_id": BDU_IN_DB, "status_code": 200},
        {"vuln_id": BDU_IN_DB, "branch": BRANCH_IN_DB, "status_code": 200},
        {"vuln_id": BDU_IN_DB, "branch": BRANCH_IN_DB2, "status_code": 200},
        {"vuln_id": BDU_IN_DB, "branch": BRANCH_NOT_IN_DB, "status_code": 400},
        {"vuln_id": BDU_NOT_IN_DB, "status_code": 404},
        {"vuln_id": BDU_NOT_IN_DB, "branch": BRANCH_IN_DB, "status_code": 404},
        {"vuln_id": BAD_BDU_ID, "status_code": 400},
    ],
)
def test_vuln_bdu_packages(client, kwargs):
    url = url_for("api.vuln_route_vulnerable_package_by_bdu")
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
        assert data["vuln_info"][0]["id"] == kwargs["vuln_id"]
        assert data["packages"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"vuln_id": CVE_IN_DB, "status_code": 200},
        {"vuln_id": CVE_NOT_IN_DB, "status_code": 404},
        {"vuln_id": BAD_CVE_ID, "status_code": 400},
    ],
)
def test_vuln_cve_info(client, kwargs):
    url = url_for("api.vuln_route_cve_info")
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
        assert data["vuln_info"]["id"] == kwargs["vuln_id"]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"vuln_id": CVE_IN_DB, "status_code": 200},
        {"vuln_id": ",".join(LIST_CVES_IN_DB), "status_code": 200},
        {"vuln_id": CVE_IN_DB, "branch": BRANCH_IN_DB, "status_code": 200},
        {"vuln_id": CVE_IN_DB, "branch": BRANCH_IN_DB2, "status_code": 200},
        {"vuln_id": CVE_IN_DB, "branch": BRANCH_NOT_IN_DB, "status_code": 400},
        {"vuln_id": CVE_NOT_IN_DB, "status_code": 404},
        {"vuln_id": CVE_NOT_IN_DB, "branch": BRANCH_IN_DB, "status_code": 404},
        {"vuln_id": BAD_CVE_ID, "status_code": 400},
    ],
)
def test_vuln_cve_packages(client, kwargs):
    url = url_for("api.vuln_route_vulnerable_package_by_cve")
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
        assert data["vuln_info"][0]["id"] == kwargs["vuln_id"].split(",")[0]
        assert data["packages"] != []
