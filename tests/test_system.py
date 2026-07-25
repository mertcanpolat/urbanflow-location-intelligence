from fastapi.testclient import TestClient


def test_root_endpoint(
    client: TestClient,
) -> None:
    response = client.get("/")

    assert response.status_code == 200

    data = response.json()

    assert data["application"] == (
        "UrbanFlow Location Intelligence API"
    )
    assert data["version"] == "0.1.0"
    assert data["documentation"] == "/docs"


def test_unknown_endpoint_returns_404(
    client: TestClient,
) -> None:
    response = client.get(
        "/api/v1/endpoint-that-does-not-exist"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Not Found"