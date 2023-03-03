import pytest
from flask import url_for


# the data is taken from git.altlinux.org/tasks/{id}
@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "task_id": 299031,
            "task_state": "DONE",
            "task_testonly": 0,
            "task_repo": "sisyphus",
            "task_owner": "ldv",
            "task_try": 7,
            "task_iter": 3,
            "task_message": "update gnulib and its dependencies",
            "task_changed": "2022-04-28T17:00:42",
            "dependencies": [],
            "subtasks": [
                {
                    "id": 1500,
                    "type": "rebuild",
                    "srpm_name": "tar",
                    "srpm_hash": "2673889282892285332",
                    "pkg_version": "1.34.0.16.12d67f44",
                    "pkg_release": "alt1",
                    "binpkgs_names": [
                        "tar",
                    ],
                },
                {
                    "id": 1040,
                    "type": "gear",
                    "srpm_name": "coreutils",
                    "srpm_hash": "2793915567944400253",
                    "pkg_version": "9.1.0.8.e08752",
                    "pkg_release": "alt1",
                    "binpkgs_names": [
                        "coreutils"
                    ],
                },
            ],
            "iterations": [
                {"task_try": 7, "task_iter": 3},
                {"task_try": 6, "task_iter": 1},
                {"task_try": 5, "task_iter": 1},
                {"task_try": 4, "task_iter": 1},
                {"task_try": 3, "task_iter": 1},
                {"task_try": 2, "task_iter": 1},
                {"task_try": 1, "task_iter": 1},
            ],
            "status_code": 200,
        },
        {
            "task_id": 312990,
            "task_state": "DONE",
            "task_testonly": 0,
            "task_repo": "p10",
            "task_owner": "ancieg",
            "task_try": 7,
            "task_iter": 1,
            "task_message": "build_racket_in_another_way",
            "task_changed": "2023-02-07T10:17:29",
            "dependencies": [],
            "subtasks": [
                {
                    "id": 1000,
                    "type": "srpm",
                    "srpm_name": "lash",
                    "srpm_hash": "2885657235453605498",
                    "pkg_version": "0.5.4",
                    "pkg_release": "alt1_49",
                    "binpkgs_names": [
                        "liblash"
                    ],
                },
            ],
            "iterations": [
                {"task_try": 7, "task_iter": 1},
                {"task_try": 6, "task_iter": 1},
                {"task_try": 5, "task_iter": 1},
                {"task_try": 4, "task_iter": 1},
                {"task_try": 3, "task_iter": 1},
                {"task_try": 2, "task_iter": 1},
                {"task_try": 1, "task_iter": 1},
            ],
            "status_code": 200,
        },
        {
            "task_id": 314136,
            "task_state": "DONE",
            "task_testonly": 0,
            "task_repo": "p10",
            "task_owner": "zerg",
            "task_try": 3,
            "task_iter": 1,
            "task_message": "update",
            "task_changed": "2023-02-11T03:02:07",
            "dependencies": [],
            "subtasks": [
                {
                    "id": 100,
                    "type": "gear",
                    "srpm_name": "nvidia_glx_common",
                    "srpm_hash": "2897575501802780949",
                    "pkg_version": "525.85.05",
                    "pkg_release": "alt260",
                    "binpkgs_names": [
                        "nvidia_glx_common",
                        "i586-nvidia_glx_common"
                    ],
                },
            ],
            "iterations": [
                {"task_try": 3, "task_iter": 1},
                {"task_try": 2, "task_iter": 1},
                {"task_try": 1, "task_iter": 1},
            ],
            "status_code": 200,
        },
        {
            "task_id": 274287,
            "task_state": "DONE",
            "task_testonly": 0,
            "task_repo": "p9",
            "task_owner": "rider",
            "task_try": 4,
            "task_iter": 1,
            "task_message": "new version is needed for apache FTBFS",
            "task_changed": "2021-06-17T18:21:13",
            "dependencies": [],
            "subtasks": [
                {
                    "id": 200,
                    "type": "gear",
                    "srpm_name": "zabbix",
                    "srpm_hash": "2677545995485572429",
                    "pkg_version": "5.0.12",
                    "pkg_release": "alt0.p9.1",
                    "binpkgs_names": [
                        "zabbix-agent",
                        "zabbix-agent-sudo",
                        "zabbix-common",
                    ],
                },
            ],
            "iterations": [
                {"task_try": 4, "task_iter": 1},
            ],
            "status_code": 200,
        },
        {
            "task_id": 234803,
            "task_state": "POSTPONED",
            "task_testonly": 0,
            "task_repo": "p8",
            "task_owner": "imz",
            "task_try": 1,
            "task_iter": 1,
            "task_message": "",
            "task_changed": "2019-07-18T05:25:59",
            "dependencies": [
                234804
            ],
            "subtask": [
                # the task is "dead", so this field is empty
            ],
            "iterations": [
                {"task_try": 2, "task_iter": 1},
            ],
            "status_code": 404,
        },
        {
            "task_id": 103854,
            "task_state": "DONE",
            "task_testonly": 0,
            "task_repo": "sisyphus",
            "task_owner": "real",
            "task_try": 2,
            "task_iter": 1,
            "task_message": "",
            "task_changed": "2013-09-11T07:54:21",
            "dependencies": [],
            "subtasks": [],
            "iterations": [],
            # no images for the task
            "status_code": 200,
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

        for field in (
            "task_id",
            "task_state",
            "task_testonly",
            "task_repo",
            "task_owner",
            "task_try",
            "task_iter",
            "task_message",
            "task_changed",
            "dependencies"
        ):
            assert data[field] == kwargs[field]

        subtasks = data["subtasks"]

        for test_subtask in kwargs["subtasks"]:
            fields = [
                  "id",
                  "type",
                  "srpm_name",
                  "srpm_hash",
                  "pkg_version",
                  "pkg_release"
            ]
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
                    branch=kwargs["task_repo"],
                    pkg_name=binpkg_name,
                    pkg_type="binary",
                    img_show="active",
                )
                resp = client.get(url)
                assert resp.status_code == 200
                resp = resp.json

                images_from_response = {
                    tuple(img.values())
                    for img in subtask["images"]
                    if img["binpkg_name"] == binpkg_name
                }

                if data["task_state"] == "DONE":
                    resp["images"] = list(filter(
                        lambda entry: entry["date"] <= data["task_changed"], resp["images"]
                    ))

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
                    for image in resp["images"]
                }

                assert images_from_response == images_from_testdata
