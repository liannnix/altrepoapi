import base64
import pytest
from flask import url_for

PKGHASH_SRC_CURL = 1000000
PKGHASH_BIN_CURL = 2000000
ARCHS_IN_DB = "noarch,x86_64"
ARCHS_NOT_IN_DB = "fakearch1,fakearch2"
BRANCH_IN_DB = "sisyphus"
BRANCHES_IN_DB = "sisyphus,p10"
BRANCH_NOT_IN_DB = "fakebranch"
BRANCHES_NOT_IN_DB = "fakebranch1,fakebranch2"
PKG_NOT_IN_DB = "fakepackage"
BIN_PKG_HASH_IN_DB = 2737734146634739740  # curl-7.80.0-alt1.x86_64.rpm
SRC_PKG_HASH_IN_DB = 2737731585263144792  # curl-7.80.0-alt1.src.rpm
FILE_MD5_IN_DB = "d2b0c6770f40995c844f3291acc8227b"  # /bin/bash4


@pytest.mark.parametrize(
    "kwargs",
    [
        {"branch": BRANCH_IN_DB, "packages": "curl", "status_code": 200},
        {"branch": BRANCH_IN_DB, "packages": "bash,mc", "arch": "i586", "status_code": 200},
        {"branch": BRANCH_IN_DB, "packages": "", "status_code": 400},
        {"branch": BRANCH_IN_DB, "packages": "curl", "arch": "fakearch", "status_code": 400},
        {"branch": BRANCH_NOT_IN_DB, "packages": "curl", "status_code": 400},
        {"branch": BRANCH_IN_DB, "packages": PKG_NOT_IN_DB, "status_code": 404},
    ],
)
def test_build_dependency_set(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("pkghash", "status_code"):
            continue
        if v is not None:
            params[k] = v
    url = url_for("api.package_route_package_build_dependency_set")
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["length"] != 0
        assert data["request_args"]["branch"] == BRANCH_IN_DB
        assert data["packages"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"packages": "curl", "branches": BRANCHES_IN_DB, "status_code": 200},
        {"packages": "bash,mc", "branches": None, "status_code": 200},
        {"packages": "", "branches": BRANCH_IN_DB, "status_code": 400},
        {"packages": "curl", "branches": BRANCHES_NOT_IN_DB, "status_code": 400},
        {"packages": "curl", "branches": BRANCH_NOT_IN_DB, "status_code": 400},
        {"packages": PKG_NOT_IN_DB, "branches": None, "status_code": 404},
    ],
)
def test_find_packageset(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("pkghash", "status_code"):
            continue
        if v is not None:
            params[k] = v
    url = url_for("api.package_route_find_packageset")
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
        {
            "branch": BRANCH_IN_DB,
            "packages": "curl,mc",
            "archs": ARCHS_IN_DB,
            "status_code": 200,
        },
        {
            "branch": BRANCH_IN_DB,
            "packages": "syslinux",
            "archs": None,
            "status_code": 200,
        },
        {"branch": BRANCH_IN_DB, "packages": "", "archs": None, "status_code": 400},
        {
            "branch": BRANCH_NOT_IN_DB,
            "packages": "curl",
            "archs": None,
            "status_code": 400,
        },
        {
            "branch": BRANCH_IN_DB,
            "packages": "syslinux",
            "archs": ARCHS_NOT_IN_DB,
            "status_code": 400,
        },
        {
            "branch": BRANCH_IN_DB,
            "packages": PKG_NOT_IN_DB,
            "archs": None,
            "status_code": 404,
        },
    ],
)
def test_misconflict_packages(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("pkghash", "status_code"):
            continue
        if v is not None:
            params[k] = v
    url = url_for("api.package_route_package_misconflict_packages")
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        if kwargs["packages"] == "syslinux":
            assert data["length"] != 0
            assert data["conflicts"] != []
        else:
            assert data["length"] == 0
            assert data["conflicts"] == []
        assert data["request_args"]["packages"] != 0


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "branch": BRANCH_IN_DB,
            "md5": FILE_MD5_IN_DB,
            "arch": None,
            "status_code": 200,
        },
        {
            "branch": BRANCH_IN_DB,
            "md5": FILE_MD5_IN_DB,
            "arch": "x86_64",
            "status_code": 200,
        },
        {
            "branch": BRANCH_IN_DB,
            "md5": FILE_MD5_IN_DB.upper(),
            "arch": None,
            "status_code": 200,
        },
        {"branch": BRANCH_IN_DB, "md5": None, "arch": None, "status_code": 400},
        {
            "branch": BRANCH_IN_DB,
            "md5": FILE_MD5_IN_DB,
            "arch": "fakearch",
            "status_code": 400,
        },
        {
            "branch": BRANCH_NOT_IN_DB,
            "md5": FILE_MD5_IN_DB,
            "arch": None,
            "status_code": 400,
        },
        {
            "branch": BRANCH_IN_DB,
            "md5": "test01234567890",
            "arch": None,
            "status_code": 400,
        },
        {
            "branch": BRANCH_IN_DB,
            "md5": FILE_MD5_IN_DB,
            "arch": "noarch",
            "status_code": 404,
        },
        {
            "branch": BRANCH_IN_DB,
            "md5": "0123456789abcdef0123456789abcdef",
            "arch": None,
            "status_code": 404,
        },
    ],
)
def test_package_by_file_md5(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("pkghash", "status_code"):
            continue
        if v is not None:
            params[k] = v
    url = url_for("api.package_route_package_by_file_md5")
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["length"] != 0
        assert data["request_args"]["branch"] == BRANCH_IN_DB
        assert data["packages"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"branch": BRANCH_IN_DB, "file": "/bin/bash", "arch": None, "status_code": 200},
        {
            "branch": BRANCH_IN_DB,
            "file": "/bin/bash4",
            "arch": "x86_64",
            "status_code": 200,
        },
        {
            "branch": BRANCH_IN_DB,
            "file": "/bin/bash*",
            "arch": None,
            "status_code": 200,
        },
        {
            "branch": BRANCH_IN_DB,
            "file": "/usr/lib64/libstdc++.so*",
            "arch": None,
            "status_code": 200,
        },
        {"branch": BRANCH_IN_DB, "file": None, "arch": None, "status_code": 400},
        {
            "branch": BRANCH_IN_DB,
            "file": "/bin/bash*",
            "arch": "fakearch",
            "status_code": 400,
        },
        {
            "branch": BRANCH_NOT_IN_DB,
            "file": "/bin/bash",
            "arch": None,
            "status_code": 400,
        },
        {
            "branch": BRANCH_IN_DB,
            "file": "/usr/bin/curl",
            "arch": "noarch",
            "status_code": 404,
        },
        {"branch": BRANCH_IN_DB, "file": "fakefile", "arch": None, "status_code": 404},
    ],
)
def test_package_by_file_name(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("pkghash", "status_code"):
            continue
        if v is not None:
            params[k] = v
    url = url_for("api.package_route_package_by_file_name")
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["length"] != 0
        assert data["request_args"]["branch"] == BRANCH_IN_DB
        assert data["packages"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "branch": BRANCH_IN_DB,
            "files": ["/bin/bash"],
            "arch": None,
            "status_code": 200,
        },
        {
            "branch": BRANCH_IN_DB,
            "files": [
                "/bin/bash4",
            ],
            "arch": "x86_64",
            "status_code": 200,
        },
        {
            "branch": BRANCH_IN_DB,
            "files": [
                "/bin/bash*",
            ],
            "arch": None,
            "status_code": 400,
        },
        {
            "branch": BRANCH_IN_DB,
            "files": [
                "/usr/lib64/libstdc++.so*",
            ],
            "arch": None,
            "status_code": 400,
        },
        {
            "branch": BRANCH_IN_DB,
            "files": [
                "/usr/lib64/libstdc++.so*",
                "/bin/bash4",
            ],
            "arch": None,
            "status_code": 400,
        },
        {
            "branch": BRANCH_IN_DB,
            "files": [
                "fakefile*",
                "/bin/bash4",
                "/bin/bash*",
            ],
            "arch": None,
            "status_code": 400,
        },
        {"branch": BRANCH_IN_DB, "files": None, "arch": None, "status_code": 400},
        {
            "branch": BRANCH_IN_DB,
            "files": [
                "/bin/bash*",
            ],
            "arch": "fakearch",
            "status_code": 400,
        },
        {
            "branch": BRANCH_NOT_IN_DB,
            "files": [
                "/bin/bash",
            ],
            "arch": None,
            "status_code": 400,
        },
        {
            "branch": BRANCH_IN_DB,
            "files": [
                "/usr/bin/curl",
            ],
            "arch": "noarch",
            "status_code": 404,
        },
        {
            "branch": BRANCH_IN_DB,
            "files": [
                "fakefile",
            ],
            "arch": None,
            "status_code": 404,
        },
    ],
)
def test_packages_by_file_names(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("pkghash", "status_code"):
            continue
        if v is not None:
            params[k] = v
    url = url_for("api.package_route_packages_by_file_names")
    response = client.post(url, json=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["length"] != 0
        assert data["request_args"]["json_data"]["branch"] == BRANCH_IN_DB
        assert data["packages"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"pkghash": BIN_PKG_HASH_IN_DB, "status_code": 200},
        {"pkghash": 1234567890, "status_code": 404},
    ],
)
def test_package_files(client, kwargs):
    url = url_for(
        "api.package_route_bin_package_files", **{"pkghash": kwargs["pkghash"]}
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
        assert data["files"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "name": "curl",
            "version": None,
            "release": None,
            "arch": None,
            "source": None,
            "branch": None,
            "full": None,
            "status_code": 200,
        },
        {
            "name": "curl",
            "version": None,
            "release": None,
            "arch": None,
            "source": None,
            "branch": BRANCH_IN_DB,
            "full": None,
            "status_code": 200,
        },
        {
            "name": "curl",
            "version": None,
            "release": None,
            "arch": None,
            "source": "true",
            "branch": BRANCH_IN_DB,
            "full": "true",
            "status_code": 200,
        },
        {
            "name": "curl",
            "version": None,
            "release": None,
            "arch": "x86_64",
            "source": "false",
            "branch": BRANCH_IN_DB,
            "full": "false",
            "status_code": 200,
        },
        {
            "name": "x",
            "version": None,
            "release": None,
            "arch": None,
            "source": None,
            "branch": BRANCH_IN_DB,
            "full": None,
            "status_code": 400,
        },
        {
            "name": "curl",
            "version": "version 123",
            "release": None,
            "arch": None,
            "source": None,
            "branch": BRANCH_IN_DB,
            "full": None,
            "status_code": 400,
        },
        {
            "name": "curl",
            "version": None,
            "release": "alt-99",
            "arch": None,
            "source": None,
            "branch": BRANCH_IN_DB,
            "full": None,
            "status_code": 400,
        },
        {
            "name": "curl",
            "version": None,
            "release": None,
            "arch": "fakearch",
            "source": None,
            "branch": BRANCH_IN_DB,
            "full": None,
            "status_code": 400,
        },
        {
            "name": "curl",
            "version": None,
            "release": None,
            "arch": None,
            "source": None,
            "branch": BRANCH_NOT_IN_DB,
            "full": None,
            "status_code": 400,
        },
        {
            "name": "fakepackage",
            "version": None,
            "release": None,
            "arch": None,
            "source": None,
            "branch": None,
            "full": None,
            "status_code": 404,
        },
    ],
)
def test_package_info(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("pkghash", "status_code"):
            continue
        if v is not None:
            params[k] = v
    url = url_for("api.package_route_package_info")
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
        {
            "packages": [
                {
                    "pkg_name": "string",
                    "pkg_version": "string",
                    "pkg_release": "string",
                    "pkg_arch": "string",
                    "pkgset_name": "string",
                    "rc_srcpkg_name": "string",
                    "rc_srcpkg_version": "string",
                    "rc_srcpkg_release": "string",
                    "rc_test_name": "string",
                    "rc_test_status": "string",
                    "rc_test_message": "string",
                    "rc_test_date": "2022-03-11T08:49:28",
                }
            ]
        }
    ],
)
def test_repocop_post(client, kwargs):
    url = url_for("api.package_route_package_repocop")
    response = client.post(url, json=kwargs)
    assert response.status_code == 401


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "branch": BRANCH_IN_DB,
            "package_name": "curl",
            "package_version": None,
            "package_release": None,
            "bin_package_arch": None,
            "package_type": "source",
            "status_code": 200,
        },
        {
            "branch": BRANCH_IN_DB,
            "package_name": "curl",
            "package_version": None,
            "package_release": None,
            "bin_package_arch": "x86_64",
            "package_type": "binary",
            "status_code": 200,
        },
        {
            "branch": BRANCH_NOT_IN_DB,
            "package_name": "curl",
            "package_version": None,
            "package_release": None,
            "bin_package_arch": None,
            "package_type": "source",
            "status_code": 400,
        },
        {
            "branch": BRANCH_IN_DB,
            "package_name": "curl",
            "package_version": "fake-version",
            "package_release": None,
            "bin_package_arch": None,
            "package_type": "source",
            "status_code": 400,
        },
        {
            "branch": BRANCH_IN_DB,
            "package_name": "curl",
            "package_version": None,
            "package_release": "fake release",
            "bin_package_arch": None,
            "package_type": "source",
            "status_code": 400,
        },
        {
            "branch": BRANCH_IN_DB,
            "package_name": "curl",
            "package_version": None,
            "package_release": None,
            "bin_package_arch": "fakearch",
            "package_type": "source",
            "status_code": 400,
        },
        {
            "branch": BRANCH_IN_DB,
            "package_name": PKG_NOT_IN_DB,
            "package_version": None,
            "package_release": None,
            "bin_package_arch": None,
            "package_type": "source",
            "status_code": 404,
        },
    ],
)
def test_repocop_get(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("pkghash", "status_code"):
            continue
        if v is not None:
            params[k] = v
    url = url_for("api.package_route_package_repocop")
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
        {"pkghash": SRC_PKG_HASH_IN_DB, "status_code": 200},
        {"pkghash": BIN_PKG_HASH_IN_DB, "status_code": 404},
    ],
)
def test_specfile_by_hash(client, kwargs):
    url = url_for(
        "api.package_route_specfile_by_package_hash", **{"pkghash": kwargs["pkghash"]}
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
        assert data["pkg_hash"] == str(kwargs["pkghash"])
        assert data["pkg_name"] != ""
        assert data["pkg_version"] != ""
        assert data["pkg_release"] != ""
        assert data["specfile_name"] != ""
        assert data["specfile_date"] != ""
        content = None
        try:
            content = base64.b64decode(data["specfile_content"]).decode("utf-8")
        except ValueError:
            pass
        assert content is not None


@pytest.mark.parametrize(
    "kwargs",
    [
        {"branch": BRANCH_IN_DB, "name": "curl", "status_code": 200},
        {"branch": BRANCH_NOT_IN_DB, "name": "curl", "status_code": 400},
        {"branch": BRANCH_IN_DB, "name": "fail name", "status_code": 400},
        {"branch": BRANCH_IN_DB, "name": PKG_NOT_IN_DB, "status_code": 404},
    ],
)
def test_specfile_by_name(client, kwargs):
    url = url_for("api.package_route_specfile_by_package_name")
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
        assert data["pkg_name"] != ""
        assert data["pkg_version"] != ""
        assert data["pkg_release"] != ""
        assert data["specfile_name"] != ""
        assert data["specfile_date"] != ""
        content = None
        try:
            content = base64.b64decode(data["specfile_content"]).decode("utf-8")
        except ValueError:
            pass
        assert content is not None


@pytest.mark.parametrize(
    "kwargs",
    [
        {"branch": BRANCH_IN_DB, "packager": "ldv", "archs": None, "status_code": 200},
        {
            "branch": BRANCH_NOT_IN_DB,
            "packager": "ldv",
            "archs": None,
            "status_code": 400,
        },
        {
            "branch": BRANCH_IN_DB,
            "packager": "ldv",
            "archs": "fakearch",
            "status_code": 400,
        },
        {
            "branch": BRANCH_IN_DB,
            "packager": "fakepackager",
            "archs": None,
            "status_code": 404,
        },
    ],
)
def test_unpackaged_dirs(client, kwargs):
    url = url_for("api.package_route_unpackaged_dirs")
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
        assert data["packages"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"branch": BRANCH_IN_DB, "packages": "curl", "depth": None, "status_code": 200},
        {"branch": BRANCH_IN_DB, "packages": "mc,bash", "depth": 2, "status_code": 200},
        {"branch": BRANCH_IN_DB, "packages": "curl", "depth": 1, "use_last_tasks": "true", "status_code": 200},
        {"branch": BRANCH_IN_DB, "packages": "curl", "dptype": "binary", "status_code": 200},
        {"branch": BRANCH_IN_DB, "packages": "", "depth": None, "status_code": 400},
        {"branch": BRANCH_IN_DB, "packages": "mc,x", "depth": None, "status_code": 400},
        {"branch": BRANCH_NOT_IN_DB, "packages": "curl", "depth": None, "status_code": 400},
    ],
)
def test_wds(client, kwargs):
    url = url_for("api.package_route_package_build_dependency")
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
