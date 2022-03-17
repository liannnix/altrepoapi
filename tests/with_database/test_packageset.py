import pytest
from flask import url_for

BRANCH_IN_DB = "sisyphus"
BRANCH_IN_DB2 = "p10"
BRANCH_NOT_IN_DB = "fakebranch"
BRANCHES_IN_DB = ("sisyphus", "p9", "p10")
ARCHS_IN_DB = "noarch,x86_64,i586"
ARCHS_NOT_IN_DB = "x86_64,fakearch2"
PACKAGES_IN_DB = ("curl", "mc", "python3")


def test_active_packagesets(client):
    url = url_for("api.packageset_route_active_packagesets")
    response = client.get(url)
    data = response.json
    assert response.status_code == 200
    assert data != {}
    assert data["length"] != 0
    assert data["packagesets"] != []
    for branch in BRANCHES_IN_DB:
        assert branch in data["packagesets"]


def test_pkgset_status_get(client):
    url = url_for("api.packageset_route_repository_status")
    response = client.get(url)
    data = response.json
    assert response.status_code == 200
    assert data != {}
    assert data["branches"] != []
    branches = [b["branch"] for b in data["branches"]]
    for branch in BRANCHES_IN_DB:
        assert branch in branches


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "branches": [
                {
                    "pkgset_name": "string",
                    "rs_pkgset_name_bugzilla": "string",
                    "rs_start_date": "2022-03-15T12:53:09",
                    "rs_end_date": "2022-03-15T12:53:09",
                    "rs_show": 0,
                    "rs_description_ru": "string",
                    "rs_description_en": "string",
                    "rs_mailing_list": "string",
                    "rs_mirrors_json": [
                        {}
                    ]
                }
            ]
        }
    ],
)
def test_pkgset_status_post(client, kwargs):
    url = url_for("api.packageset_route_repository_status")
    response = client.post(url, json=kwargs)
    assert response.status_code == 401


@pytest.mark.parametrize(
    "kwargs",
    [
        {"branch": BRANCH_IN_DB, "package_type": "source", "archs": None, "status_code": 200},
        {"branch": BRANCH_IN_DB, "package_type": "binary", "archs": ARCHS_IN_DB, "status_code": 200},
        {"branch": BRANCH_IN_DB, "package_type": "faketype", "archs": None, "status_code": 400},
        {"branch": BRANCH_IN_DB, "package_type": "binary", "archs": ARCHS_NOT_IN_DB, "status_code": 400},
        {"branch": BRANCH_NOT_IN_DB, "package_type": None, "archs": None, "status_code": 400},
    ],
)
def test_repository_packages(client, kwargs):
    url = url_for("api.packageset_route_packageset_packages")
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
        pkg_names = [p["name"] for p in data["packages"]]
        assert data != {}
        assert data["length"] != 0
        assert data["packages"] != []
        for pkg in PACKAGES_IN_DB:
            assert pkg in pkg_names


@pytest.mark.parametrize(
    "kwargs",
    [
        {"pkgset1": BRANCH_IN_DB, "pkgset2": BRANCH_IN_DB, "status_code": 404},
        {"pkgset1": BRANCH_IN_DB, "pkgset2": BRANCH_IN_DB2, "status_code": 200},
        {"pkgset1": BRANCH_IN_DB, "pkgset2": BRANCH_NOT_IN_DB, "status_code": 400},
        {"pkgset1": BRANCH_NOT_IN_DB, "pkgset2": BRANCH_IN_DB, "status_code": 400},
    ],
)
def test_compare_packagesets(client, kwargs):
    url = url_for("api.packageset_route_packageset_compare")
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
        assert data["length"] != 0
        assert data["packages"] != []
        pkg_match = []
        for el in data["packages"]:
            assert el["pkgset1"] == kwargs["pkgset1"]
            assert el["pkgset2"] == kwargs["pkgset2"]
            pkg_match.append(
                el["package1"]["name"] == el["package2"]["name"]
            )
        assert pkg_match.count(True) > 0
        assert pkg_match.count(False) > 0
