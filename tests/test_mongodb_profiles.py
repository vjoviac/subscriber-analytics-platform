from unittest.mock import MagicMock

import pytest
from pymongo import ASCENDING
from pathlib import Path

import pandas as pd
from datetime import datetime

import numpy as np
from infrastructure.mongodb_config import (
    MongoDBConfigurationError,
)
from serving.mongodb_profiles import (
    SUBSCRIBER_ID_INDEX_NAME,
    ensure_subscriber_id_index,
    get_subscriber_profiles_collection,
)
from serving.mongodb_profiles import (
    MONGODB_PROFILE_REQUIRED_COLUMNS,
    MongoDBProfileError,
    load_subscriber_profiles_snapshot,
)

from serving.mongodb_profiles import (
    build_mongodb_profile_documents,
    profile_row_to_document,
    to_bson_value,
)
from pymongo import UpdateOne
from pymongo.errors import BulkWriteError
from serving.mongodb_profiles import (
    MongoDBProfileSyncReport,
    build_profile_upsert_operations,
    sync_subscriber_profiles,
)

def test_get_subscriber_profiles_collection() -> None:
    client = MagicMock()

    database = client["subscriber_analytics"]
    expected_collection = database[
        "subscriber_profiles"
    ]

    result = get_subscriber_profiles_collection(
        client,
        database_name="subscriber_analytics",
        collection_name="subscriber_profiles",
    )

    assert result == expected_collection


def test_get_subscriber_profiles_collection_rejects_empty_database(
) -> None:
    client = MagicMock()

    with pytest.raises(
        MongoDBConfigurationError,
        match="MONGODB_DATABASE is required",
    ):
        get_subscriber_profiles_collection(
            client,
            database_name="",
            collection_name="subscriber_profiles",
        )


def test_get_subscriber_profiles_collection_rejects_empty_collection(
) -> None:
    client = MagicMock()

    with pytest.raises(
        MongoDBConfigurationError,
        match="MONGODB_COLLECTION is required",
    ):
        get_subscriber_profiles_collection(
            client,
            database_name="subscriber_analytics",
            collection_name="",
        )


def test_ensure_subscriber_id_index_creates_unique_index(
) -> None:
    collection = MagicMock()
    collection.create_index.return_value = (
        SUBSCRIBER_ID_INDEX_NAME
    )

    result = ensure_subscriber_id_index(
        collection
    )

    assert result == SUBSCRIBER_ID_INDEX_NAME

    collection.create_index.assert_called_once_with(
        [
            (
                "subscriber_id",
                ASCENDING,
            )
        ],
        unique=True,
        name=SUBSCRIBER_ID_INDEX_NAME,
    )

def build_sample_mongodb_profile() -> pd.DataFrame:
    profile = {
        column: 0
        for column in MONGODB_PROFILE_REQUIRED_COLUMNS
    }

    profile.update(
        {
            "subscriber_id": "SUB_000001",
            "imsi": "334030123456789",
            "msisdn": "+525512345678",
            "plan": "Unlimited",
            "tac": "35693803",
            "device_vendor": "Samsung",
            "device_model": "Galaxy S24",
            "device_os": "Android",
            "device_capability": "5G",
            "network_technology": "5G",
            "cell_id": "CELL_001",
            "city": "Mexico City",
            "state": "Ciudad de México",
            "country": None,
            "first_activity_at": pd.Timestamp(
                "2026-07-22T00:00:00Z"
            ),
            "last_activity_at": pd.Timestamp(
                "2026-07-25T00:00:00Z"
            ),
            "profile_updated_at": pd.Timestamp(
                "2026-07-26T12:00:00Z"
            ),
            "active_day_count": 3,
            "profile_version": 1,
        }
    )

    return pd.DataFrame([profile])

