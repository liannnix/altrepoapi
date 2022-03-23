import pytest
from flask import url_for

BRANCH_IN_DB = "p10"
BRANCH_NOT_IN_DB = "fakebranch"
EDITION_IN_DB = "alt-workstation"
EDITION_NOT_IN_DB = "fakeedititon"
PKG_IN_DB = "curl"
PKG_NOT_IN_DB = "fakepackage"
IMAGE_TYPE_IN_DB = "iso"
IMAGE_TYPE_NOT_IN_DB = "faketype"

@pytest.mark.parametrize(
    "kwargs",
    [
        {"name": PKG_IN_DB,"branch": BRANCH_IN_DB, "edition": EDITION_IN_DB, "type": IMAGE_TYPE_IN_DB, "status_code": 200},
        {"name": PKG_NOT_IN_DB,"branch": BRANCH_IN_DB, "edition": EDITION_IN_DB, "type": IMAGE_TYPE_IN_DB, "status_code": 404},
        {"name": PKG_IN_DB,"branch": BRANCH_NOT_IN_DB, "edition": EDITION_IN_DB, "type": IMAGE_TYPE_IN_DB, "status_code": 400},
        {"name": PKG_IN_DB,"branch": BRANCH_IN_DB, "edition": EDITION_NOT_IN_DB, "type": IMAGE_TYPE_IN_DB, "status_code": 400},
        {"name": PKG_IN_DB,"branch": BRANCH_IN_DB, "edition": EDITION_IN_DB, "type": IMAGE_TYPE_NOT_IN_DB, "status_code": 400},
    ],
)
def test_package_versions_from_images(client, kwargs):
    params = {}
    for k, v in kwargs.items():
        if k in ("status_code",):
            continue
        if v is not None:
            params[k] = v
    url = url_for("api.site_route_package_versions_from_images")
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["length"] != 0
        assert data["versions"] != []
        for version in data["versions"]:
            assert all([el != "" for el in version.values()])
