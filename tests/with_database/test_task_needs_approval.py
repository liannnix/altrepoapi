import pytest
from flask import url_for


# the data is taken from git.altlinux.org/tasks/{id}
@pytest.mark.parametrize(
    "kwargs",
    [
        {"branches": ["p10"], "group": "maint", "status_code": 200},
        {"branches": ["p10"], "group": "tester", "status_code": 200},
        {"branches": ["p9"], "group": "maint", "status_code": 200},
        {"branches": ["p9"], "group": "tester", "status_code": 200},
        {"branches": ["p8"], "group": "tester", "status_code": 200},
        {"branches": ["p7"], "group": "maint", "status_code": 400},
        {"branches": ["p7"], "group": "tester", "status_code": 400},
        {"branches": ["c9f2"], "group": "maint", "status_code": 200},
        {"branches": ["c9f2"], "group": "tester", "status_code": 200},
        {"branches": ["c9f1"], "group": "maint", "status_code": 400},
        {"branches": ["c9f1"], "group": "tester", "status_code": 400},
    ],
)
def test_needs_approval(client, kwargs):
    url = url_for(
        "api.task_route_needs_approval",
        branches=kwargs["branches"],
        acl_group=kwargs["group"],
    )
    response = client.get(url)
    assert response.status_code == kwargs["status_code"]

    data = response.json

    task_fields = [
        "id",
        "state",
        "runby",
        "try",
        "iter",
        "failearly",
        "shared",
        "depends",
        "testonly",
        "message",
        "version",
        "prev",
        "last_changed",
        "branch",
        "user",
    ]

    subtask_fields = [
        "type",
        "package",
        "userid",
        "dir",
        "sid",
        "pkg_from",
        "tag_author",
        "tag_id",
        "tag_name",
        "srpm",
        "srpm_name",
        "srpm_evr",
        "last_changed",
    ]

    source_package_fields = ["name", "version", "release", "filename"]

    if response.status_code == 200:
        assert data != {}
        assert data["length"] == len(data["tasks"])

        for task in data["tasks"]:
            url = url_for("api.task_route_task_info", id=task["id"])
            task_info_response = client.get(url)

            assert task_info_response.status_code == 200
            task_info = task_info_response.json

            assert task["state"] == "EPERM"
            assert task["testonly"] is False
            assert task["branch"] in kwargs["branches"]

            for field in task_fields:
                assert task[field] == task_info[field]

            assert len(task["subtasks"]) == len(task_info["subtasks"])

            for subtask in task["subtasks"]:
                for sub in task_info["subtasks"]:
                    if sub["subtask_id"] == subtask["id"]:
                        subtask_info = sub

                assert subtask["id"] == subtask_info["subtask_id"]

                for field in subtask_fields:
                    assert subtask[field] == subtask_info[field]

                for field in source_package_fields:
                    assert (
                        subtask["source_package"][field]
                        in (subtask_info["source_package"][field], '')
                    )
