from pymongo import ASCENDING, MongoClient
from pymongo.collection import Collection
from pathlib import Path

import pandas as pd
from datetime import datetime
from typing import Any

import numpy as np

from analytics.subscriber_profiles import (
    CURRENT_PROFILE_FILENAME,
)
from config.settings import (
    SUBSCRIBER_PROFILES_CURRENT_DIRECTORY,
)
from config.settings import (
    MONGODB_COLLECTION,
    MONGODB_DATABASE,
)
from infrastructure.mongodb_config import (
    MongoDBConfigurationError,
)

from dataclasses import dataclass

from pymongo import UpdateOne
from pymongo.errors import BulkWriteError

SUBSCRIBER_ID_INDEX_NAME = "uq_subscriber_id"

MONGODB_PROFILE_REQUIRED_COLUMNS = {
    "subscriber_id",
    "imsi",
    "msisdn",
    "plan",
    "tac",
    "device_vendor",
    "device_model",
    "device_os",
    "device_capability",
    "network_technology",
    "cell_id",
    "city",
    "state",
    "country",
    "first_activity_at",
    "last_activity_at",
    "active_day_count",
    "lifetime_event_count",
    "lifetime_total_bytes_dl",
    "lifetime_total_bytes_ul",
    "lifetime_total_bytes",
    "lifetime_latency_sum",
    "lifetime_latency_sample_count",
    "lifetime_avg_latency_ms",
    "lifetime_packet_loss_sum",
    "lifetime_packet_loss_sample_count",
    "lifetime_avg_packet_loss_pct",
    "profile_version",
    "profile_updated_at",
}


class MongoDBProfileError(Exception):
    """Raised when subscriber profiles cannot be synchronized."""

def load_subscriber_profiles_snapshot(
    snapshot_file: Path | None = None,
) -> pd.DataFrame:
    if snapshot_file is None:
        snapshot_file = (
            SUBSCRIBER_PROFILES_CURRENT_DIRECTORY
            / CURRENT_PROFILE_FILENAME
        )

    snapshot_file = Path(snapshot_file)

    if not snapshot_file.exists():
        raise FileNotFoundError(
            f"Subscriber profile snapshot not found: "
            f"{snapshot_file}"
        )

    if not snapshot_file.is_file():
        raise IsADirectoryError(
            "Expected a subscriber profile Parquet file: "
            f"{snapshot_file}"
        )

    profiles = pd.read_parquet(
        snapshot_file
    )

    if profiles.empty:
        raise MongoDBProfileError(
            "Subscriber profile snapshot is empty."
        )

    missing_columns = (
        MONGODB_PROFILE_REQUIRED_COLUMNS
        - set(profiles.columns)
    )

    if missing_columns:
        missing = ", ".join(
            sorted(missing_columns)
        )

        raise MongoDBProfileError(
            f"Missing required subscriber profile "
            f"columns: {missing}"
        )

    if profiles["subscriber_id"].isna().any():
        raise MongoDBProfileError(
            "Subscriber profiles contain null "
            "subscriber IDs."
        )

    blank_subscriber_ids = (
        profiles["subscriber_id"]
        .astype("string")
        .str.strip()
        .eq("")
    )

    if blank_subscriber_ids.any():
        raise MongoDBProfileError(
            "Subscriber profiles contain blank "
            "subscriber IDs."
        )

    if profiles["subscriber_id"].duplicated().any():
        raise MongoDBProfileError(
            "Subscriber profiles contain duplicate "
            "subscriber IDs."
        )

    timestamp_columns = [
        "first_activity_at",
        "last_activity_at",
        "profile_updated_at",
    ]

    validated_profiles = profiles.copy()

    for column in timestamp_columns:
        validated_profiles[column] = pd.to_datetime(
            validated_profiles[column],
            utc=True,
            errors="coerce",
        )

        if validated_profiles[column].isna().any():
            raise MongoDBProfileError(
                "Subscriber profiles contain invalid "
                f"{column} values."
            )

    return validated_profiles

def get_subscriber_profiles_collection(
    client: MongoClient,
    database_name: str = MONGODB_DATABASE,
    collection_name: str = MONGODB_COLLECTION,
) -> Collection:
    if not database_name.strip():
        raise MongoDBConfigurationError(
            "MONGODB_DATABASE is required."
        )

    if not collection_name.strip():
        raise MongoDBConfigurationError(
            "MONGODB_COLLECTION is required."
        )

    return client[
        database_name
    ][
        collection_name
    ]


def ensure_subscriber_id_index(
    collection: Collection,
) -> str:
    return collection.create_index(
        [
            (
                "subscriber_id",
                ASCENDING,
            )
        ],
        unique=True,
        name=SUBSCRIBER_ID_INDEX_NAME,
    )

def to_bson_value(
    value: Any,
) -> Any:
    if value is None:
        return None

    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()

    if pd.isna(value):
        return None

    if isinstance(value, np.generic):
        return value.item()

    return value

