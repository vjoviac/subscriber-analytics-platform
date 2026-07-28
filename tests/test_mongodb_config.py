from unittest.mock import MagicMock

import pytest

from infrastructure.mongodb_config import (
    MongoDBConfigurationError,
    create_mongodb_client,
    ping_mongodb,
    verify_mongodb_connection,
)


def test_create_mongodb_client_rejects_empty_uri() -> None:
    with pytest.raises(
        MongoDBConfigurationError,
        match="MONGODB_URI is required",
    ):
        create_mongodb_client(
            uri="",
            timeout_ms=10000,
        )


def test_create_mongodb_client_rejects_invalid_timeout() -> None:
    with pytest.raises(
        MongoDBConfigurationError,
        match="timeout must be greater than zero",
    ):
        create_mongodb_client(
            uri="mongodb://localhost:27017",
            timeout_ms=0,
        )


def test_ping_mongodb_executes_admin_ping() -> None:
    client = MagicMock()

    ping_mongodb(client)

    client.admin.command.assert_called_once_with(
        "ping"
    )


def test_verify_mongodb_connection_closes_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = MagicMock()

    client_factory = MagicMock(
        return_value=client
    )

    monkeypatch.setattr(
        "infrastructure.mongodb_config.MongoClient",
        client_factory,
    )

    verify_mongodb_connection(
        uri="mongodb://localhost:27017",
        timeout_ms=5000,
    )

    client_factory.assert_called_once_with(
        "mongodb://localhost:27017",
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        appname="subscriber-analytics-platform",
        tz_aware=True,
    )

    client.admin.command.assert_called_once_with(
        "ping"
    )
    client.close.assert_called_once_with()