def test_load_subscriber_profiles_snapshot(
    tmp_path: Path,
) -> None:
    snapshot_file = tmp_path / "profiles.parquet"

    build_sample_mongodb_profile().to_parquet(
        snapshot_file,
        index=False,
    )

    result = load_subscriber_profiles_snapshot(
        snapshot_file
    )

    assert len(result) == 1
    assert result["subscriber_id"].is_unique
    assert str(result["profile_updated_at"].dt.tz) == "UTC"


def test_load_subscriber_profiles_snapshot_rejects_missing_file(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        FileNotFoundError,
        match="snapshot not found",
    ):
        load_subscriber_profiles_snapshot(
            tmp_path / "missing.parquet"
        )


def test_load_subscriber_profiles_snapshot_rejects_missing_columns(
    tmp_path: Path,
) -> None:
    snapshot_file = tmp_path / "profiles.parquet"

    dataframe = (
        build_sample_mongodb_profile()
        .drop(columns=["subscriber_id"])
    )

    dataframe.to_parquet(
        snapshot_file,
        index=False,
    )

    with pytest.raises(
        MongoDBProfileError,
        match="Missing required subscriber profile columns",
    ):
        load_subscriber_profiles_snapshot(
            snapshot_file
        )


def test_load_subscriber_profiles_snapshot_rejects_duplicate_ids(
    tmp_path: Path,
) -> None:
    snapshot_file = tmp_path / "profiles.parquet"

    dataframe = build_sample_mongodb_profile()

    dataframe = pd.concat(
        [dataframe, dataframe],
        ignore_index=True,
    )

    dataframe.to_parquet(
        snapshot_file,
        index=False,
    )

    with pytest.raises(
        MongoDBProfileError,
        match="duplicate subscriber IDs",
    ):
        load_subscriber_profiles_snapshot(
            snapshot_file
        )


def test_load_subscriber_profiles_snapshot_rejects_blank_id(
    tmp_path: Path,
) -> None:
    snapshot_file = tmp_path / "profiles.parquet"

    dataframe = build_sample_mongodb_profile()
    dataframe["subscriber_id"] = "   "

    dataframe.to_parquet(
        snapshot_file,
        index=False,
    )

    with pytest.raises(
        MongoDBProfileError,
        match="blank subscriber IDs",
    ):
        load_subscriber_profiles_snapshot(
            snapshot_file
        )


def test_load_subscriber_profiles_snapshot_rejects_invalid_timestamp(
    tmp_path: Path,
) -> None:
    snapshot_file = tmp_path / "profiles.parquet"

    dataframe = build_sample_mongodb_profile()
    dataframe["profile_updated_at"] = "invalid"

    dataframe.to_parquet(
        snapshot_file,
        index=False,
    )

    with pytest.raises(
        MongoDBProfileError,
        match="invalid profile_updated_at",
    ):
        load_subscriber_profiles_snapshot(
            snapshot_file
        )

def test_to_bson_value_converts_null_values() -> None:
    assert to_bson_value(None) is None
    assert to_bson_value(pd.NA) is None
    assert to_bson_value(float("nan")) is None


def test_to_bson_value_converts_pandas_timestamp() -> None:
    value = pd.Timestamp(
        "2026-07-26T12:00:00Z"
    )

    result = to_bson_value(value)

    assert isinstance(result, datetime)
    assert result.tzinfo is not None


def test_to_bson_value_converts_numpy_scalar() -> None:
    result = to_bson_value(
        np.int64(10)
    )

    assert result == 10
    assert isinstance(result, int)


def test_profile_row_to_document_builds_nested_document(
) -> None:
    profile = (
        build_sample_mongodb_profile()
        .iloc[0]
    )

    result = profile_row_to_document(
        profile
    )

    assert result["subscriber_id"] == "SUB_000001"
    assert result["subscriber"]["plan"] == "Unlimited"
    assert result["device"]["model"] == "Galaxy S24"
    assert result["last_network_state"]["country"] is None

    assert result["activity"]["active_day_count"] == 3
    assert isinstance(
        result["activity"]["first_activity_at"],
        datetime,
    )

    assert result["metadata"]["profile_version"] == 1
    assert isinstance(
        result["metadata"]["profile_updated_at"],
        datetime,
    )


