from fastapi.testclient import TestClient

from api.app import app


client = TestClient(app)


def test_get_health_returns_healthy_status() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/json"
    )
    assert response.json() == {
        "status": "healthy"
    }


def test_health_endpoint_is_documented_in_openapi() -> None:
    openapi_schema = app.openapi()

    health_operation = openapi_schema["paths"][
        "/health"
    ]["get"]

    assert health_operation["summary"] == (
        "Check API liveness"
    )

    assert health_operation["responses"]["200"][
        "content"
    ]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/HealthResponse"
    }
