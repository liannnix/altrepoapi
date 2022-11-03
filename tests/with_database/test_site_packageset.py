import pytest
from flask import url_for

ARCH_IN_DB = "x86_64"
ARCH_NOT_IN_DB = "fakearch"
BRANCH_IN_DB = "sisyphus"
BRANCH_IN_DB_WO_TASKS = "sisyphus_mipsel"
BRANCH_NOT_IN_DB = "fakebranch"
GROUP_IN_DB_1 = "System/Configuration"  # has sub categories
GROUP_IN_DB_2 = "Office"  # has no sub categories
GROUP_NOT_IN_DB = "Fake group"
SRC_PACKAGE_IN_DB = "curl"
BIN_PACKAGE_IN_DB = "libcurl"
PACKAGE_NOT_IN_DB = "fakepackage"
PACKAGER_IN_DB = "rider"
PACKAGER_NOT_IN_DB = "fakepackager"
BIN_PKG_HASH_IN_DB = 2737734146634739740  # curl-7.80.0-alt1.x86_64.rpm
SRC_PKG_HASH_IN_DB = 2737731585263144792  # curl-7.80.0-alt1.src.rpm
PKG_HASH_NOT_IN_DB = 1234567890


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "branch": BRANCH_IN_DB,
            "package_type": "source",
            "group": None,
            "buildtime": None,
            "status_code": 200,
        },
        {
            "branch": BRANCH_IN_DB,
            "package_type": None,
            "group": GROUP_IN_DB_1,
            "buildtime": None,
            "status_code": 200,
        },
        {
            "branch": BRANCH_IN_DB,
            "package_type": "binary",
            "group": GROUP_IN_DB_2,
            "buildtime": None,
            "status_code": 200,
        },
        {
            "branch": BRANCH_NOT_IN_DB,
            "package_type": "source",
            "group": None,
            "buildtime": None,
            "status_code": 400,
        },
        {
            "branch": BRANCH_IN_DB,
            "package_type": "fake",
            "group": None,
            "buildtime": None,
            "status_code": 400,
        },
        {
            "branch": BRANCH_IN_DB,
            "package_type": None,
            "group": GROUP_NOT_IN_DB,
            "buildtime": None,
            "status_code": 400,
        },
        {
            "branch": BRANCH_IN_DB,
            "package_type": "binary",
            "group": None,
            "buildtime": -100,
            "status_code": 400,
        },
        {
            "branch": BRANCH_IN_DB,
            "package_type": None,
            "group": GROUP_IN_DB_2,
            "buildtime": 2_000_000_000,
            "status_code": 404,
        },
    ],
)
def test_repository_packages(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("pkghash", "status_code"):
            continue
        if v is not None:
            params[k] = v
    url = url_for("api.site_route_packageset_packages")
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["length"] != 0
        assert data["packages"] != []
        if kwargs["group"] == GROUP_IN_DB_1:
            assert data["subcategories"] != []
        if kwargs["group"] == GROUP_IN_DB_2:
            assert data["subcategories"] == []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"branch": BRANCH_IN_DB, "name": SRC_PACKAGE_IN_DB, "status_code": 200},
        {"branch": BRANCH_IN_DB, "name": PACKAGE_NOT_IN_DB, "status_code": 404},
        {"branch": BRANCH_IN_DB, "name": BIN_PACKAGE_IN_DB, "status_code": 404},
        {"branch": BRANCH_NOT_IN_DB, "name": SRC_PACKAGE_IN_DB, "status_code": 400},
        {"branch": BRANCH_IN_DB, "name": "", "status_code": 400},
    ],
)
def test_pkghash_by_name(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("pkghash", "status_code"):
            continue
        if v is not None:
            params[k] = v
    url = url_for("api.site_route_packageset_package_hash")
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["pkghash"] != ""
        assert data["version"] != ""
        assert data["release"] != ""


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "branch": BRANCH_IN_DB,
            "name": BIN_PACKAGE_IN_DB,
            "arch": ARCH_IN_DB,
            "status_code": 200,
        },
        {
            "branch": BRANCH_IN_DB,
            "name": PACKAGE_NOT_IN_DB,
            "arch": ARCH_IN_DB,
            "status_code": 404,
        },
        {
            "branch": BRANCH_NOT_IN_DB,
            "name": BIN_PACKAGE_IN_DB,
            "arch": ARCH_IN_DB,
            "status_code": 400,
        },
        {
            "branch": BRANCH_IN_DB,
            "name": BIN_PACKAGE_IN_DB,
            "arch": ARCH_NOT_IN_DB,
            "status_code": 400,
        },
        {"branch": BRANCH_IN_DB, "name": "", "arch": ARCH_IN_DB, "status_code": 400},
    ],
)
def test_pkghash_by_binary_name(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("pkghash", "status_code"):
            continue
        if v is not None:
            params[k] = v
    url = url_for("api.site_route_packageset_package_binary_hash")
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["pkghash"] != ""
        assert data["version"] != ""
        assert data["release"] != ""


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "branch": BRANCH_IN_DB,
            "name": "curl",
            "version": "7.78.0",
            "release": "alt1",
            "status_code": 200,
        },
        {
            "branch": BRANCH_IN_DB,
            "name": PACKAGE_NOT_IN_DB,
            "version": "7.78.0",
            "release": "alt1",
            "status_code": 404,
        },
        {
            "branch": BRANCH_NOT_IN_DB,
            "name": "curl",
            "version": "7.78.0",
            "release": "alt1",
            "status_code": 400,
        },
        {
            "branch": BRANCH_IN_DB,
            "name": "",
            "version": "7.78.0",
            "release": "alt1",
            "status_code": 400,
        },
        {
            "branch": BRANCH_IN_DB,
            "name": "curl",
            "version": "abc!",
            "release": "alt1",
            "status_code": 400,
        },
        {
            "branch": BRANCH_IN_DB,
            "name": "curl",
            "version": "1.2.3",
            "release": "",
            "status_code": 400,
        },
    ],
)
def test_pkghash_by_nvr(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("pkghash", "status_code"):
            continue
        if v is not None:
            params[k] = v
    url = url_for("api.site_route_packageset_pkghash_by_nvr")
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["pkghash"] != ""


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "branch": BRANCH_IN_DB_WO_TASKS,
            "packages_limit": 10,
            "packager": None,
            "status_code": 200,
        },
        {
            "branch": BRANCH_IN_DB,
            "packages_limit": 10,
            "packager": PACKAGER_IN_DB,
            "status_code": 200,
        },
        {
            "branch": BRANCH_IN_DB,
            "packages_limit": 10,
            "packager": PACKAGER_NOT_IN_DB,
            "status_code": 404,
        },
        {
            "branch": BRANCH_NOT_IN_DB,
            "packages_limit": 10,
            "packager": PACKAGER_IN_DB,
            "status_code": 400,
        },
        {
            "branch": BRANCH_IN_DB,
            "packages_limit": 0,
            "packager": PACKAGER_IN_DB,
            "status_code": 400,
        },
        {
            "branch": BRANCH_IN_DB,
            "packages_limit": -10,
            "packager": PACKAGER_IN_DB,
            "status_code": 400,
        },
        {
            "branch": BRANCH_IN_DB,
            "packages_limit": 10,
            "packager": " ",
            "status_code": 400,
        },
    ],
)
def test_last_packages_by_branch(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("pkghash", "status_code"):
            continue
        if v is not None:
            params[k] = v
    url = url_for("api.site_route_last_branch_packages")
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["length"] != 0
        assert data["packages"] != []
        assert data["last_branch_date"] != ""
        for pkg in data["packages"]:
            assert pkg["hash"] != ""


@pytest.mark.parametrize(
    "kwargs",
    [
        {"pkghash": BIN_PKG_HASH_IN_DB, "status_code": 200},
        {"pkghash": SRC_PKG_HASH_IN_DB, "status_code": 200},
        {"pkghash": PKG_HASH_NOT_IN_DB, "status_code": 404},
    ],
)
def test_packagesets_by_hash(client, kwargs):
    url = url_for("api.site_route_packagsets_by_hash", **{"pkghash": kwargs["pkghash"]})
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
        assert data["branches"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"name": SRC_PACKAGE_IN_DB, "branch": None, "arch": None, "status_code": 200},
        {
            "name": "getssl",
            "branch": "p10",
            "arch": None,
            "status_code": 200,
        },  # source package deleted from branch
        {
            "name": BIN_PACKAGE_IN_DB,
            "branch": BRANCH_IN_DB,
            "arch": None,
            "status_code": 200,
        },
        {
            "name": BIN_PACKAGE_IN_DB,
            "branch": BRANCH_IN_DB,
            "arch": ARCH_IN_DB,
            "status_code": 200,
        },
        {"name": PACKAGE_NOT_IN_DB, "branch": None, "arch": None, "status_code": 404},
        {"name": "", "branch": None, "arch": None, "status_code": 400},
        {
            "name": SRC_PACKAGE_IN_DB,
            "branch": BRANCH_NOT_IN_DB,
            "arch": None,
            "status_code": 400,
        },
        {
            "name": SRC_PACKAGE_IN_DB,
            "branch": None,
            "arch": ARCH_NOT_IN_DB,
            "status_code": 400,
        },
    ],
)
def test_find_packages(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("pkghash", "status_code"):
            continue
        if v is not None:
            params[k] = v
    url = url_for("api.site_route_packageset_find_packages")
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["length"] != 0
        assert data["packages"] != []
        for pkg in data["packages"]:
            assert pkg["versions"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"name": SRC_PACKAGE_IN_DB, "branch": None, "status_code": 200},
        {"name": BIN_PACKAGE_IN_DB, "branch": BRANCH_IN_DB, "status_code": 200},
        {
            "name": "getssl",
            "branch": "p10",
            "status_code": 200,
        },  # source package deleted from branch
        {
            "name": "getssl",
            "branch": "sisyphus",
            "status_code": 200,
        },  # source package deleted from branch
        {"name": PACKAGE_NOT_IN_DB, "branch": None, "status_code": 404},
        {"name": SRC_PACKAGE_IN_DB, "branch": BRANCH_NOT_IN_DB, "status_code": 400},
        {"name": "", "branch": None, "status_code": 400},
    ],
)
def test_fast_packages_search_lookup(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("pkghash", "status_code"):
            continue
        if v is not None:
            params[k] = v
    url = url_for("api.site_route_packageset_fast_packages_search")
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["length"] != 0
        assert data["packages"] != []
        for pkg in data["packages"]:
            assert pkg["branches"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"name": SRC_PACKAGE_IN_DB, "branch": BRANCH_IN_DB, "status_code": 200},
        {"name": BIN_PACKAGE_IN_DB, "branch": BRANCH_IN_DB, "status_code": 200},
        {
            "name": "getssl",
            "branch": BRANCH_IN_DB,
            "status_code": 200,
        },  # source package deleted from branch
        {"name": PACKAGE_NOT_IN_DB, "branch": BRANCH_IN_DB, "status_code": 404},
        {"name": SRC_PACKAGE_IN_DB, "branch": BRANCH_NOT_IN_DB, "status_code": 400},
        {"name": PACKAGE_NOT_IN_DB, "branch": None, "status_code": 400},
        {"name": "", "branch": None, "status_code": 400},
    ],
)
def test_find_source_package(client, kwargs):
    params = {k: v for k, v in kwargs.items() if k != "status_code"}
    url = url_for("api.site_route_find_source_package")
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["source_package"] != ""
