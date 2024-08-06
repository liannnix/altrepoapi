import pytest
from flask import url_for

VALID_ACCESS_TOKEN = "valid_token"
INVALID_ACCESS_TOKEN = "invalid_token"

AV_SCAN_PKG_NAME_IN_DB = "php8"
AV_SCAN_MESSAGE_IN_DB = "php8.2-8.2.15-alt1"
AV_SCAN_PKG_NAME_NOT_IN_DB = "php3"
AV_SCAN_VALID_BRANCH = "p10"
AV_SCAN_INVALID_BRANCH = "foo"
AV_SCAN_VALID_SCANNER = "kesl"
AV_SCAN_VALID_SCANNER2 = "drweb"
AV_SCAN_INVALID_SCANNER = "foo"
AV_SCAN_VALID_ISSUE = "Corrupted object"
AV_SCAN_VALID_ISSUE2 = "Read error"
AV_SCAN_INVALID_ISSUE = "foo"

AV_SCAN_IMG_NAME_IN_DB = "firmware"
AV_SCAN_IMG_MESSAGE_IN_DB = "firmware-linux"


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "input": None,
            "limit": 10,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": AV_SCAN_PKG_NAME_IN_DB,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": AV_SCAN_MESSAGE_IN_DB,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": AV_SCAN_PKG_NAME_NOT_IN_DB,
            "status_code": 404,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": AV_SCAN_PKG_NAME_IN_DB,
            "status_code": 401,
            "headers": {"Authorization": INVALID_ACCESS_TOKEN},
        },
        {
            "status_code": 200,
            "branch": AV_SCAN_VALID_BRANCH,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "status_code": 400,
            "branch": AV_SCAN_INVALID_BRANCH,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "status_code": 200,
            "scanner": AV_SCAN_VALID_SCANNER,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "status_code": 200,
            "scanner": AV_SCAN_VALID_SCANNER2,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "status_code": 404,
            "scanner": AV_SCAN_INVALID_SCANNER,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "status_code": 200,
            "issue": AV_SCAN_VALID_ISSUE,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "status_code": 404,
            "issue": AV_SCAN_INVALID_ISSUE,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "status_code": 200,
            "input": AV_SCAN_PKG_NAME_IN_DB,
            "branch": AV_SCAN_VALID_BRANCH,
            "scanner": AV_SCAN_VALID_SCANNER,
            "issue": "read error",
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": None,
            "limit": 10,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
    ],
)
def test_av_scan_pkg_list(client, kwargs, mocked_check_access_token):
    params = {k: v for k, v in kwargs.items() if k not in ("status_code", "headers")}
    url = url_for("manage.antivirus_scan_route_antivirus_scan_pkg_list")
    mocked_check_access_token.headers = kwargs.get("headers", {})
    mocked_check_access_token.status_code = kwargs["status_code"]
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["length"] != 0
        assert data["detections"] != []
        for detection in data["detections"]:
            if params.get("branch", ""):
                assert params["branch"] == detection["pkgset_name"]
            if params.get("scanner", ""):
                for scanner in [
                    info["av_scanner"] for info in detection["detect_info"]
                ]:
                    assert params["scanner"] == scanner
            if params.get("issue", ""):
                for issue in [info["av_issue"] for info in detection["detect_info"]]:
                    assert params["issue"] == issue
            if params.get("input", "") == AV_SCAN_PKG_NAME_IN_DB:
                assert params["input"] in detection["pkg_name"]
            if params.get("input", "") == AV_SCAN_MESSAGE_IN_DB:
                for msg in [info["av_message"] for info in detection["detect_info"]]:
                    assert params["input"] in msg
        if params.get("limit", ""):
            assert params["limit"] == data["length"]


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "input": None,
            "limit": 10,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": AV_SCAN_IMG_NAME_IN_DB,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": AV_SCAN_IMG_MESSAGE_IN_DB,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": AV_SCAN_PKG_NAME_NOT_IN_DB,
            "status_code": 404,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": AV_SCAN_IMG_NAME_IN_DB,
            "status_code": 401,
            "headers": {"Authorization": INVALID_ACCESS_TOKEN},
        },
        {
            "status_code": 200,
            "branch": AV_SCAN_VALID_BRANCH,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "status_code": 400,
            "branch": AV_SCAN_INVALID_BRANCH,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "status_code": 200,
            "scanner": AV_SCAN_VALID_SCANNER,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "status_code": 200,
            "scanner": AV_SCAN_VALID_SCANNER2,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "status_code": 404,
            "scanner": AV_SCAN_INVALID_SCANNER,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "status_code": 200,
            "issue": AV_SCAN_VALID_ISSUE2,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "status_code": 404,
            "issue": AV_SCAN_INVALID_ISSUE,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "status_code": 200,
            "input": AV_SCAN_IMG_NAME_IN_DB,
            "branch": AV_SCAN_VALID_BRANCH,
            "scanner": AV_SCAN_VALID_SCANNER2,
            "issue": "Read error",
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
        {
            "input": None,
            "limit": 10,
            "status_code": 200,
            "headers": {"Authorization": VALID_ACCESS_TOKEN},
        },
    ],
)
def test_av_scan_img_list(client, kwargs, mocked_check_access_token):
    params = {k: v for k, v in kwargs.items() if k not in ("status_code", "headers")}
    url = url_for("manage.antivirus_scan_route_antivirus_scan_img_list")
    mocked_check_access_token.headers = kwargs.get("headers", {})
    mocked_check_access_token.status_code = kwargs["status_code"]
    response = client.get(url, query_string=params)
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert data != {}
        assert data["length"] != 0
        assert data["detections"] != []
        for detection in data["detections"]:
            if params.get("branch", ""):
                assert params["branch"] == detection["pkgset_name"]
            if params.get("scanner", ""):
                for scanner in [
                    info["av_scanner"] for info in detection["detect_info"]
                ]:
                    assert params["scanner"] == scanner
            if params.get("issue", ""):
                for issue in [info["av_issue"] for info in detection["detect_info"]]:
                    assert params["issue"] == issue
            if params.get("input", "") == AV_SCAN_PKG_NAME_IN_DB:
                assert params["input"] in detection["pkg_name"]
            if params.get("input", "") == AV_SCAN_MESSAGE_IN_DB:
                for msg in [info["av_message"] for info in detection["detect_info"]]:
                    assert params["input"] in msg
        if params.get("limit", ""):
            assert params["limit"] == data["length"]
