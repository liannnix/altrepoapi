import pytest
from flask import url_for


# the data is taken from git.altlinux.org/tasks/{id}
@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "task_id": 299031,
            "task_state": "DONE",
            "task_branch": "sisyphus",
            "task_try": 7,
            "task_iter": 3,
            "task_message": "update gnulib and its dependencies",
            "subtasks": [
                {
                    "id": 1500,
                    "type": "build",
                    "srcpkg_name": "tar",
                    "srcpkg_version": "1.34.0.16.12d67f44",
                    "srcpkg_release": "alt1",
                    "binpkgs_names": [
                        "tar",
                    ],
                },
                {
                    "id": 1040,
                    "type": "build",
                    "srcpkg_name": "coreutils",
                    "srcpkg_version": "9.1.0.8.e08752",
                    "srcpkg_release": "alt1",
                    "binpkgs_names": [
                        "coreutils"
                    ],
                },
            ],
            "arepo": [],
            "status_code": 200,
        },
        {
            "task_id": 312990,
            "task_state": "DONE",
            "task_branch": "p10",
            "task_try": 7,
            "task_iter": 1,
            "task_message": "build_racket_in_another_way",
            "subtasks": [
                {
                    "id": 1000,
                    "type": "build",
                    "srcpkg_name": "lash",
                    "srcpkg_version": "0.5.4",
                    "srcpkg_release": "alt1_49",
                    "binpkgs_names": [
                        "liblash"
                    ],
                },
            ],
            "arepo": [],
            "status_code": 200,
        },
        {
            "task_id": 314136,
            "task_state": "DONE",
            "task_branch": "p10",
            "task_try": 3,
            "task_iter": 1,
            "task_message": "update",
            "subtasks": [
                {
                    "id": 100,
                    "type": "build",
                    "srcpkg_name": "nvidia_glx_common",
                    "srcpkg_version": "525.85.05",
                    "srcpkg_release": "alt260",
                    "binpkgs_names": [
                        "nvidia_glx_common"
                    ],
                },
            ],
            "arepo": [
                {
                    "type": "build",
                    "binpkg_name": "i586-nvidia_glx_common",
                    "binpkg_version": "525.85.05",
                    "binpkg_release": "alt260",
                    "binpkg_arch": "x86_64-i586",
                    "binpkgs_names": [
                        "i586-nvidia_glx_common",
                    ],
                },
            ],
            "status_code": 200,
        },
        {
            "task_id": 274287,
            "task_state": "DONE",
            "task_branch": "p9",
            "task_try": 4,
            "task_iter": 1,
            "task_message": "new version is needed for apache FTBFS",
            "subtasks": [
                {
                    "id": 200,
                    "type": "build",
                    "srcpkg_name": "zabbix",
                    "srcpkg_version": "5.0.12",
                    "srcpkg_release": "alt0.p9.1",
                    "binpkgs_names": [
                        "zabbix-agent",
                        "zabbix-agent-sudo",
                        "zabbix-common",
                    ],
                },
            ],
            "arepo": [],
            "status_code": 200,
        },
        {
            "task_id": 234803,
            "task_state": "POSTPONED",
            "task_branch": "p8",
            "task_try": 1,
            "task_iter": 1,
            "task_message": "",
            "subtask": [
                # the task is "dead", so this field is empty
            ],
            "arepo": [],
            "status_code": 404,
        },
        {
            # too old task which isn't in altrepodb
            "task_id": 103854,
            "arepo": [],
            "status_code": 404,
        },
    ],
)
def test_find_images_by_task(client, kwargs):
    def gather(container, keys):
        return tuple(container[key] for key in keys)

    url = url_for(
        "api.task_route_find_images", id=kwargs["task_id"]
    )
    response = client.get(url)
    assert response.status_code == kwargs["status_code"]

    data = response.json

    if response.status_code == 200:
        assert data != {}
        assert data["subtasks"] != []

        for field in (
            "task_id",
            "task_state",
            "task_branch",
            "task_try",
            "task_iter",
            "task_message",
        ):
            assert data[field] == kwargs[field]

        subtasks = data["subtasks"]
        arepos = data["arepo"]

        for test_subtask in kwargs["subtasks"]:
            fields = ["id", "type", "srcpkg_name", "srcpkg_version", "srcpkg_release"]
            subtasks_metas = [gather(subtask, fields) for subtask in subtasks]
            assert gather(test_subtask, fields) in subtasks_metas

            for sub in subtasks:
                if sub["id"] == test_subtask["id"]:
                    subtask = sub

            subtask_all_binpkgs_names = {
                img["binpkg_name"] for img in subtask["images"]
            }

            assert {*test_subtask["binpkgs_names"]} == subtask_all_binpkgs_names

            for binpkg_name in subtask_all_binpkgs_names:
                url = url_for(
                    "api.image_route_find_images_by_package",
                    branch=kwargs["task_branch"],
                    pkg_name=binpkg_name,
                    pkg_type="binary",
                    img_show="active",
                )
                resp = client.get(url)
                assert resp.status_code == 200

                images_from_response = {
                    tuple(img.values())
                    for img in subtask["images"]
                    if img["binpkg_name"] == binpkg_name
                }

                images_from_testdata = {
                    gather(
                        image,
                        [
                            "file",
                            "edition",
                            "tag",
                            "date",
                            "name",
                            "version",
                            "release",
                            "arch",
                            "pkghash"
                        ]
                    )
                    for image in resp.json["images"]
                }

                assert images_from_response == images_from_testdata

        for test_arepo in kwargs["arepo"]:
            fields = [
                "type",
                "binpkg_name",
                "binpkg_version",
                "binpkg_release",
                "binpkg_arch"
            ]
            arepo_metas = [gather(arepo, fields) for arepo in arepos]
            assert gather(test_arepo, fields) in arepo_metas

            for arp in arepos:
                if arp["binpkg_name"] == test_arepo["binpkg_name"]:
                    arepo = arp

            arepo_all_binpkgs_names = {
                arp["binpkg_name"] for arp in arepo["images"]
            }

            assert {*test_arepo["binpkgs_names"]} == arepo_all_binpkgs_names

            for binpkg_name in arepo_all_binpkgs_names:
                url = url_for(
                    "api.image_route_find_images_by_package",
                    branch=kwargs["task_branch"],
                    pkg_name=binpkg_name,
                    pkg_type="binary",
                    img_show="active"
                )
                resp = client.get(url)
                assert resp.status_code == 200

                images_from_response = {
                    tuple(img.values())
                    for img in arepo["images"]
                    if img["binpkg_name"] == binpkg_name
                }

                images_from_testdata = {
                    gather(
                        image,
                        [
                            "file",
                            "edition",
                            "tag",
                            "date",
                            "name",
                            "version",
                            "release",
                            "arch",
                            "pkghash"
                        ]
                    )
                    for image in resp.json["images"]
                }

                assert images_from_response == images_from_testdata
