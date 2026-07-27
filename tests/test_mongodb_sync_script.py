from unittest.mock import MagicMock

import pytest

from scripts.sync_mongodb_profiles import (
    run_mongodb_profile_sync,
)
from serving.mongodb_profiles import (
    MongoDBProfileSyncReport,
)


def test_run_mongodb_profile_sync(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profiles = MagicMock()
    documents = [
        {
            "subscriber_id": "SUB_000001",
        }
    ]

    client = MagicMock()
    collection = MagicMock()

    expected_report = MongoDBProfileSyncReport(
        source_profile_count=1,
        matched_count=0,
        modified_count=0,
        upserted_count=1,
        failed_count=0,
        validated_profile_count=1,
    )

    load_snapshot = MagicMock(
        return_value=profiles
    )
    build_documents = MagicMock(
        return_value=documents
    )
    create_client = MagicMock(
        return_value=client
    )
    get_collection = MagicMock(
        return_value=collection
    )
    ensure_index = MagicMock(
        return_value="uq_subscriber_id"
    )
    synchronize = MagicMock(
        return_value=expected_report
    )
    ping = MagicMock()

    monkeypatch.setattr(
        "scripts.sync_mongodb_profiles."
        "load_subscriber_profiles_snapshot",
        load_snapshot,
    )
    monkeypatch.setattr(
        "scripts.sync_mongodb_profiles."
        "build_mongodb_profile_documents",
        build_documents,
    )
    monkeypatch.setattr(
        "scripts.sync_mongodb_profiles."
        "create_mongodb_client",
        create_client,
    )
    monkeypatch.setattr(
        "scripts.sync_mongodb_profiles."
        "ping_mongodb",
        ping,
    )
    monkeypatch.setattr(
        "scripts.sync_mongodb_profiles."
        "get_subscriber_profiles_collection",
        get_collection,
    )
    monkeypatch.setattr(
        "scripts.sync_mongodb_profiles."
        "ensure_subscriber_id_index",
        ensure_index,
    )
    monkeypatch.setattr(
        "scripts.sync_mongodb_profiles."
        "sync_subscriber_profiles",
        synchronize,
    )

    result = run_mongodb_profile_sync()

    assert result == expected_report

    load_snapshot.assert_called_once_with()
    build_documents.assert_called_once_with(
        profiles
    )
    ping.assert_called_once_with(client)
    get_collection.assert_called_once_with(
        client
    )
    ensure_index.assert_called_once_with(
        collection
    )
    synchronize.assert_called_once_with(
        collection,
        documents,
    )
    client.close.assert_called_once_with()

def test_run_mongodb_profile_sync_closes_client_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = MagicMock()
    collection = MagicMock()

    monkeypatch.setattr(
        "scripts.sync_mongodb_profiles."
        "load_subscriber_profiles_snapshot",
        MagicMock(
            return_value=MagicMock()
        ),
    )
    monkeypatch.setattr(
        "scripts.sync_mongodb_profiles."
        "build_mongodb_profile_documents",
        MagicMock(
            return_value=[
                {
                    "subscriber_id": "SUB_000001",
                }
            ]
        ),
    )
    monkeypatch.setattr(
        "scripts.sync_mongodb_profiles."
        "create_mongodb_client",
        MagicMock(
            return_value=client
        ),
    )
    monkeypatch.setattr(
        "scripts.sync_mongodb_profiles."
        "ping_mongodb",
        MagicMock(),
    )
    monkeypatch.setattr(
        "scripts.sync_mongodb_profiles."
        "get_subscriber_profiles_collection",
        MagicMock(
            return_value=collection
        ),
    )
    monkeypatch.setattr(
        "scripts.sync_mongodb_profiles."
        "ensure_subscriber_id_index",
        MagicMock(),
    )
    monkeypatch.setattr(
        "scripts.sync_mongodb_profiles."
        "sync_subscriber_profiles",
        MagicMock(
            side_effect=RuntimeError(
                "Simulated synchronization failure"
            )
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="Simulated synchronization failure",
    ):
        run_mongodb_profile_sync()

    client.close.assert_called_once_with()

