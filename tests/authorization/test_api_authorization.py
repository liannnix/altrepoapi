import pytest
import base64

# test routes
TEST_ROUTE_ADMIN_AUTH = "/auth"
TEST_ROUTE_LDAP_USER_AUTH = "/ldap_user"
TEST_ROUTE_LDAP_ADMIN_AUTH = "/ldap_admin"
TEST_ROUTE_LDAP_GROUPS_AUTH = "/ldap_groups"
# test admin user
TEST_ADMIN_NAME = "admin"
TEST_ADMIN_NAME_FORBIDDEN = "admin2"
TEST_ADMIN_PASSWORD = "12qwaszx"
TEST_ADMIN_LDAP_GROUP = "admins"
# test regular user
TEST_USER_NAME = "user"
TEST_USER2_NAME = "user2"
TEST_USER_PASSWORD = "password"
TEST_USER_LDAP_GROUP = "users"
TEST_USER2_LDAP_GROUP = "users2"
# test fake user
TEST_FAKE_USER_NAME = "UNKNOWN"
TEST_FAKE_USER_PASSWORD = "UNKNOWN"
TEST_FAKE_USER_LDAP_GROUP = "UNKNOWN"


def test_api_admin_authorization_fail(client):
    response = client.get(f"/api{TEST_ROUTE_ADMIN_AUTH}")
    assert response.status_code == 401


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "user": TEST_ADMIN_NAME,
            "password": TEST_ADMIN_PASSWORD,
            "status_code": 200,
        },
        {
            "user": TEST_USER_NAME,
            "password": TEST_ADMIN_PASSWORD,
            "status_code": 401,
        },
        {
            "user": TEST_FAKE_USER_NAME,
            "password": TEST_FAKE_USER_PASSWORD,
            "status_code": 401,
        },
    ],
)
def test_api_admin_authorization(client, kwargs):
    credentials_bytes = f'{kwargs["user"]}:{kwargs["password"]}'.encode("utf-8")
    credentials = base64.b64encode(credentials_bytes).decode("utf-8")
    response = client.get(
        f"/api{TEST_ROUTE_ADMIN_AUTH}",
        headers={"Authorization": f"Basic {credentials}"},
    )
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert "message" in data
        assert data["message"] == "authorized"


def test_api_ldap_authorization_fail(client):
    response = client.get(f"/api{TEST_ROUTE_LDAP_USER_AUTH}")
    assert response.status_code == 401


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "user": TEST_ADMIN_NAME,
            "password": TEST_ADMIN_PASSWORD,
            "route": TEST_ROUTE_LDAP_ADMIN_AUTH,
            "status_code": 200,
        },
        {
            "user": TEST_ADMIN_NAME_FORBIDDEN,
            "password": TEST_ADMIN_PASSWORD,
            "route": TEST_ROUTE_LDAP_ADMIN_AUTH,
            "status_code": 403,
        },
        {
            "user": TEST_FAKE_USER_NAME,
            "password": TEST_ADMIN_PASSWORD,
            "route": TEST_ROUTE_LDAP_ADMIN_AUTH,
            "status_code": 401,
        },
    ],
)
def test_api_ldap_authorization_admin(client, slapd, kwargs):
    credentials_bytes = f'{kwargs["user"]}:{kwargs["password"]}'.encode("utf-8")
    credentials = base64.b64encode(credentials_bytes).decode("utf-8")
    response = client.get(
        f'/api{kwargs["route"]}', headers={"Authorization": f"Basic {credentials}"}
    )
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert "message" in data
        assert data["message"] == "authorized"


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "user": TEST_USER_NAME,
            "password": TEST_USER_PASSWORD,
            "route": TEST_ROUTE_LDAP_USER_AUTH,
            "status_code": 200,
        },
        {
            "user": TEST_USER2_NAME,
            "password": TEST_USER_PASSWORD,
            "route": TEST_ROUTE_LDAP_USER_AUTH,
            "status_code": 401,
        },
        {
            "user": TEST_USER_NAME,
            "password": TEST_FAKE_USER_PASSWORD,
            "route": TEST_ROUTE_LDAP_USER_AUTH,
            "status_code": 401,
        },
    ],
)
def test_api_ldap_authorization_user(client, slapd, kwargs):
    credentials_bytes = f'{kwargs["user"]}:{kwargs["password"]}'.encode("utf-8")
    credentials = base64.b64encode(credentials_bytes).decode("utf-8")
    response = client.get(
        f'/api{kwargs["route"]}', headers={"Authorization": f"Basic {credentials}"}
    )
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert "message" in data
        assert data["message"] == "authorized"


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "user": TEST_USER2_NAME,
            "password": TEST_USER_PASSWORD,
            "route": TEST_ROUTE_LDAP_GROUPS_AUTH,
            "status_code": 200,
        },
        {
            "user": TEST_ADMIN_NAME,
            "password": TEST_ADMIN_PASSWORD,
            "route": TEST_ROUTE_LDAP_GROUPS_AUTH,
            "status_code": 200,
        },
        {
            "user": TEST_USER_NAME,
            "password": TEST_USER_PASSWORD,
            "route": TEST_ROUTE_LDAP_GROUPS_AUTH,
            "status_code": 401,
        },
        {
            "user": TEST_USER2_NAME,
            "password": TEST_FAKE_USER_PASSWORD,
            "route": TEST_ROUTE_LDAP_GROUPS_AUTH,
            "status_code": 401,
        },
    ],
)
def test_api_ldap_authorization_groups(client, slapd, kwargs):
    credentials_bytes = f'{kwargs["user"]}:{kwargs["password"]}'.encode("utf-8")
    credentials = base64.b64encode(credentials_bytes).decode("utf-8")
    response = client.get(
        f'/api{kwargs["route"]}', headers={"Authorization": f"Basic {credentials}"}
    )
    data = response.json
    assert response.status_code == kwargs["status_code"]
    if response.status_code == 200:
        assert "message" in data
        assert data["message"] == "authorized"
