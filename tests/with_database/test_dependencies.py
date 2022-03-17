import pytest
from flask import url_for


BRANCH_IN_DB = "sisyphus"
BRANCH_NOT_IN_DB = "fakebranch"
BIN_PKG_HASH_IN_DB = 2737734146634739740  # curl-7.80.0-alt1.x86_64.rpm
SRC_PKG_HASH_IN_DB = 2737731585263144792  # curl-7.80.0-alt1.src.rpm
PKG_HASH_NOT_IN_DB = 1234567890
DP_NAME_IN_DB = "curl"
DP_NAME_NOT_IN_DB = "fakepackage"

@pytest.mark.parametrize(
    "kwargs",
    [
        {"branch": BRANCH_IN_DB, "dp_name": DP_NAME_IN_DB, "dp_type": None, "status_code": 200},
        {"branch": BRANCH_IN_DB, "dp_name": DP_NAME_IN_DB, "dp_type": "provide", "status_code": 200},
        {"branch": BRANCH_IN_DB, "dp_name": DP_NAME_NOT_IN_DB, "dp_type": None, "status_code": 404},
        {"branch": BRANCH_NOT_IN_DB, "dp_name": DP_NAME_IN_DB, "dp_type": None, "status_code": 400},
        {"branch": None, "dp_name": DP_NAME_IN_DB, "dp_type": None, "status_code": 400},
        {"branch": BRANCH_IN_DB, "dp_name": None, "dp_type": None, "status_code": 400},
        {"branch": BRANCH_IN_DB, "dp_name": DP_NAME_IN_DB, "dp_type": "abc", "status_code": 400},
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
        assert data["versions"] != []


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
