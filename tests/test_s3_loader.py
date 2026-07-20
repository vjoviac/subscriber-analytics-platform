from pathlib import Path

from ingestion.s3_loader import build_s3_key


def test_build_s3_key() -> None:
    local_file = Path(
        "data/raw/year=2026/month=07/day=17/events.jsonl"
    )

    object_key = build_s3_key(local_file)

    assert object_key == (
        "raw/year=2026/month=07/day=17/events.jsonl"
    )