from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api.app import app


@pytest.fixture
def client(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[TestClient]:
    mongodb_client = MagicMock()

    monkeypatch.setattr(
        "api.app.create_mongodb_client",
        MagicMock(
            return_value=mongodb_client
        ),
    )

    with TestClient(app) as test_client:
        yield test_client


def test_get_health_returns_healthy_status(
    client: TestClient,
) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/json"
    )
    assert response.json() == {
        "status": "healthy"
    }


def test_health_endpoint_is_documented_in_openapi(
    client: TestClient,
) -> None:
    openapi_schema = client.app.openapi()

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
