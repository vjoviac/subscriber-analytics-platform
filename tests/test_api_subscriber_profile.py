from collections.abc import Iterator
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from pymongo.errors import ServerSelectionTimeoutError

from api.app import app
from infrastructure.mongodb_config import (
    MongoDBConfigurationError,
)


def build_subscriber_profile_document() -> dict:
    return {
        "_id": "internal-mongodb-id",
        "subscriber_id": "SUB_000001",
        "subscriber": {
            "imsi": "334030123456789",
            "msisdn": "+525512345678",
            "plan": "Unlimited",
        },
        "device": {
            "tac": "35693803",
            "vendor": "Samsung",
            "model": "Galaxy S24",
            "os": "Android",
            "capability": "5G",
        },
        "last_network_state": {
            "technology": "5G",
            "cell_id": "CELL_001",
            "city": "Mexico City",
            "state": "Ciudad de México",
            "country": None,
        },
        "activity": {
            "first_activity_at": datetime(
                2026,
                7,
                22,
                tzinfo=UTC,
            ),
            "last_activity_at": datetime(
                2026,
                7,
                25,
                tzinfo=UTC,
            ),
            "active_day_count": 4,
            "lifetime_event_count": 100,
            "total_bytes_dl": 1000,
            "total_bytes_ul": 500,
            "total_bytes": 1500,
            "latency_sum": 2500.0,
            "latency_sample_count": 100,
            "avg_latency_ms": 25.0,
            "packet_loss_sum": 10.0,
            "packet_loss_sample_count": 100,
            "avg_packet_loss_pct": 0.1,
        },
        "metadata": {
            "profile_version": 1,
            "profile_updated_at": datetime(
                2026,
                7,
                26,
                12,
                0,
                tzinfo=UTC,
            ),
        },
    }


@pytest.fixture
def mongodb_client() -> MagicMock:
    return MagicMock()


@pytest.fixture
def client(
    monkeypatch: pytest.MonkeyPatch,
    mongodb_client: MagicMock,
) -> Iterator[TestClient]:
    monkeypatch.setattr(
        "api.app.create_mongodb_client",
        MagicMock(
            return_value=mongodb_client
        ),
    )

    with TestClient(app) as test_client:
        yield test_client


def test_get_subscriber_profile_returns_profile(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    mongodb_client: MagicMock,
) -> None:
    collection = MagicMock()
    get_collection = MagicMock(
        return_value=collection
    )
    find_profile = MagicMock(
        return_value=build_subscriber_profile_document()
    )

    monkeypatch.setattr(
        "api.app.get_subscriber_profiles_collection",
        get_collection,
    )
    monkeypatch.setattr(
        "api.app.find_subscriber_profile",
        find_profile,
    )

    response = client.get(
        "/subscribers/SUB_000001"
    )

    assert response.status_code == 200

    response_body = response.json()

    assert response_body["subscriber_id"] == (
        "SUB_000001"
    )
    assert response_body["subscriber"]["plan"] == (
        "Unlimited"
    )
    assert response_body["device"]["model"] == (
        "Galaxy S24"
    )
    assert "_id" not in response_body

    get_collection.assert_called_once_with(
        mongodb_client
    )
    find_profile.assert_called_once_with(
        collection,
        "SUB_000001",
    )


def test_get_subscriber_profile_returns_not_found(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setattr(
        "api.app.get_subscriber_profiles_collection",
        MagicMock(
            return_value=MagicMock()
        ),
    )
    monkeypatch.setattr(
        "api.app.find_subscriber_profile",
        MagicMock(
            return_value=None
        ),
    )

    response = client.get(
        "/subscribers/SUB_999999"
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Subscriber profile not found."
    }


def test_get_subscriber_profile_returns_unavailable_without_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "api.app.create_mongodb_client",
        MagicMock(
            side_effect=MongoDBConfigurationError(
                "MONGODB_URI is required."
            )
        ),
    )

    with TestClient(app) as client:
        response = client.get(
            "/subscribers/SUB_000001"
        )

    assert response.status_code == 503
    assert response.json() == {
        "detail": (
            "Subscriber profile service is unavailable."
        )
    }


def test_get_subscriber_profile_handles_database_failure(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setattr(
        "api.app.get_subscriber_profiles_collection",
        MagicMock(
            return_value=MagicMock()
        ),
    )
    monkeypatch.setattr(
        "api.app.find_subscriber_profile",
        MagicMock(
            side_effect=ServerSelectionTimeoutError(
                "Simulated MongoDB timeout"
            )
        ),
    )

    response = client.get(
        "/subscribers/SUB_000001"
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": (
            "Subscriber profile service is unavailable."
        )
    }


def test_subscriber_profile_endpoint_is_documented_in_openapi(
    client: TestClient,
) -> None:
    openapi_schema = client.app.openapi()

    operation = openapi_schema["paths"][
        "/subscribers/{subscriber_id}"
    ]["get"]

    assert operation["summary"] == (
        "Get subscriber profile"
    )

    assert operation["responses"]["200"][
        "content"
    ]["application/json"]["schema"] == {
        "$ref": (
            "#/components/schemas/"
            "SubscriberProfileResponse"
        )
    }

    assert operation["responses"]["404"][
        "content"
    ]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ErrorResponse"
    }

    assert operation["responses"]["503"][
        "content"
    ]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ErrorResponse"
    }