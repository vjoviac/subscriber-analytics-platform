from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from pymongo.errors import ServerSelectionTimeoutError

from api.app import app
from infrastructure.mongodb_config import (
    MongoDBConfigurationError,
)


def test_ready_returns_ready_and_closes_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mongodb_client = MagicMock()
    client_factory = MagicMock(
        return_value=mongodb_client
    )
    ping = MagicMock()

    monkeypatch.setattr(
        "api.app.create_mongodb_client",
        client_factory,
        raising=False,
    )
    monkeypatch.setattr(
        "api.app.ping_mongodb",
        ping,
        raising=False,
    )

    with TestClient(app) as client:
        response = client.get("/ready")

        assert response.status_code == 200
        assert response.json() == {
            "status": "ready"
        }

        client_factory.assert_called_once_with()
        ping.assert_called_once_with(
            mongodb_client
        )

    mongodb_client.close.assert_called_once_with()


def test_health_remains_available_without_mongodb_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client_factory = MagicMock(
        side_effect=MongoDBConfigurationError(
            "MONGODB_URI is required."
        )
    )

    monkeypatch.setattr(
        "api.app.create_mongodb_client",
        client_factory,
        raising=False,
    )

    with TestClient(app) as client:
        health_response = client.get("/health")
        ready_response = client.get("/ready")

    assert health_response.status_code == 200
    assert health_response.json() == {
        "status": "healthy"
    }

    assert ready_response.status_code == 503
    assert ready_response.json() == {
        "status": "not_ready",
        "detail": "MongoDB is unavailable.",
    }

    client_factory.assert_called_once_with()


def test_ready_returns_not_ready_when_mongodb_ping_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mongodb_client = MagicMock()
    client_factory = MagicMock(
        return_value=mongodb_client
    )
    ping = MagicMock(
        side_effect=ServerSelectionTimeoutError(
            "Simulated MongoDB timeout"
        )
    )

    monkeypatch.setattr(
        "api.app.create_mongodb_client",
        client_factory,
        raising=False,
    )
    monkeypatch.setattr(
        "api.app.ping_mongodb",
        ping,
        raising=False,
    )

    with TestClient(app) as client:
        health_response = client.get("/health")
        ready_response = client.get("/ready")

        assert health_response.status_code == 200
        assert ready_response.status_code == 503
        assert ready_response.json() == {
            "status": "not_ready",
            "detail": "MongoDB is unavailable.",
        }

        ping.assert_called_once_with(
            mongodb_client
        )

    mongodb_client.close.assert_called_once_with()

def test_ready_endpoint_is_documented_in_openapi(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mongodb_client = MagicMock()

    monkeypatch.setattr(
        "api.app.create_mongodb_client",
        MagicMock(
            return_value=mongodb_client
        ),
    )

    with TestClient(app) as client:
        openapi_schema = client.app.openapi()

    ready_operation = openapi_schema["paths"][
        "/ready"
    ]["get"]

    assert ready_operation["summary"] == (
        "Check API readiness"
    )

    assert ready_operation["responses"]["200"][
        "content"
    ]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ReadinessResponse"
    }

    assert ready_operation["responses"]["503"][
        "content"
    ]["application/json"]["schema"] == {
        "$ref": (
            "#/components/schemas/"
            "ReadinessErrorResponse"
        )
    }

    mongodb_client.close.assert_called_once_with()
