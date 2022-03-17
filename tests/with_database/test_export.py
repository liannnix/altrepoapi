import pytest
from flask import url_for


BRANCH_IN_DB = "sisyphus"
BRANCH_NOT_IN_DB = "fakebranch"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"branch": BRANCH_IN_DB, "status_code": 200},
        {"branch": BRANCH_NOT_IN_DB, "status_code": 400},
    ],
)
def test_repology(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("branch", "status_code"):
            continue
        if v is not None:
            params[k] = v
    url = url_for("api.export_route_package_info", **{"branch": kwargs["branch"]})
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        # assert data["length"] != 0
        assert data["date"] != ""
        assert data["branch"] == kwargs["branch"]
        assert data["packages"] != []
        for el in data["stats"]:
            assert el["count"] != 0


@pytest.mark.parametrize(
    "kwargs",
    [
        {"branch": BRANCH_IN_DB, "status_code": 200},
        {"branch": BRANCH_NOT_IN_DB, "status_code": 400},
    ],
)
def test_sitemap(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("branch", "status_code"):
            continue
        if v is not None:
            params[k] = v
    url = url_for("api.export_route_sitemap_packages", **{"branch": kwargs["branch"]})
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["branch"] == kwargs["branch"]
        assert data["packages"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"branch": BRANCH_IN_DB, "arch": None, "status_code": 200},
        {"branch": BRANCH_IN_DB, "arch": "x86_64", "status_code": 200},
        {"branch": BRANCH_NOT_IN_DB, "arch": None, "status_code": 400},
        {"branch": BRANCH_IN_DB, "arch": "fakearch", "status_code": 400},
    ],
)
def test_branch_binary_packages(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("branch", "status_code"):
            continue
        if v is not None:
            params[k] = v
    url = url_for(
        "api.export_route_package_set_binaries", **{"branch": kwargs["branch"]}
    )
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["length"] != 0
        assert data["packages"] != []
