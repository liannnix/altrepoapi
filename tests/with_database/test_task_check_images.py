import re

from operator import itemgetter
from itertools import chain
from typing import Union

import pytest
from flask import url_for


@pytest.mark.parametrize(
    "kwargs",
    [
        # simple tasks tests
        {"payload": {"task_id": 100000}, "status_code": 400},
        {"payload": {"task_id": 234803}, "status_code": 404},
        {"payload": {"task_id": 326841}, "status_code": 200},
        {"payload": {"task_id": 312990}, "status_code": 200},
        {"payload": {"task_id": 317847}, "status_code": 200},
        {"payload": {"task_id": 324379}, "status_code": 200},
        # test "packages_names" filter
        {
            "payload": {
                "task_id": 312990,
                "packages_names": [
                    "plasma5-kwin-common",
                    "libkwin5",
                    "libplasmapotdprovidercore0",
                ],
            },
            "status_code": 200,
        },
        # test "editions" filter
        {
            "payload": {
                "task_id": 312990,
                "filters": [
                    {
                        "editions": ["blahblahblah"],
                    },
                ],
            },
            "status_code": 400,
        },
        {
            "payload": {
                "task_id": 312990,
                "filters": [
                    {
                        "editions": [],
                    },
                ],
            },
            "status_code": 200,
        },
        {
            "payload": {
                "task_id": 312990,
                "filters": [
                    {
                        "editions": ["alt-kworkstation"],
                    },
                ],
            },
            "status_code": 200,
        },
        {
            "payload": {
                "task_id": 312990,
                "filters": [
                    {
                        "editions": ["alt-server", "alt-workstation"],
                    },
                ],
            },
            "status_code": 200,
        },
        # test "releases" filter
        {
            "payload": {
                "task_id": 312990,
                "filters": [
                    {
                        "releases": ["blahblahblah"],
                    },
                ],
            },
            "status_code": 400,
        },
        {
            "payload": {
                "task_id": 312990,
                "filters": [
                    {
                        "releases": [],
                    },
                ],
            },
            "status_code": 200,
        },
        {
            "payload": {
                "task_id": 312990,
                "filters": [
                    {
                        "releases": ["release"],
                    },
                ],
            },
            "status_code": 200,
        },
        {
            "payload": {
                "task_id": 312990,
                "filters": [
                    {
                        "releases": ["release", "beta"],
                    },
                ],
            },
            "status_code": 200,
        },
        # test "versions" filter
        {
            "payload": {
                "task_id": 312990,
                "filters": [
                    {
                        "versions": ["blahblahblah"],
                    },
                ],
            },
            "status_code": 400,
        },
        {
            "payload": {
                "task_id": 312990,
                "filters": [
                    {
                        "versions": [],
                    },
                ],
            },
            "status_code": 200,
        },
        {
            "payload": {
                "task_id": 312990,
                "filters": [
                    {
                        "versions": ["10"],
                    },
                ],
            },
            "status_code": 200,
        },
        {
            "payload": {
                "task_id": 312990,
                "filters": [
                    {
                        "versions": ["10.1.0", "10.0"],
                    },
                ],
            },
            "status_code": 200,
        },
        # test "archs" filter
        {
            "payload": {
                "task_id": 312990,
                "filters": [
                    {
                        "archs": ["blahblahblah"],
                    },
                ],
            },
            "status_code": 400,
        },
        {
            "payload": {
                "task_id": 312990,
                "filters": [
                    {
                        "archs": [],
                    },
                ],
            },
            "status_code": 200,
        },
        {
            "payload": {
                "task_id": 312990,
                "filters": [
                    {
                        "archs": ["x86_64"],
                    },
                ],
            },
            "status_code": 200,
        },
        {
            "payload": {
                "task_id": 312990,
                "filters": [
                    {
                        "archs": ["x86_64", "aarch64"],
                    },
                ],
            },
            "status_code": 200,
        },
        # test "variants" filter
        {
            "payload": {
                "task_id": 312990,
                "filters": [
                    {
                        "variants": ["blahblahblah"],
                    },
                ],
            },
            "status_code": 400,
        },
        {
            "payload": {
                "task_id": 312990,
                "filters": [
                    {
                        "variants": [],
                    },
                ],
            },
            "status_code": 200,
        },
        {
            "payload": {
                "task_id": 312990,
                "filters": [
                    {
                        "variants": ["install"],
                    },
                ],
            },
            "status_code": 200,
        },
        {
            "payload": {
                "task_id": 312990,
                "filters": [
                    {
                        "variants": ["install", "live"],
                    },
                ],
            },
            "status_code": 200,
        },
        # test "types" filter
        {
            "payload": {
                "task_id": 312990,
                "filters": [
                    {
                        "types": ["blahblahblah"],
                    },
                ],
            },
            "status_code": 400,
        },
        {
            "payload": {
                "task_id": 312990,
                "filters": [
                    {
                        "types": [],
                    },
                ],
            },
            "status_code": 200,
        },
        {
            "payload": {
                "task_id": 312990,
                "filters": [
                    {
                        "types": ["iso"],
                    },
                ],
            },
            "status_code": 200,
        },
        {
            "payload": {
                "task_id": 312990,
                "filters": [
                    {
                        "types": ["iso", "img"],
                    },
                ],
            },
            "status_code": 200,
        },
        # test complex filter
        {
            "payload": {
                "task_id": 324379,
                "packages_names": [
                    "plasma5-disks",
                    "plasma5-systemmonitor",
                ],
                "filters": [
                    {
                        "editions": ["alt-kworkstation", "slinux"],
                        "releases": ["release"],
                        "versions": ["10", "10.1"],
                        "archs": ["x86_64", "armh"],
                        "variants": ["install", "live"],
                        "types": ["iso", "img"],
                    },
                ],
            },
            "status_code": 200,
        },
        # test unknown filter
        {
            "payload": {
                "task_id": 324379,
                "filters": [
                    {
                        "eedishnz": ["alt-kworkstation", "slinux"],
                    },
                ],
            },
            "status_code": 400,
        },
    ],
)
def test_task_check_images(client, kwargs):
    tag_fields = itemgetter(
        "branch",
        "edition",
        "flavor",
        "platform",
        "release",
        "major_version",
        "minor_version",
        "sub_version",
        "arch",
        "variant",
        "type",
    )

    def maketag(img: dict[str, Union[str, int]]) -> str:
        fields = tag_fields(img)
        release = ".".join([fields[4], *map(str, fields[5:8])])
        return ":".join([e for e in chain(fields[:4], [release], fields[8:])])

    def extractarch(
        rpmfilename: str, name: str, version: str, release: str
    ) -> Union[None, str]:
        pattern = re.compile(rf"{name}-{version}-{release}\.(\S+)\.rpm")
        return pattern.search(rpmfilename).groups()[0]

    def matchesfilter(
        i: dict[str, Union[int, str]], f: dict[str, list[Union[int, str]]]
    ) -> bool:
        return all(
            [
                i[field] in f[field + "s"] if f.get(field + "s", []) else True
                for field in [
                    "edition",
                    "flavor",
                    "platform",
                    "release",
                    "version",
                    "arch",
                    "variant",
                    "type",
                ]
            ]
        )

    url = url_for("api.task_route_check_images")
    response = client.post(url, json=kwargs["payload"], content_type="application/json")
    data = response.json
    assert response.status_code == kwargs["status_code"]

    if response.status_code == 200:
        url_find_images = url_for(
            "api.task_route_find_images", id=kwargs["payload"]["task_id"]
        )
        response_find_images = client.get(url_find_images)
        assert response_find_images.status_code == 200
        data_find_images = response_find_images.json

        url_task_info = url_for(
            "api.task_route_task_info", id=kwargs["payload"]["task_id"]
        )
        response_task_info = client.get(url_task_info)
        assert response_task_info.status_code == 200
        data_task_info = response_task_info.json

        plan = {
            "add": {
                "src": {el["name"] for el in data_task_info["plan"]["add"]["src"]},
                "bin": {
                    (
                        el["name"],
                        extractarch(
                            el["filename"], el["name"], el["version"], el["release"]
                        ),
                    )
                    for el in data_task_info["plan"]["add"]["bin"]
                },
            },
            "del": {
                "src": {el["name"] for el in data_task_info["plan"]["del"]["src"]},
                "bin": {
                    (
                        el["name"],
                        extractarch(
                            el["filename"], el["name"], el["version"], el["release"]
                        ),
                    )
                    for el in data_task_info["plan"]["del"]["bin"]
                },
            },
        }

        assert data
        assert data["request_args"]
        assert "in_images" in data
        assert "not_in_images" in data

        for img in data["in_images"]:
            if kwargs.get("filters", []):
                img["version"] = ".".join(
                    [
                        *img.get("major_version", []),
                        *img.get("minor_version", []),
                        *img.get("sub_version", []),
                    ]
                )
                assert any([matchesfilter(img, filter) for filter in kwargs["filters"]])

            assert img["packages"]
            for pkg in img["packages"]:
                assert pkg["status"]
                assert pkg["status"] in ("built", "deleted")
                assert pkg["binpkg_name"]
                assert pkg["binpkg_arch"]

                if kwargs["payload"].get("packages_names"):
                    assert pkg["binpkg_name"] in kwargs["payload"]["packages_names"]

                if pkg["binpkg_arch"] == "x86_64-i586":
                    assert not pkg["from_subtask"]
                    assert not pkg["srcpkg_name"]
                    assert pkg["binpkg_name"].startswith("i586-")
                else:
                    assert pkg["from_subtask"] > 0
                    assert pkg["srcpkg_name"]
                    assert not pkg["binpkg_name"].startswith("i586-")

                if pkg["binpkg_arch"] == "x86_64-i586":
                    continue

                assert data_find_images["subtasks"]
                subtasks = [
                    s
                    for s in data_find_images["subtasks"]
                    if s["id"] == pkg["from_subtask"]
                ]
                assert len(subtasks) == 1
                subtask = subtasks[0]

                assert pkg["srcpkg_name"] == subtask["srpm_name"]
                if pkg["status"] == "built":
                    assert subtask["type"] != "delete"
                    if subtask["type"] != "rebuild":
                        assert pkg["srcpkg_name"] in plan["add"]["src"]
                    assert (pkg["binpkg_name"], pkg["binpkg_arch"]) in plan["add"][
                        "bin"
                    ]
                else:
                    assert subtask["type"] == "delete"
                    assert pkg["srcpkg_name"] in plan["del"]["src"]
                    assert (pkg["binpkg_name"], pkg["binpkg_arch"]) in plan["del"][
                        "bin"
                    ]

                if img["buildtime"] >= data_find_images["task_changed"]:
                    continue

                assert subtask["images"]
                images = [i for i in subtask["images"] if i["filename"] == img["file"]]
                assert images

                for image in images:
                    assert maketag(img) == image["tag"]

                assert (pkg["binpkg_name"], pkg["binpkg_arch"]) in [
                    (image["binpkg_name"], image["binpkg_arch"]) for image in images
                ]

        for pkg in data["not_in_images"]:
            if kwargs["payload"].get("packages_names"):
                assert pkg["binpkg_name"] in kwargs["payload"]["packages_names"]

            if pkg["binpkg_arch"] != "x86_64-i586":
                assert data_task_info["subtasks"]
                subtasks = [
                    s
                    for s in data_task_info["subtasks"]
                    if s["subtask_id"] == pkg["from_subtask"]
                ]
                assert len(subtasks) == 1
                subtask = subtasks[0]

                if subtask["type"] == "delete":
                    assert pkg["srcpkg_name"] == subtask["package"]
                    assert pkg["srcpkg_name"] in plan["del"]["src"]
                    assert (pkg["binpkg_name"], pkg["binpkg_arch"]) in plan["del"][
                        "bin"
                    ]
                elif subtask["type"] == "rebuild":
                    assert pkg["srcpkg_name"] == subtask["package"]
                    assert (pkg["binpkg_name"], pkg["binpkg_arch"]) in plan["add"][
                        "bin"
                    ]
                else:
                    assert pkg["srcpkg_name"] == subtask["source_package"]["name"]
                    assert pkg["srcpkg_name"] in plan["add"]["src"]
                    assert (pkg["binpkg_name"], pkg["binpkg_arch"]) in plan["add"][
                        "bin"
                    ]
                    if pkg["binpkg_arch"] != "noarch":
                        assert (pkg["binpkg_arch"], pkg["status"]) in [
                            (a["arch"], a["status"]) for a in subtask["archs"]
                        ]