def test_build_mongodb_profile_documents() -> None:
    profiles = build_sample_mongodb_profile()

    result = build_mongodb_profile_documents(
        profiles
    )

    assert len(result) == 1
    assert result[0]["subscriber_id"] == "SUB_000001"


def test_build_mongodb_profile_documents_rejects_empty_dataframe(
) -> None:
    with pytest.raises(
        MongoDBProfileError,
        match="empty profile dataset",
    ):
        build_mongodb_profile_documents(
            pd.DataFrame()
        )

def test_build_profile_upsert_operations() -> None:
    documents = [
        {
            "subscriber_id": "SUB_000001",
            "subscriber": {
                "plan": "Unlimited",
            },
        }
    ]

    result = build_profile_upsert_operations(
        documents
    )

    assert len(result) == 1
    assert isinstance(result[0], UpdateOne)
    assert result[0]._filter == {
        "subscriber_id": "SUB_000001"
    }
    assert result[0]._doc == {
        "$set": documents[0]
    }
    assert result[0]._upsert is True

def test_build_profile_upsert_operations_rejects_empty_documents(
) -> None:
    with pytest.raises(
        MongoDBProfileError,
        match="without subscriber profile documents",
    ):
        build_profile_upsert_operations([])

def test_sync_subscriber_profiles_returns_report() -> None:
    collection = MagicMock()

    bulk_result = MagicMock()
    bulk_result.matched_count = 0
    bulk_result.modified_count = 0
    bulk_result.upserted_count = 1

    collection.bulk_write.return_value = (
        bulk_result
    )
    collection.count_documents.return_value = 1

    documents = [
        {
            "subscriber_id": "SUB_000001",
            "subscriber": {
                "plan": "Unlimited",
            },
        }
    ]

    result = sync_subscriber_profiles(
        collection,
        documents,
    )

    assert result == MongoDBProfileSyncReport(
        source_profile_count=1,
        matched_count=0,
        modified_count=0,
        upserted_count=1,
        failed_count=0,
        validated_profile_count=1,
    )

    collection.bulk_write.assert_called_once()

    _, keyword_arguments = (
        collection.bulk_write.call_args
    )

    assert keyword_arguments["ordered"] is False

    collection.count_documents.assert_called_once_with(
        {
            "subscriber_id": {
                "$in": ["SUB_000001"]
            }
        }
    )

def test_sync_subscriber_profiles_rejects_count_mismatch(
) -> None:
    collection = MagicMock()

    bulk_result = MagicMock()
    bulk_result.matched_count = 0
    bulk_result.modified_count = 0
    bulk_result.upserted_count = 1

    collection.bulk_write.return_value = (
        bulk_result
    )
    collection.count_documents.return_value = 0

    documents = [
        {
            "subscriber_id": "SUB_000001",
        }
    ]

    with pytest.raises(
        MongoDBProfileError,
        match="does not reconcile",
    ):
        sync_subscriber_profiles(
            collection,
            documents,
        )

def test_sync_subscriber_profiles_propagates_bulk_failure(
) -> None:
    collection = MagicMock()

    collection.bulk_write.side_effect = (
        BulkWriteError(
            {
                "writeErrors": [
                    {
                        "index": 0,
                        "code": 11000,
                        "errmsg": "Duplicate key",
                    }
                ],
                "writeConcernErrors": [],
                "nInserted": 0,
                "nUpserted": 0,
                "nMatched": 0,
                "nModified": 0,
                "nRemoved": 0,
                "upserted": [],
            }
        )
    )

    with pytest.raises(
        MongoDBProfileError,
        match="failed for 1 operation",
    ):
        sync_subscriber_profiles(
            collection,
            [
                {
                    "subscriber_id": "SUB_000001",
                }
            ],
        )

