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
        {"branches": ["c10f1"], "group": "maint", "status_code": 200},
        {"branches": ["c9f1"], "group": "tester", "status_code": 200},
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
            for field in task_fields:
                assert task[field] is not None

            assert task["state"] == "EPERM"
            assert task["testonly"] is False
            assert task["branch"] in kwargs["branches"]

            for subtask in task["subtasks"]:
                for field in subtask_fields:
                    assert subtask[field] is not None

                source_package = subtask["source_package"]
                for field in source_package_fields:
                    assert source_package[field] is not None
