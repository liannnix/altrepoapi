import pytest
from flask import url_for


BRANCH_IN_DB = "sisyphus"
BRANCH_NOT_IN_DB = "fakebranch"
TASK_ID_WITH_BRANCH_COMMITS_IN_DB = 102418
TASK_ID_WITHOUT_BRANCH_COMMITS_IN_DB = 102404
TASK_ID_NOT_IN_DB = 0


def test_all_pkgsets(client):
    url = url_for("api.site_route_all_packagesets")
    response = client.get(url)
    data = response.json
    assert response.status_code == 200
    assert data != {}
    assert data["branches"] != []
    for branch in data["branches"]:
        assert branch["branch"] != ""
        assert branch["count"] == 0


def test_all_pkgsets_with_src_count(client):
    url = url_for("api.site_route_all_packagesets_source_count")
    response = client.get(url)
    data = response.json
    assert response.status_code == 200
    assert data != {}
    assert data["branches"] != []
    for branch in data["branches"]:
        assert branch["branch"] != ""
        assert branch["count"] > 0


def test_all_pkgsets_summary(client):
    url = url_for("api.site_route_all_packagesets_summary")
    response = client.get(url)
    data = response.json
    assert response.status_code == 200
    assert data != {}
    assert data["branches"] != []
    for branch in data["branches"]:
        assert branch["branch"] != ""
        for cnt in branch["packages_count"]:
            assert cnt["arch"] != ""
            assert cnt["count"] > 0


def test_pkgsets_summary_status(client):
    url = url_for("api.site_route_packagesets_summary_status")
    response = client.get(url)
    data = response.json
    assert response.status_code == 200
    assert data != {}
    assert data["branches"] != []
    for branch in data["branches"]:
        assert branch["branch"] != ""
        for cnt in branch["packages_count"]:
            assert cnt["arch"] != ""
            assert cnt["count"] > 0
    assert data["status"] != []
    for st in data["status"]:
        assert st["branch"] != ""
        assert st["start_date"] != ""
        assert st["end_date"] != ""
        assert st["show"] in (0, 1)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"branch": BRANCH_IN_DB, "status_code": 200},
        {"branch": BRANCH_NOT_IN_DB, "status_code": 400},
    ],
)
def test_all_pkgset_archs(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("status_code",):
            continue
        if v is not None:
            params[k] = v
    url = url_for("api.site_route_all_packageset_archs")
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["length"] != 0
        assert data["archs"] != []
        for arch in data["archs"]:
            assert arch["arch"] != ""
            assert arch["count"] == 0


@pytest.mark.parametrize(
    "kwargs",
    [
        {"branch": BRANCH_IN_DB, "status_code": 200},
        {"branch": BRANCH_NOT_IN_DB, "status_code": 400},
    ],
)
def test_all_pkgset_archs_with_src_count(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("status_code",):
            continue
        if v is not None:
            params[k] = v
    url = url_for("api.site_route_all_packageset_archs_source_count")
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["length"] != 0
        assert data["archs"] != []
        for arch in data["archs"]:
            assert arch["arch"] != ""
            assert arch["count"] > 0


@pytest.mark.parametrize(
    "kwargs",
    [
        {"branch": BRANCH_IN_DB, "package_type": None, "status_code": 200},
        {"branch": BRANCH_IN_DB, "package_type": "binary", "status_code": 200},
        {"branch": BRANCH_NOT_IN_DB, "package_type": None, "status_code": 400},
        {"branch": BRANCH_IN_DB, "package_type": "abc", "status_code": 400},
    ],
)
def test_pkgset_categories_count(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("status_code",):
            continue
        if v is not None:
            params[k] = v
    url = url_for("api.site_route_pkgset_categories_count")
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["length"] != 0
        assert data["categories"] != []
        for cat in data["categories"]:
            assert cat["category"] != ""
            assert cat["count"] > 0


@pytest.mark.parametrize(
    "kwargs",
    [
        {"task_id": None, "status_code": 200},
        {"task_id": TASK_ID_WITH_BRANCH_COMMITS_IN_DB, "status_code": 200},
        {"task_id": TASK_ID_WITHOUT_BRANCH_COMMITS_IN_DB, "status_code": 200},
        {"task_id": TASK_ID_NOT_IN_DB, "status_code": 400},
    ],
)
def test_tasks_history(client, kwargs):
    params = {k: v for k, v in kwargs.items() if k != "status_code"}
    url = url_for("api.site_route_tasks_history")
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["active_branches"] != []
        assert data["tasks"] != []
        assert BRANCH_IN_DB in data["active_branches"]
        assert BRANCH_NOT_IN_DB not in data["active_branches"]
        if params.get("task_id", ""):
            assert data["tasks"][0]["id"] == params["task_id"]
        if params.get("task_id", "") == TASK_ID_WITH_BRANCH_COMMITS_IN_DB:
            assert data["branch_commits"] != []
        if params.get("task_id", "") == TASK_ID_WITHOUT_BRANCH_COMMITS_IN_DB:
            assert data["branch_commits"] == []