def profile_row_to_document(
    profile: pd.Series,
) -> dict:
    return {
        "subscriber_id": to_bson_value(
            profile["subscriber_id"]
        ),
        "subscriber": {
            "imsi": to_bson_value(
                profile["imsi"]
            ),
            "msisdn": to_bson_value(
                profile["msisdn"]
            ),
            "plan": to_bson_value(
                profile["plan"]
            ),
        },
        "device": {
            "tac": to_bson_value(
                profile["tac"]
            ),
            "vendor": to_bson_value(
                profile["device_vendor"]
            ),
            "model": to_bson_value(
                profile["device_model"]
            ),
            "os": to_bson_value(
                profile["device_os"]
            ),
            "capability": to_bson_value(
                profile["device_capability"]
            ),
        },
        "last_network_state": {
            "technology": to_bson_value(
                profile["network_technology"]
            ),
            "cell_id": to_bson_value(
                profile["cell_id"]
            ),
            "city": to_bson_value(
                profile["city"]
            ),
            "state": to_bson_value(
                profile["state"]
            ),
            "country": to_bson_value(
                profile["country"]
            ),
        },
        "activity": {
            "first_activity_at": to_bson_value(
                profile["first_activity_at"]
            ),
            "last_activity_at": to_bson_value(
                profile["last_activity_at"]
            ),
            "active_day_count": to_bson_value(
                profile["active_day_count"]
            ),
            "lifetime_event_count": to_bson_value(
                profile["lifetime_event_count"]
            ),
            "total_bytes_dl": to_bson_value(
                profile["lifetime_total_bytes_dl"]
            ),
            "total_bytes_ul": to_bson_value(
                profile["lifetime_total_bytes_ul"]
            ),
            "total_bytes": to_bson_value(
                profile["lifetime_total_bytes"]
            ),
            "latency_sum": to_bson_value(
                profile["lifetime_latency_sum"]
            ),
            "latency_sample_count": to_bson_value(
                profile[
                    "lifetime_latency_sample_count"
                ]
            ),
            "avg_latency_ms": to_bson_value(
                profile["lifetime_avg_latency_ms"]
            ),
            "packet_loss_sum": to_bson_value(
                profile[
                    "lifetime_packet_loss_sum"
                ]
            ),
            "packet_loss_sample_count": to_bson_value(
                profile[
                    "lifetime_packet_loss_sample_count"
                ]
            ),
            "avg_packet_loss_pct": to_bson_value(
                profile[
                    "lifetime_avg_packet_loss_pct"
                ]
            ),
        },
        "metadata": {
            "profile_version": to_bson_value(
                profile["profile_version"]
            ),
            "profile_updated_at": to_bson_value(
                profile["profile_updated_at"]
            ),
        },
    }

def build_mongodb_profile_documents(
    profiles: pd.DataFrame,
) -> list[dict]:
    if profiles.empty:
        raise MongoDBProfileError(
            "Cannot build MongoDB documents from an "
            "empty profile dataset."
        )

    documents = [
        profile_row_to_document(profile)
        for _, profile in profiles.iterrows()
    ]

    subscriber_ids = [
        document["subscriber_id"]
        for document in documents
    ]

    if len(subscriber_ids) != len(
        set(subscriber_ids)
    ):
        raise MongoDBProfileError(
            "MongoDB profile documents contain duplicate "
            "subscriber IDs."
        )

    return documents

@dataclass(frozen=True)
class MongoDBProfileSyncReport:
    source_profile_count: int
    matched_count: int
    modified_count: int
    upserted_count: int
    failed_count: int
    validated_profile_count: int

def build_profile_upsert_operations(
    documents: list[dict],
) -> list[UpdateOne]:
    if not documents:
        raise MongoDBProfileError(
            "Cannot build MongoDB upserts without "
            "subscriber profile documents."
        )

    return [
        UpdateOne(
            {
                "subscriber_id": document[
                    "subscriber_id"
                ]
            },
            {
                "$set": document
            },
            upsert=True,
        )
        for document in documents
    ]

def sync_subscriber_profiles(
    collection: Collection,
    documents: list[dict],
) -> MongoDBProfileSyncReport:
    operations = build_profile_upsert_operations(
        documents
    )

    try:
        result = collection.bulk_write(
            operations,
            ordered=False,
        )
    except BulkWriteError as error:
        failed_count = len(
            error.details.get(
                "writeErrors",
                [],
            )
        )

        raise MongoDBProfileError(
            "MongoDB subscriber profile synchronization "
            f"failed for {failed_count} operation(s)."
        ) from error

    subscriber_ids = [
        document["subscriber_id"]
        for document in documents
    ]

    validated_profile_count = (
        collection.count_documents(
            {
                "subscriber_id": {
                    "$in": subscriber_ids
                }
            }
        )
    )

    if validated_profile_count != len(documents):
        raise MongoDBProfileError(
            "MongoDB subscriber profile count does not "
            "reconcile with the source snapshot."
        )

    return MongoDBProfileSyncReport(
        source_profile_count=len(documents),
        matched_count=result.matched_count,
        modified_count=result.modified_count,
        upserted_count=result.upserted_count,
        failed_count=0,
        validated_profile_count=(
            validated_profile_count
        ),
    )