from pymongo import MongoClient

from config.settings import (
    MONGODB_TIMEOUT_MS,
    MONGODB_URI,
)


class MongoDBConfigurationError(ValueError):
    """Raised when MongoDB configuration is invalid."""


def create_mongodb_client(
    uri: str = MONGODB_URI,
    timeout_ms: int = MONGODB_TIMEOUT_MS,
) -> MongoClient:
    if not uri.strip():
        raise MongoDBConfigurationError(
            "MONGODB_URI is required to connect to MongoDB."
        )

    if timeout_ms <= 0:
        raise MongoDBConfigurationError(
            "MongoDB timeout must be greater than zero."
        )

    return MongoClient(
        uri,
        serverSelectionTimeoutMS=timeout_ms,
        connectTimeoutMS=timeout_ms,
        appname="subscriber-analytics-platform",
        tz_aware=True,
    )


def ping_mongodb(
    client: MongoClient,
) -> None:
    client.admin.command("ping")


def verify_mongodb_connection(
    uri: str = MONGODB_URI,
    timeout_ms: int = MONGODB_TIMEOUT_MS,
) -> None:
    client = create_mongodb_client(
        uri=uri,
        timeout_ms=timeout_ms,
    )

    try:
        ping_mongodb(client)
    finally:
        client.close()