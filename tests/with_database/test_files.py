import pytest
from flask import url_for


FILE_IN_DB = [
    "gtksourceview-5/language-specs",
    "Colloid-green-light/mimetypes/scalable/image-svg+xml.svg",
    "meta.cpython-37.opt-1.pyc"
]
FULL_PATH_FILE_IN_DB = [
    "/usr/share/gtksourceview-5/language-specs",
    "/usr/share/icons/Colloid-green-light/mimetypes/scalable/image-svg+xml.svg",
    "/usr/lib/python3/site-packages/collective/monkeypatcher/__pycache__/meta.cpython-37.opt-1.pyc"
]
FILE_NOT_IN_DB = "gtksourceview-5/language-specs/abc"
INVALID_FILE_NAME = "gtksourceview-5/language-specs^"
BRANCH_IN_DB = "sisyphus"
BRANCH_NOT_IN_DB = "abc"


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "branch": BRANCH_IN_DB,
            "file_name": FILE_IN_DB[0],
            "status_code": 200
        },
        {
            "branch": BRANCH_IN_DB,
            "file_name": FILE_IN_DB[1],
            "status_code": 200
        },
        {
            "branch": BRANCH_IN_DB,
            "file_name": FILE_IN_DB[2],
            "status_code": 200
        },
        {
            "branch": BRANCH_NOT_IN_DB,
            "file_name": FILE_IN_DB[0],
            "status_code": 400
        },
        {
            "branch": BRANCH_IN_DB,
            "file_name": INVALID_FILE_NAME,
            "status_code": 400
        },
        {
            "branch": BRANCH_IN_DB,
            "file_name": FILE_NOT_IN_DB,
            "status_code": 404
        },
    ],
)
def test_file_search(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("status_code",):
            continue
        if v is not None:
            params[k] = v
    url = url_for("api.file_route_file_search")
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
            "branch": BRANCH_IN_DB,
            "file_name": FILE_IN_DB[0],
            "status_code": 200
        },
        {
            "branch": BRANCH_IN_DB,
            "file_name": FILE_IN_DB[1],
            "status_code": 200
        },
        {
            "branch": BRANCH_IN_DB,
            "file_name": FILE_IN_DB[2],
            "status_code": 200
        },
        {
            "branch": BRANCH_NOT_IN_DB,
            "file_name": FILE_IN_DB[0],
            "status_code": 400
        },
        {
            "branch": BRANCH_IN_DB,
            "file_name": INVALID_FILE_NAME,
            "status_code": 400
        },
        {
            "branch": BRANCH_IN_DB,
            "file_name": FILE_NOT_IN_DB,
            "status_code": 404
        },
    ],
)
def test_fast_lookup(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("status_code",):
            continue
        if v is not None:
            params[k] = v
    url = url_for("api.file_route_fast_lookup")
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
            "branch": BRANCH_IN_DB,
            "file_name": FULL_PATH_FILE_IN_DB[0],
            "status_code": 200
        },
        {
            "branch": BRANCH_IN_DB,
            "file_name": FULL_PATH_FILE_IN_DB[1],
            "status_code": 200
        },
        {
            "branch": BRANCH_IN_DB,
            "file_name": FULL_PATH_FILE_IN_DB[2],
            "status_code": 200
        },
        {
            "branch": BRANCH_IN_DB,
            "file_name": FILE_IN_DB[0],
            "status_code": 404
        },
        {
            "branch": BRANCH_NOT_IN_DB,
            "file_name": FILE_IN_DB[0],
            "status_code": 400
        },
        {
            "branch": BRANCH_IN_DB,
            "file_name": INVALID_FILE_NAME,
            "status_code": 400
        },
        {
            "branch": BRANCH_IN_DB,
            "file_name": FILE_NOT_IN_DB,
            "status_code": 404
        },
    ],
)
def test_packages_by_file(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("status_code",):
            continue
        if v is not None:
            params[k] = v

    url = url_for("api.file_route_packages_by_file")
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["length"] != 0
        assert data["packages"] != []
