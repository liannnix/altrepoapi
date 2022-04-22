import pytest
from flask import url_for


ARCH_IN_DB = "x86_64"
ARCH_NOT_IN_DB = "fakearch"
BRANCH_IN_DB = "sisyphus"
BRANCH_NOT_IN_DB = "fakebranch"
SRC_PACKAGE_IN_DB = "curl"
BIN_PACKAGE_IN_DB = "libcurl"
PACKAGE_NOT_IN_DB = "fakepackage"
BIN_PKG_HASH_IN_DB = 2737734146634739740  # curl-7.80.0-alt1.x86_64.rpm
SRC_PKG_HASH_IN_DB = 2737731585263144792  # curl-7.80.0-alt1.src.rpm
PKG_HASH_NOT_IN_DB = 1234567890
BIN_PKG_HASH_IN_DB_W_SCRIPTS = (
    2741769951412931821  # docker-engine-20.10.11-alt1.x86_64.rpm
)
DELETED_BIN_PACKAGE = "tgt-debuginfo"  # x86_64
DELETED_SRC_PACKAGE = "python3-module-flask-script"


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "pkghash": SRC_PKG_HASH_IN_DB,
            "branch": BRANCH_IN_DB,
            "package_type": None,
            "changelog_last": 1,
            "status_code": 200,
        },
        {
            "pkghash": BIN_PKG_HASH_IN_DB,
            "branch": BRANCH_IN_DB,
            "package_type": "binary",
            "changelog_last": None,
            "status_code": 200,
        },
        {
            "pkghash": BIN_PKG_HASH_IN_DB,
            "branch": BRANCH_IN_DB,
            "package_type": "source",
            "changelog_last": None,
            "status_code": 404,
        },
        {
            "pkghash": SRC_PKG_HASH_IN_DB,
            "branch": BRANCH_IN_DB,
            "package_type": "binary",
            "changelog_last": None,
            "status_code": 404,
        },
        {
            "pkghash": SRC_PKG_HASH_IN_DB,
            "branch": BRANCH_NOT_IN_DB,
            "package_type": None,
            "changelog_last": None,
            "status_code": 400,
        },
        {
            "pkghash": SRC_PKG_HASH_IN_DB,
            "branch": BRANCH_IN_DB,
            "package_type": "abc",
            "changelog_last": None,
            "status_code": 400,
        },
        {
            "pkghash": SRC_PKG_HASH_IN_DB,
            "branch": BRANCH_IN_DB,
            "package_type": None,
            "changelog_last": 0,
            "status_code": 400,
        },
    ],
)
def test_package_info(client, kwargs):
    url = url_for("api.site_route_package_info", **{"pkghash": kwargs["pkghash"]})
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
        assert data["pkghash"] != ""
        assert data["maintainers"] != []
        assert data["package_archs"] != []
        if kwargs["package_type"] == "source":
            assert data["tasks"] != []
        assert data["changelog"] != []
        assert data["versions"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"branch": BRANCH_IN_DB, "name": BIN_PACKAGE_IN_DB, "status_code": 200},
        {"branch": BRANCH_IN_DB, "name": PACKAGE_NOT_IN_DB, "status_code": 404},
        {"branch": BRANCH_NOT_IN_DB, "name": BIN_PACKAGE_IN_DB, "status_code": 400},
        {"branch": BRANCH_IN_DB, "name": "", "status_code": 400},
    ],
)
def test_binary_package_archs_and_versions(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("pkghash", "status_code"):
            continue
        if v is not None:
            params[k] = v
    url = url_for("api.site_route_packages_binary_list")
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["length"] != 0
        assert data["packages"] != []
        assert data["versions"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"pkghash": SRC_PKG_HASH_IN_DB, "changelog_last": None, "status_code": 200},
        {"pkghash": BIN_PKG_HASH_IN_DB, "changelog_last": 1, "status_code": 200},
        {"pkghash": SRC_PKG_HASH_IN_DB, "changelog_last": 0, "status_code": 400},
        {"pkghash": SRC_PKG_HASH_IN_DB, "changelog_last": -10, "status_code": 400},
        {"pkghash": PKG_HASH_NOT_IN_DB, "changelog_last": None, "status_code": 404},
    ],
)
def test_package_changelog(client, kwargs):
    url = url_for("api.site_route_package_changelog", **{"pkghash": kwargs["pkghash"]})
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
        assert data["pkghash"] != ""
        assert data["changelog"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "branch": BRANCH_IN_DB,
            "name": DELETED_SRC_PACKAGE,
            "package_type": None,
            "arch": None,
            "status_code": 200,
        },
        {
            "branch": BRANCH_IN_DB,
            "name": DELETED_BIN_PACKAGE,
            "package_type": "binary",
            "arch": ARCH_IN_DB,
            "status_code": 200,
        },
        {
            "branch": BRANCH_IN_DB,
            "name": SRC_PACKAGE_IN_DB,
            "package_type": None,
            "arch": None,
            "status_code": 404,
        },
        {
            "branch": BRANCH_IN_DB,
            "name": PACKAGE_NOT_IN_DB,
            "package_type": None,
            "arch": None,
            "status_code": 404,
        },
        {
            "branch": BRANCH_NOT_IN_DB,
            "name": DELETED_SRC_PACKAGE,
            "package_type": None,
            "arch": None,
            "status_code": 400,
        },
        {
            "branch": BRANCH_IN_DB,
            "name": "",
            "package_type": None,
            "arch": None,
            "status_code": 400,
        },
        {
            "branch": BRANCH_IN_DB,
            "name": DELETED_SRC_PACKAGE,
            "package_type": "abc",
            "arch": None,
            "status_code": 400,
        },
        {
            "branch": BRANCH_IN_DB,
            "name": DELETED_SRC_PACKAGE,
            "package_type": "binary",
            "arch": ARCH_NOT_IN_DB,
            "status_code": 400,
        },
    ],
)
def test_deleted_package_info(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("pkghash", "status_code"):
            continue
        if v is not None:
            params[k] = v
    url = url_for("api.site_route_deleted_package_info")
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["hash"] != ""
        assert data["branch"] != ""
        assert data["package"] != ""
        assert data["version"] != ""
        assert data["task_id"] != 0
        assert data["subtask_id"] != 0


@pytest.mark.parametrize(
    "kwargs",
    [
        {"pkghash": BIN_PKG_HASH_IN_DB_W_SCRIPTS, "status_code": 200},
        {"pkghash": PKG_HASH_NOT_IN_DB, "status_code": 404},
    ],
)
def test_binary_package_scripts(client, kwargs):
    url = url_for(
        "api.site_route_bin_package_scripts", **{"pkghash": kwargs["pkghash"]}
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
        assert data["pkg_arch"] != ""
        assert data["pkg_name"] != ""
        assert data["scripts"] != []
        assert data["versions"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"branch": BRANCH_IN_DB, "status_code": 200},
        {"branch": BRANCH_NOT_IN_DB, "status_code": 400},
    ],
)
def test_last_packages_with_cve_fixed(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("pkghash", "status_code"):
            continue
        if v is not None:
            params[k] = v
    url = url_for("api.site_route_last_packages_with_cve_fix")
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["length"] != 0
        assert data["packages"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"branch": BRANCH_IN_DB, "pkghash": SRC_PKG_HASH_IN_DB, "status_code": 200},
        {"branch": BRANCH_IN_DB, "pkghash": PKG_HASH_NOT_IN_DB, "status_code": 404},
        {"branch": BRANCH_NOT_IN_DB, "pkghash": SRC_PKG_HASH_IN_DB, "status_code": 400},
    ],
)
def test_package_downloads_src(client, kwargs):
    url = url_for(
        "api.site_route_package_download_links", **{"pkghash": kwargs["pkghash"]}
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
        assert data["pkghash"] != ""
        assert data["downloads"] != []
        # assert data["versions"] != []  # available only for packages from last branch state


@pytest.mark.parametrize(
    "kwargs",
    [
        {"branch": BRANCH_IN_DB, "pkghash": SRC_PKG_HASH_IN_DB, "status_code": 200},
        {"branch": BRANCH_IN_DB, "pkghash": PKG_HASH_NOT_IN_DB, "status_code": 404},
        {"branch": BRANCH_NOT_IN_DB, "pkghash": SRC_PKG_HASH_IN_DB, "status_code": 400},
    ],
)
def test_package_downloads(client, kwargs):
    url = f'api/site/package_downloads/{kwargs["pkghash"]}'
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
        assert data["pkghash"] != ""
        assert data["downloads"] != []
        # assert data["versions"] != []  # available only for packages from last branch state


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "branch": BRANCH_IN_DB,
            "pkghash": BIN_PKG_HASH_IN_DB,
            "arch": ARCH_IN_DB,
            "status_code": 200,
        },
        {
            "branch": BRANCH_IN_DB,
            "pkghash": PKG_HASH_NOT_IN_DB,
            "arch": ARCH_IN_DB,
            "status_code": 404,
        },
        {
            "branch": BRANCH_NOT_IN_DB,
            "pkghash": BIN_PKG_HASH_IN_DB,
            "arch": ARCH_IN_DB,
            "status_code": 400,
        },
        {
            "branch": BRANCH_IN_DB,
            "pkghash": BIN_PKG_HASH_IN_DB,
            "arch": ARCH_NOT_IN_DB,
            "status_code": 400,
        },
    ],
)
def test_package_downloads_bin(client, kwargs):
    url = url_for(
        "api.site_route_binary_package_download_links", **{"pkghash": kwargs["pkghash"]}
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
        assert data["pkghash"] != ""
        assert data["downloads"] != []
        # assert data["versions"] != []  # available only for packages from last branch state


@pytest.mark.parametrize(
    "kwargs",
    [
        {"name": SRC_PACKAGE_IN_DB, "status_code": 200},
        {"name": BIN_PACKAGE_IN_DB, "status_code": 404},
        {"name": PACKAGE_NOT_IN_DB, "status_code": 404},
        {"name": "", "status_code": 400},
    ],
)
def test_source_package_versions(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("pkghash", "status_code"):
            continue
        if v is not None:
            params[k] = v
    url = url_for("api.site_route_source_package_versions")
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["versions"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "name": SRC_PACKAGE_IN_DB,
            "package_type": None,
            "arch": None,
            "status_code": 200,
        },
        {
            "name": BIN_PACKAGE_IN_DB,
            "package_type": "binary",
            "arch": ARCH_IN_DB,
            "status_code": 200,
        },
        {
            "name": BIN_PACKAGE_IN_DB,
            "package_type": "binary",
            "arch": None,
            "status_code": 400,
        },
        {"name": "", "package_type": None, "arch": None, "status_code": 400},
        {
            "name": SRC_PACKAGE_IN_DB,
            "package_type": "abc",
            "arch": None,
            "status_code": 400,
        },
        {
            "name": SRC_PACKAGE_IN_DB,
            "package_type": None,
            "arch": ARCH_NOT_IN_DB,
            "status_code": 400,
        },
        {
            "name": BIN_PACKAGE_IN_DB,
            "package_type": "source",
            "arch": None,
            "status_code": 404,
        },
        {
            "name": PACKAGE_NOT_IN_DB,
            "package_type": None,
            "arch": None,
            "status_code": 404,
        },
    ],
)
def test_package_versions(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("pkghash", "status_code"):
            continue
        if v is not None:
            params[k] = v
    url = url_for("api.site_route_package_versions")
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["versions"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"pkghash": BIN_PKG_HASH_IN_DB, "status_code": 200},
        {"pkghash": SRC_PKG_HASH_IN_DB, "status_code": 404},
        {"pkghash": PKG_HASH_NOT_IN_DB, "status_code": 404},
    ],
)
def test_package_log_bin(client, kwargs):
    url = url_for("api.site_route_binary_package_log", **{"pkghash": kwargs["pkghash"]})
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
        assert data["pkg_hash"] != ""
        assert data["task_id"] != 0
        assert data["subtask_id"] != 0
        assert data["subtask_arch"] != ""
        assert data["buildlog_hash"] != ""
        assert data["link"] != ""


@pytest.mark.parametrize(
    "kwargs",
    [
        {"pkghash": SRC_PKG_HASH_IN_DB, "name": None, "status_code": 200},
        {"pkghash": BIN_PKG_HASH_IN_DB, "name": None, "status_code": 200},
        {"pkghash": SRC_PKG_HASH_IN_DB, "name": "curl", "status_code": 200},
        {"pkghash": BIN_PKG_HASH_IN_DB, "name": "curl", "status_code": 200},
        {"pkghash": BIN_PKG_HASH_IN_DB, "name": PACKAGE_NOT_IN_DB, "status_code": 404},
        {"pkghash": PKG_HASH_NOT_IN_DB, "name": None, "status_code": 404},
        {"pkghash": SRC_PKG_HASH_IN_DB, "name": " ", "status_code": 400},
        {"pkghash": SRC_PKG_HASH_IN_DB, "name": "**abc#", "status_code": 400},
    ],
)
def test_package_nvr_by_hash(client, kwargs):
    url = url_for(
        "api.site_route_package_nvr_by_hash", **{"pkghash": kwargs["pkghash"]}
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
        assert data["hash"] != ""
        assert data["name"] != ""
        assert data["is_source"] in (True, False)
