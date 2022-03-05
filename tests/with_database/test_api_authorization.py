import base64

def test_api_authorization_fail(client):
    response = client.get("/api/ping")
    assert response.status_code == 401

def test_api_authorization_pass(client):
    credentials = base64.b64encode(b"admin:12qwaszx").decode('utf-8')
    response = client.get("/api/ping", headers={"Authorization": f"Basic {credentials}"})
    data = response.json
    assert response.status_code == 200
    assert "message" in data
    assert data["message"] == "pong"
