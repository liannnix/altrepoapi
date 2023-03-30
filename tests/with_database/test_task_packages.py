import pytest
from flask import url_for


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "id": 310327,
            "repo": "p10",
            "owner": "cas",
            "state": "DONE",
            "testonly": 0,
            "try": 27,
            "iter": 1,
            "message": "New_version",
            "dependencies": [],
            "length": 14,
            "subtasks": [
                100,
                200,
                220,
                260,
                400,
                500,
                600,
                1300,
                1400,
                2500,
                2600,
                2700,
                3400,
                4100,
            ],
            "sources": [
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
                "qt6-webengine",
            ],
            "arepo": ["i586-libuv", "i586-libuv-devel", "i586-ocaml-luv"],
            "status_code": 200,
        },
        {
            "id": 312990,
            "repo": "p10",
            "owner": "ancieg",
            "state": "DONE",
            "testonly": 0,
            "try": 7,
            "iter": 1,
            "message": "build_racket_in_another_way",
            "dependencies": [],
            "length": 6,
            "subtasks": [100, 140, 500, 600, 700, 1000],
            "sources": [
                "lash",
                "racket-core",
                "racket-main",
                "rpm-macros-racket",
                "swig",
                "zuo",
            ],
            "arepo": ["i586-liblash", "i586-liblash-devel"],
            "status_code": 200,
        },
        {
            "id": 1,
            "status_code": 404,
        },
    ],
)
def test_task_packages(client, kwargs):
    def check_package_fields(package):
        fields = set(package.keys())
        return fields == {
            "name",
            "epoch",
            "version",
            "release",
            "disttag",
            "buildtime",
            "arch",
        }

    url = url_for("api.task_route_task_packages", id=kwargs["id"])
    response = client.get(url)
    assert response.status_code == kwargs["status_code"]

    data = response.json

    if response.status_code == 200:
        assert data != {}

        for field in [
            "id",
            "repo",
            "owner",
            "state",
            "testonly",
            "try",
            "iter",
            "message",
            "length",
        ]:
            assert data[field] == kwargs[field]
        assert sorted(data["dependencies"]) == sorted(kwargs["dependencies"])

        assert data["subtasks"] != []

        for subtask in data["subtasks"]:
            assert subtask["subtask"] in kwargs["subtasks"]
            assert check_package_fields(subtask["source"])
            assert subtask["source"]["arch"] == ""
            for binary in subtask["binaries"]:
                assert check_package_fields(binary)
                assert binary["arch"] != ""

        for arepo in data["arepo"]:
            check_package_fields(arepo)
            assert arepo["arch"] == "x86_64-i586"
            assert arepo["name"].startswith("i586-")
            assert arepo["name"] in kwargs["arepo"]
