import pytest
from flask import url_for

BRANCH_IN_DB = ["p9", "p10", "4.0"]
BRANCH_NOT_DB = "abc"
ROOT_UUID_VALID = "76958932-e135-45f4-98ff-673d0fd017a2"
COMPONENT_UUID_VALID = "a1cc3d26-4606-4230-aee0-115ff7bc2975"
UUID_VALID = "a2a5645b-1d71-40b9-958c-d5a79b2260dd"
UUID_NOT_VALID = "00000-0000-0000-0000-000000000000"
UUID_NOT_DB = "00000000-0000-0000-0000-000000000000"
CATEGORY_VALID = "Security/Networking"
CATEGORY_NOT_DB = "Security/Abcd"


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "branch": BRANCH_IN_DB[0],
            "edition": "slinux",
            "version": None,
            "release": None,
            "variant": None,
            "arch": None,
            "flavor": None,
            "component": None,
            "type": None,
            "status_code": 200
        },
        {
            "branch": BRANCH_IN_DB[0],
            "edition": 'cloud',
            "version": "9.2.0",
            "release": "release",
            "variant": "install",
            "arch": "x86_64",
            "flavor": "workstation",
            "component": None,
            "type": "qcow",
            "status_code": 200
        },
        {
            "branch": BRANCH_NOT_DB,
            "edition": "slinux",
            "version": None,
            "release": None,
            "variant": None,
            "arch": None,
            "flavor": None,
            "component": None,
            "type": "zip",
            "status_code": 400
        },
        {
            "branch": BRANCH_IN_DB[1],
            "edition": 'slinux',
            "version": "10.0.0",
            "release": "release",
            "variant": None,
            "arch": "x86_64",
            "flavor": None,
            "component": None,
            "type": "img",
            "status_code": 404
        },
    ],
)
def test_image_info(client, kwargs):
    params = {k: v for k, v in kwargs.items() if k != "status_code"}

    url = url_for("api.image_route_image_info")
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["length"] != 0
        assert data["images"] != []


def test_image_status_get(client):
    url = url_for("api.image_route_image_status")
    response = client.get(url)
    data = response.json
    assert response.status_code == 200
    if response.status_code == 200:
        assert data != {}
        assert data["images"] != []
        for elem in data["images"]:
            assert elem["branch"] != ""
            assert elem["edition"] != ""
            assert elem["show"] == "hide" or elem["show"] == "show"


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "img_branch": BRANCH_IN_DB[0],
            "img_description_ru": "0YLQtdGB0YLQvtCy0L7QtSDQvtC/0LjRgdCw0L3QuNC1",
            "img_description_en": "dGVzdCBkZXNjcmlwdGlvbg==",
            "images": [
                {
                    "img_edition": "alt-kworkstation",
                    "img_name": "ALT-KWORKSTATION 9.2 x86_64",
                    "img_show": "hide",
                    "img_summary_ru": "Image summary in Russian",
                    "img_summary_en": "Image summary in English",
                    "img_start_date": "2022-03-10T14:26:43.284",
                    "img_end_date": "2022-03-10T14:26:43.284",
                    "img_mailing_list": "https://lists.altlinux.org/mailman/listinfo/devel-ports",
                    "img_name_bugzilla": "p9",
                    "img_json": {}
                }
            ]
        }
    ]
)
def test_image_status_post(client, kwargs):
    url = url_for("api.image_route_image_status")
    response = client.post(url, json=kwargs)
    assert response.status_code == 401


