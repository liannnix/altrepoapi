import altrepo_api.version as version


def test_api_name(client):
    response = client.get("/api/version")
    data = response.json
    assert response.status_code == 200
    assert "name" in data
    assert data["name"] == "ALTRepo API"

def test_api_version(client):
    response = client.get("/api/version")
    data = response.json
    assert response.status_code == 200
    assert "version" in data
    assert data["version"] == version.__version__

def test_api_description(client):
    response = client.get("/api/version")
    data = response.json
    assert "description" in data
    assert data["description"] != ""
