import pytest
from flask import url_for


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "task_id": 310327,
            "task_packages": [
                "gyp",
                "ocaml-luv",
                "libuv",
                "chromium-gost",
                "crystal-open",
                "node",
                "node-canvas",
                "node-nan",
                "node-nyc",
                "node-sass",
                "node-uglify-js",
                "npmjs-fibers",
                "npm",
                "qt6-webengine"
            ],
            "length": 14,
            "status_code": 200,
        },
        {
            "task_id": 312990,
            "task_packages": [
                "lash",
                "racket-core",
                "racket-main",
                "rpm-macros-racket",
                "swig",
                "zuo"
            ],
            "length": 6,
            "status_code": 200,
        },
        {
            "task_id": 1,
            "status_code": 404,
        },
    ],
)
def test_task_packages(client, kwargs):
    url = url_for(
        "api.task_route_task_packages", id=kwargs["task_id"]
    )
    response = client.get(url)
    assert response.status_code == kwargs["status_code"]

    data = response.json

    if response.status_code == 200:
        assert data != {}

        assert data["id"] == kwargs["task_id"]
        assert sorted(data["task_packages"]) == sorted(kwargs["task_packages"])
        assert data["length"] == kwargs["length"]
        assert data["packages"] != []

        for package in data["packages"]:
            assert package["sourcepkgname"] in kwargs["task_packages"]
            assert package["packages"] != []
            assert package["version"] != ""
            assert package["release"] != ""
            assert package["disttag"] != ""
            assert package["packager_email"] != ""
            assert package["buildtime"] != ""
            assert package["archs"] != []