@pytest.mark.parametrize(
    "kwargs",
    [
        {"branch": BRANCH_IN_DB[1], "edition": "slinux", "status_code": 200},
        {"branch": BRANCH_IN_DB[0], "edition": "alt-kworkstation", "status_code": 200},
        {"branch": BRANCH_NOT_DB, "edition": "alt-kworkstation", "status_code": 400},
        {"branch": BRANCH_IN_DB[0], "edition": "test", "status_code": 400},
        {"branch": BRANCH_IN_DB[2], "edition": "alt-kworkstation", "status_code": 404},
    ]
)
def test_image_tag_status_get(client, kwargs):
    params = {k: v for k, v in kwargs.items() if k != "status_code"}

    url = url_for("api.image_route_image_tag_status")
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["tags"] != []
        for elem in data["tags"]:
            assert elem["show"] == "hide" or elem["show"] == "show"


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "tags": [
                {
                    "img_tag": "branch:edition:flavor:platform:release.ver_major.ver_minor.ver_sub:arch:variant:type",
                    "img_show": "hide"
                }
            ]
        }
    ]
)
def test_image_tag_status_post(client, kwargs):
    url = url_for("api.image_route_image_tag_status")
    response = client.post(url, json=kwargs)
    assert response.status_code == 401


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "uuid": ROOT_UUID_VALID,
            "packages_limit": 10,
            "component": False,
            "status_code": 200
        },
        {
            "uuid": ROOT_UUID_VALID,
            "packages_limit": 10,
            "component": True,
            "status_code": 404
        },
        {
            "uuid": COMPONENT_UUID_VALID,
            "packages_limit": 10,
            "component": False,
            "status_code": 404
        },
        {
            "uuid": COMPONENT_UUID_VALID,
            "packages_limit": 10,
            "component": True,
            "status_code": 200
        },
        {
            "uuid": UUID_NOT_VALID,
            "packages_limit": 10,
            "component": True,
            "status_code": 400
        },
        {
            "uuid": UUID_NOT_DB,
            "packages_limit": 10,
            "component": True,
            "status_code": 404
        },
    ]
)
def test_last_packages_by_image(client, kwargs):
    params = {k: v for k, v in kwargs.items() if k != "status_code"}

    url = url_for("api.image_route_last_image_packages")
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["packages"] != []
        assert len(data["packages"]) == kwargs["packages_limit"]


def test_all_images(client):
    url = url_for("api.image_route_all_iso_images")
    response = client.get(url)
    data = response.json
    assert response.status_code == 200
    if response.status_code == 200:
        assert data != {}
        assert data["images"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "tag": "p9:slinux::mcom02:release.9.1.0:armh:install:img",
            "status_code": 200
        },
        {
            "tag": "p5:slinux::mcom02:release.9.1.0:armh:install:img",
            "status_code": 404
        },
        {
            "tag": "p9:slinux:mcom02:release.9.1.0:install:img",
            "status_code": 404
        },
    ]
)
def test_image_uuid_by_tag(client, kwargs):
    params = {k: v for k, v in kwargs.items() if k != "status_code"}

    url = url_for("api.image_route_image_tag_uuid")
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["uuid"] != ""
        assert data["file"] != ""
        assert data["components"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "uuid": ROOT_UUID_VALID,
            "status_code": 200
        },
        {
            "uuid": ROOT_UUID_VALID,
            "component": "live",
            "status_code": 200
        },
        {
            "uuid": COMPONENT_UUID_VALID,
            "component": "live",
            "status_code": 404
        },
        {
            "uuid": ROOT_UUID_VALID,
            "component": "invalid",
            "status_code": 400
        },
        {
            "uuid": UUID_NOT_VALID,
            "component": "invalid",
            "status_code": 400
        },
    ]
)
def test_image_categories_count(client, kwargs):
    params = {k: v for k, v in kwargs.items() if k != "status_code"}

    url = url_for("api.image_route_image_categories_count")
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["categories"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "uuid": ROOT_UUID_VALID,
            "group": CATEGORY_VALID,
            "status_code": 200
        },
        {
            "uuid": ROOT_UUID_VALID,
            "group": CATEGORY_VALID,
            "component": "live",
            "status_code": 200
        },
        {
            "uuid": COMPONENT_UUID_VALID,
            "group": CATEGORY_VALID,
            "component": "live",
            "status_code": 404
        },
        {
            "uuid": ROOT_UUID_VALID,
            "group": CATEGORY_NOT_DB,
            "status_code": 400
        },
        {
            "uuid": UUID_NOT_VALID,
            "group": CATEGORY_VALID,
            "status_code": 400
        },
    ]
)
def test_image_packages(client, kwargs):
    params = {k: v for k, v in kwargs.items() if k != "status_code"}

    url = url_for("api.image_route_image_packages")
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["packages"] != []
