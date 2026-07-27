import json
from dataclasses import asdict

from infrastructure.mongodb_config import (
    create_mongodb_client,
    ping_mongodb,
)
from serving.mongodb_profiles import (
    MongoDBProfileSyncReport,
    build_mongodb_profile_documents,
    ensure_subscriber_id_index,
    get_subscriber_profiles_collection,
    load_subscriber_profiles_snapshot,
    sync_subscriber_profiles,
)


def run_mongodb_profile_sync(
) -> MongoDBProfileSyncReport:
    profiles = load_subscriber_profiles_snapshot()

    documents = build_mongodb_profile_documents(
        profiles
    )

    client = create_mongodb_client()

    try:
        ping_mongodb(client)

        collection = (
            get_subscriber_profiles_collection(
                client
            )
        )

        ensure_subscriber_id_index(
            collection
        )

        return sync_subscriber_profiles(
            collection,
            documents,
        )

    finally:
        client.close()


def main() -> None:
    report = run_mongodb_profile_sync()

    print(
        json.dumps(
            asdict(report),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()