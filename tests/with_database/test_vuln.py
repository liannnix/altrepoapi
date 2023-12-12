import pytest
from flask import url_for

BRANCH_IN_DB = "sisyphus"
BRANCH_IN_DB2 = "p10"
BRANCH_NOT_IN_DB = "fakebranch"

TASK_IN_DB = "310692"
DELETED_TASK_IN_DB = "307229"
TASK_NOT_IN_DB = "123456789"
TASK_NOT_FIX_CVE = "322690"
TASK_FIX_CVE = "234665"

MAINTAINER_IN_DB = "rider"
MAINTAINER_NOT_IN_DB = "fakemaintainer"

BAD_CVE_ID = "CVE-1234-123"
CVE_IN_DB = "CVE-2023-0466"
CVE_NOT_IN_DB = "CVE-2000-99999"
LIST_CVE_IN_DB = ["CVE-2023-0466", "CVE-2023-0467", "CVE-2023-0468"]

BAD_BDU_ID = "BDU:1234-123"
BDU_IN_DB = "BDU:2019-01845"
LIST_BDU_IN_DB = ["BDU:2023-01241", "BDU:2023-01242", "BDU:2023-01243"]
BDU_NOT_IN_DB = "BDU:2000-00001"

PAKCAGE_IN_DB = "python3"
PAKCAGE_NOT_IN_DB = "fakepackage"
BAD_PACKAGE_NAME = "xxx*yyy"


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
        {"vuln_id": BDU_IN_DB, "branch": BRANCH_IN_DB, "status_code": 200},
        {"vuln_id": ",".join(LIST_BDU_IN_DB), "branch": BRANCH_IN_DB2, "status_code": 200},
        {"vuln_id": BDU_IN_DB, "branch": BRANCH_NOT_IN_DB, "status_code": 400},
        {"vuln_id": BDU_NOT_IN_DB, "branch": BRANCH_IN_DB, "status_code": 404},
        {"vuln_id": BDU_NOT_IN_DB, "branch": BRANCH_IN_DB, "status_code": 404},
        {"vuln_id": BAD_BDU_ID, "branch": BRANCH_IN_DB, "status_code": 400},
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
        assert set(e for e in kwargs["vuln_id"].split(",")) & set(
            e["id"] for e in data["vuln_info"]
        )
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
        {"vuln_id": CVE_IN_DB, "branch": BRANCH_IN_DB, "status_code": 200},
        {"vuln_id": ",".join(LIST_CVE_IN_DB), "branch": BRANCH_IN_DB2, "status_code": 200},
        {"vuln_id": CVE_IN_DB, "branch": BRANCH_NOT_IN_DB, "status_code": 400},
        {"vuln_id": CVE_NOT_IN_DB, "branch": BRANCH_IN_DB, "status_code": 404},
        {"vuln_id": BAD_CVE_ID, "branch": BRANCH_IN_DB, "status_code": 400},
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
        assert tuple(e["id"] for e in data["vuln_info"]) == tuple(
            e for e in kwargs["vuln_id"].split(",")
        )
        assert data["packages"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"name": PAKCAGE_IN_DB, "status_code": 400},
        {"name": PAKCAGE_IN_DB, "branch": BRANCH_IN_DB2, "status_code": 200},
        {"name": BAD_PACKAGE_NAME, "branch": BRANCH_IN_DB, "status_code": 400},
        {"name": PAKCAGE_IN_DB, "branch": BRANCH_NOT_IN_DB, "status_code": 400},
        {"name": PAKCAGE_NOT_IN_DB, "branch": BRANCH_IN_DB, "status_code": 404},
    ],
)
def test_vuln_packages(client, kwargs):
    url = url_for("api.vuln_route_package_vulnerabilities")
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
        assert data["vuln_info"] != []
        assert data["packages"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        # TODO: disabled due to each positive test takes more than 100 seconds
        # {"branch": BRANCH_IN_DB, "status_code": 200},
        # {"branch": BRANCH_IN_DB2, "status_code": 200},
        {"branch": BRANCH_NOT_IN_DB, "status_code": 400},
    ],
)
def test_vuln_branch(client, kwargs):
    url = url_for("api.vuln_route_branch_open_vulnerabilities")
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
        assert data["vuln_info"] != []
        assert data["packages"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "branch": BRANCH_IN_DB,
            "maintainer_nickname": MAINTAINER_IN_DB,
            "by_acl": None,
            "status_code": 200,
        },
        {
            "branch": BRANCH_IN_DB2,
            "maintainer_nickname": MAINTAINER_IN_DB,
            "by_acl": "none",
            "status_code": 200,
        },
        {
            "branch": BRANCH_IN_DB,
            "maintainer_nickname": MAINTAINER_IN_DB,
            "by_acl": "by_nick",
            "status_code": 200,
        },
        {
            "branch": BRANCH_IN_DB2,
            "maintainer_nickname": MAINTAINER_IN_DB,
            "by_acl": "by_nick_leader",
            "status_code": 200,
        },
        {
            "branch": BRANCH_IN_DB,
            "maintainer_nickname": MAINTAINER_IN_DB,
            "by_acl": "by_nick_or_group",
            "status_code": 200,
        },
        {
            "branch": BRANCH_IN_DB2,
            "maintainer_nickname": MAINTAINER_IN_DB,
            "by_acl": "by_nick_leader_and_group",
            "status_code": 200,
        },
        {
            "branch": BRANCH_NOT_IN_DB,
            "maintainer_nickname": MAINTAINER_IN_DB,
            "by_acl": None,
            "status_code": 400,
        },
        {
            "branch": BRANCH_IN_DB,
            "maintainer_nickname": MAINTAINER_IN_DB,
            "by_acl": "abc",
            "status_code": 400,
        },
        {
            "branch": BRANCH_IN_DB,
            "maintainer_nickname": MAINTAINER_NOT_IN_DB,
            "by_acl": None,
            "status_code": 404,
        },
    ],
)
def test_vuln_maintainer(client, kwargs):
    url = url_for("api.vuln_route_maintainer_open_vulnerabilities")
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
        assert data["vuln_info"] != []
        assert data["packages"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"id": TASK_FIX_CVE, "status_code": 200},
        {"id": TASK_IN_DB, "status_code": 404},
        {"id": TASK_NOT_FIX_CVE, "status_code": 404},
        {"id": DELETED_TASK_IN_DB, "status_code": 404},
        {"id": TASK_NOT_IN_DB, "status_code": 404},
    ],
)
def test_vuln_task(client, kwargs):
    url = url_for("api.vuln_route_task_vulnerabilities", **{"id": kwargs["id"]})
    response = client.get(url)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        if kwargs["id"] == TASK_NOT_FIX_CVE:
            assert data["packages"] == []
        elif kwargs["id"] == TASK_FIX_CVE:
            assert data["packages"] != []
            for pkg in data["packages"]:
                assert pkg["vulnerabilities"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"vuln_id": CVE_IN_DB, "status_code": 200},
        {"vuln_id": CVE_NOT_IN_DB, "status_code": 404},
        {"vuln_id": BAD_CVE_ID, "status_code": 400},
    ],
)
def test_vuln_cve_fixes(client, kwargs):
    url = url_for("api.vuln_route_vulnerable_cve_fixes")
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
        assert data["packages"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"vuln_id": BDU_IN_DB, "status_code": 200},
        {"vuln_id": BDU_NOT_IN_DB, "status_code": 404},
        {"vuln_id": BAD_BDU_ID, "status_code": 400},
    ],
)
def test_vuln_bdu_fixes(client, kwargs):
    url = url_for("api.vuln_route_vulnerable_bdu_fixes")
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
        assert data["packages"] != []
