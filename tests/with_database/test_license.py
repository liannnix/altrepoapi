import pytest
from flask import url_for

from altrepo_api.api.license.endpoints.license import parse_license_tokens


@pytest.mark.parametrize(
    "test_input,expected",
    [
        (
            {
                "licenses_str": "BSD",
                "aliases": {"BSD": "BSD-3_Clause"},
                "spdx_ids": {"BSD-3_Clause", "BSD-4_Clause"},
            },
            {"BSD": "BSD-3_Clause"}
        ),
        (
            {
                "licenses_str": "MIT",
                "aliases": {"BSD": "BSD-3_Clause", "MIT": "MIT"},
                "spdx_ids": {"BSD-3_Clause", "BSD-4_Clause"},
            },
            {"MIT": "MIT"}
        ),
        (
            {
                "licenses_str": "MIT",
                "aliases": {"BSD": "BSD-3_Clause"},
                "spdx_ids": {"BSD-3_Clause", "BSD-4_Clause", "MIT"},
            },
            {"MIT": "MIT"}
        ),
        (
            {
                "licenses_str": "modified BSD",
                "aliases": {"BSD": "BSD-3_Clause"},
                "spdx_ids": {"BSD-3_Clause", "BSD-4_Clause"},
            },
            {}
        ),
    ],
)
def test_pkg_name_type(test_input, expected):
    assert parse_license_tokens(**test_input) == expected


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "license": "LGPLv2",
            "status_code": 200
        },
        {
            "license": "GPLv3+ and (MIT or BSD)",
            "status_code": 200
        },
        {
            "license": "modified BSD",
            "status_code": 404
        },
        {
            "license": "not-a-license",
            "status_code": 404
        },
        {
            "license": "!invalid_license$",
            "status_code": 400
        },
    ]
)
def test_license_tokens(client, kwargs):
    params = {k: v for k, v in kwargs.items() if k != "status_code"}

    url = url_for("api.license_route_license_tokens")
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["length"] != 0
        assert data["tokens"] != []


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "license": "LGPL-3.0",
            "status_code": 200
        },
        {
            "license": "BSD",
            "status_code": 200
        },
        {
            "license": "LGPL-3.0-linking-exception",
            "status_code": 200
        },
        {
            "license": "LGPLv3+",
            "status_code": 200
        },
        {
            "license": "not-a-license",
            "status_code": 404
        },
        {
            "license": "!invalid license$",
            "status_code": 400
        },
    ]
)
def test_license_infor(client, kwargs):
    params = {k: v for k, v in kwargs.items() if k != "status_code"}

    url = url_for("api.license_route_license_info")
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["id"] != ""
        assert data["name"] != ""
        assert data["text"] != ""
        assert data["type"] in ("license", "exception")
        assert "header" in data
        assert "comment" in data
        assert data["urls"] != []
