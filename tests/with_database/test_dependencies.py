import pytest
from flask import url_for

BRANCH_IN_DB = "sisyphus"
BRANCH_NOT_IN_DB = "fakebranch"
BIN_PKG_HASH_IN_DB = 2737734146634739740  # curl-7.80.0-alt1.x86_64.rpm
SRC_PKG_HASH_IN_DB = 2737731585263144792  # curl-7.80.0-alt1.src.rpm
PKG_HASH_NOT_IN_DB = 1234567890
DP_NAME_IN_DB = "curl"
DP_NAME_NOT_IN_DB = "fakepackage"
SRC_PKG_NAME = "curl"
BIN_PKG_NAME = "libcurl"


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "branch": BRANCH_IN_DB,
            "dp_name": DP_NAME_IN_DB,
            "dp_type": None,
            "status_code": 200,
        },
        {
            "branch": BRANCH_IN_DB,
            "dp_name": DP_NAME_IN_DB,
            "dp_type": "all",
            "status_code": 200,
        },
        {
            "branch": BRANCH_IN_DB,
            "dp_name": DP_NAME_IN_DB,
            "dp_type": "provide",
            "status_code": 200,
        },
        {
            "branch": BRANCH_IN_DB,
            "dp_name": DP_NAME_NOT_IN_DB,
            "dp_type": None,
            "status_code": 404,
        },
        {
            "branch": BRANCH_NOT_IN_DB,
            "dp_name": DP_NAME_IN_DB,
            "dp_type": None,
            "status_code": 400,
        },
        {"branch": None, "dp_name": DP_NAME_IN_DB, "dp_type": None, "status_code": 400},
        {"branch": BRANCH_IN_DB, "dp_name": None, "dp_type": None, "status_code": 400},
        {
            "branch": BRANCH_IN_DB,
            "dp_name": DP_NAME_IN_DB,
            "dp_type": "abc",
            "status_code": 400,
        },
    ],
)
def test_packages_by_dependency(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("pkghash", "status_code"):
            continue
        if v is not None:
            params[k] = v
    url = url_for("api.dependencies_route_package_depends")
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["length"] != 0
        assert data["request_args"]["branch"] == kwargs["branch"]
        assert data["packages"] != []
        assert data["branches"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"pkghash": BIN_PKG_HASH_IN_DB, "status_code": 200},
        {"pkghash": PKG_HASH_NOT_IN_DB, "status_code": 404},
    ],
)
def test_binary_package_dependencies(client, kwargs):
    url = url_for(
        "api.dependencies_route_depends_bin_package", **{"pkghash": kwargs["pkghash"]}
    )
    params = {}
    for k, v in kwargs.items():
        if k in ("pkghash", "status_code"):
            continue
        if v is not None:
            params[k] = v
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["length"] != 0
        assert data["dependencies"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"branch": BRANCH_IN_DB, "pkghash": SRC_PKG_HASH_IN_DB, "status_code": 200},
        {"branch": BRANCH_NOT_IN_DB, "pkghash": SRC_PKG_HASH_IN_DB, "status_code": 400},
        {"branch": BRANCH_IN_DB, "pkghash": PKG_HASH_NOT_IN_DB, "status_code": 404},
    ],
)
def test_source_package_dependencies(client, kwargs):
    url = url_for(
        "api.dependencies_route_depends_src_package", **{"pkghash": kwargs["pkghash"]}
    )
    params = {}
    for k, v in kwargs.items():
        if k in ("pkghash", "status_code"):
            continue
        if v is not None:
            params[k] = v
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["length"] != 0
        assert data["package_info"] != {}
        assert data["dependencies"] != []
        assert data["provided_by_src"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "from_branch": "sisyphus",
            "into_branch": "p11",
            "packages_names": ["curl"],
            "dp_type": "both",
            "archs": ["x86_64"],
            "status_code": 200,
        },
        {
            "from_branch": "p10",
            "into_branch": "c9f2",
            "packages_names": ["python3"],
            "dp_type": "binary",
            "archs": ["x86_64"],
            "status_code": 200,
        },
        {
            "from_branch": "p10",
            "into_branch": "c9f2",
            "packages_names": ["python3"],
            "dp_type": "binary",
            "archs": [],
            "status_code": 200,
        },
        {
            "from_branch": "p10",
            "into_branch": "c9f2",
            "packages_names": ["this-package-doesn't-exist"],
            "dp_type": "binary",
            "archs": ["x86_64"],
            "status_code": 400,
        },
        {
            "from_branch": "p10",
            "into_branch": "p7",
            "packages_names": ["curl"],
            "dp_type": "source",
            "archs": ["x86_64"],
            "status_code": 400,
        },
        {
            "from_branch": "p10",
            "into_branch": "sisyphus",
            "packages_names": ["python3"],
            "dp_type": "binary",
            "archs": ["x86_64"],
            "status_code": 400,
        },
    ],
)
def test_backport_helper(client, kwargs):
    url = url_for("api.dependencies_route_backport_helper")
    params = {}
    for keyword, value in kwargs.items():
        if keyword != "status_code":
            params[keyword] = value

    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["count"] >= 0
        assert data["maxdepth"] >= 0

        if data["dependencies"]:
            for level in data["dependencies"]:
                assert level["depth"] != 0
                assert level["packages"] != []
                for package in level["packages"]:
                    assert package["srpm"] != ""
                    assert package["name"] != ""
                    assert package["epoch"] >= 0
                    assert package["version"] != ""
                    assert package["release"] != ""
                    assert package["arch"] != "" and package["arch"] in (
                        (kwargs["archs"] if kwargs["archs"] else ["x86_64"])
                        + ["noarch"]
                    )


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "branch": BRANCH_IN_DB,
            "name": SRC_PKG_NAME,
            "dp_type": None,
            "status_code": 200,
        },
        {
            "branch": BRANCH_IN_DB,
            "name": SRC_PKG_NAME,
            "dp_type": None,
            "status_code": 200,
        },
        {
            "branch": BRANCH_IN_DB,
            "name": SRC_PKG_NAME,
            "dp_type": "source",
            "status_code": 200,
        },
        {
            "branch": BRANCH_IN_DB,
            "name": SRC_PKG_NAME,
            "dp_type": "binary",
            "status_code": 200,
        },
        {
            "branch": BRANCH_IN_DB,
            "name": SRC_PKG_NAME,
            "dp_type": "both",
            "status_code": 200,
        },
        {
            "branch": BRANCH_IN_DB,
            "name": BIN_PKG_NAME,
            "dp_type": None,
            "status_code": 404,
        },
        {
            "branch": BRANCH_NOT_IN_DB,
            "name": SRC_PKG_NAME,
            "dp_type": None,
            "status_code": 400,
        },
    ],
)
def test_wds(client, kwargs):
    url = url_for("api.dependencies_route_package_build_dependency")
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
        assert data["dependencies"] != []
        for elem in data["dependencies"]:
            assert elem["name"] != kwargs["name"]
            assert elem["depends"] != []
            for dep in elem["depends"]:
                assert dep["requires"] != {}
                assert dep["provides"] != {}
                if kwargs["dp_type"] == "source":
                    assert dep["requires"]["arch"] == "srpm"
                elif kwargs["dp_type"] == "binary":
                    assert dep["requires"]["arch"] != "srpm"


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "branch": BRANCH_IN_DB,
            "dp_name": DP_NAME_IN_DB,
            "status_code": 200,
        },
        {
            "branch": BRANCH_IN_DB,
            "dp_name": DP_NAME_IN_DB,
            "limit": 100,
            "status_code": 200,
        },
        {
            "branch": BRANCH_IN_DB,
            "dp_name": DP_NAME_NOT_IN_DB,
            "status_code": 404,
        },
        {
            "branch": BRANCH_IN_DB,
            "dp_name": DP_NAME_IN_DB,
            "limit": 10000,
            "status_code": 400,
        },
        {
            "branch": BRANCH_NOT_IN_DB,
            "dp_name": DP_NAME_NOT_IN_DB,
            "status_code": 400,
        },
    ],
)
def test_fast_lookup(client, kwargs):
    url = url_for("api.dependencies_route_fast_lookup")
    params = {k: v for k, v in kwargs.items() if k != "status_code"}
    response = client.get(url, query_string=params)

    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["length"] != 0
        assert data["dependencies"] != []
