import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from enrichment.enrichment_processor import (
    EnrichmentProcessingError,
    process_raw_file,
)
from generators.catalogs.applications import APPLICATIONS
from generators.catalogs.devices import DEVICES
from generators.catalogs.locations import NETWORK_CELLS
from generators.catalogs.subscribers import SUBSCRIBERS


EXPECTED_COLUMN_COUNT = 44


@pytest.fixture
def valid_raw_event() -> dict:
    """
    Build a valid raw event using keys that exist in the catalogs.
    """
    subscriber = SUBSCRIBERS[0]
    device = DEVICES[0]
    network_cell = NETWORK_CELLS[0]
    application = APPLICATIONS[0]

    return {
        "event_id": "test-event-0001",
        "timestamp": "2026-07-21T19:53:03+00:00",
        "imsi": subscriber["imsi"],
        "msisdn": subscriber["msisdn"],
        "tac": device["tac"],
        "cell_id": network_cell["cell_id"],
        "application_id": application["application_id"],
        "bytes_dl": 1_000_000,
        "bytes_ul": 250_000,
        "total_bytes": 1_250_000,
        "latency_ms": 35,
        "packet_loss_pct": 0.25,
    }


def write_jsonl(path: Path, events: list[dict]) -> None:
    """
    Write a list of dictionaries as a JSONL file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        for event in events:
            file.write(json.dumps(event) + "\n")


def test_process_raw_file_creates_parquet(
    tmp_path: Path,
    valid_raw_event: dict,
) -> None:
    raw_base_dir = tmp_path / "data" / "raw"
    enriched_base_dir = tmp_path / "data" / "enriched"

    raw_file = (
        raw_base_dir
        / "year=2026"
        / "month=07"
        / "day=21"
        / "hour=19"
        / "subscriber_events_test.jsonl"
    )

    write_jsonl(raw_file, [valid_raw_event])

    process_raw_file(
        raw_file=raw_file,
        raw_base_dir=raw_base_dir,
        enriched_base_dir=enriched_base_dir,
    )

    expected_output = (
        enriched_base_dir
        / "year=2026"
        / "month=07"
        / "day=21"
        / "hour=19"
        / "enriched_subscriber_events_test.parquet"
    )

    assert expected_output.exists()
    assert expected_output.is_file()


def test_process_raw_file_preserves_partition_structure(
    tmp_path: Path,
    valid_raw_event: dict,
) -> None:
    raw_base_dir = tmp_path / "raw"
    enriched_base_dir = tmp_path / "enriched"

    partition = Path(
        "year=2026/month=07/day=21/hour=19"
    )

    raw_file = (
        raw_base_dir
        / partition
        / "subscriber_events_test.jsonl"
    )

    write_jsonl(raw_file, [valid_raw_event])

    process_raw_file(
        raw_file=raw_file,
        raw_base_dir=raw_base_dir,
        enriched_base_dir=enriched_base_dir,
    )

    expected_output = (
        enriched_base_dir
        / partition
        / "enriched_subscriber_events_test.parquet"
    )

    assert expected_output.exists()


def test_generated_parquet_has_expected_rows_and_schema(
    tmp_path: Path,
    valid_raw_event: dict,
) -> None:
    raw_base_dir = tmp_path / "raw"
    enriched_base_dir = tmp_path / "enriched"

    raw_file = (
        raw_base_dir
        / "year=2026"
        / "month=07"
        / "day=21"
        / "hour=19"
        / "subscriber_events_test.jsonl"
    )

    events = []

    for index in range(5):
        event = valid_raw_event.copy()
        event["event_id"] = f"test-event-{index:04d}"
        events.append(event)

    write_jsonl(raw_file, events)

    process_raw_file(
        raw_file=raw_file,
        raw_base_dir=raw_base_dir,
        enriched_base_dir=enriched_base_dir,
    )

    output_file = (
        enriched_base_dir
        / "year=2026"
        / "month=07"
        / "day=21"
        / "hour=19"
        / "enriched_subscriber_events_test.parquet"
    )

    table = pq.read_table(output_file)

    assert table.num_rows == 5
    assert table.num_columns == EXPECTED_COLUMN_COUNT

    assert table.schema.field("event_id").type == pa.string()

    assert table.schema.field("timestamp").type == pa.timestamp(
        "us",
        tz="UTC",
    )

    assert (
        table.schema.field("monthly_data_allowance_gb").type
        == pa.int64()
    )

    assert (
        table.schema.field("technology_access").type
        == pa.list_(pa.string())
    )

    assert (
        table.schema.field(
            "subscriber_enrichment_reason"
        ).type
        == pa.string()
    )


def test_generated_parquet_contains_enriched_values(
    tmp_path: Path,
    valid_raw_event: dict,
) -> None:
    raw_base_dir = tmp_path / "raw"
    enriched_base_dir = tmp_path / "enriched"

    raw_file = (
        raw_base_dir
        / "year=2026"
        / "month=07"
        / "day=21"
        / "hour=19"
        / "subscriber_events_test.jsonl"
    )

    write_jsonl(raw_file, [valid_raw_event])

    process_raw_file(
        raw_file=raw_file,
        raw_base_dir=raw_base_dir,
        enriched_base_dir=enriched_base_dir,
    )

    output_file = (
        enriched_base_dir
        / "year=2026"
        / "month=07"
        / "day=21"
        / "hour=19"
        / "enriched_subscriber_events_test.parquet"
    )

    table = pq.read_table(output_file)
    enriched_event = table.to_pylist()[0]

    assert enriched_event["event_id"] == "test-event-0001"

    assert (
        enriched_event["subscriber_enrichment_status"]
        == "MATCHED"
    )
    assert (
        enriched_event["plan_enrichment_status"]
        == "MATCHED"
    )
    assert (
        enriched_event["device_enrichment_status"]
        == "MATCHED"
    )
    assert (
        enriched_event["network_enrichment_status"]
        == "MATCHED"
    )
    assert (
        enriched_event["application_enrichment_status"]
        == "MATCHED"
    )

    assert enriched_event["subscriber_id"] != "UNKNOWN"
    assert enriched_event["device_vendor"] != "UNKNOWN"
    assert enriched_event["application_name"] != "UNKNOWN"


def test_invalid_json_line_is_skipped(
    tmp_path: Path,
    valid_raw_event: dict,
) -> None:
    raw_base_dir = tmp_path / "raw"
    enriched_base_dir = tmp_path / "enriched"

    raw_file = (
        raw_base_dir
        / "year=2026"
        / "month=07"
        / "day=21"
        / "hour=19"
        / "subscriber_events_test.jsonl"
    )

    raw_file.parent.mkdir(parents=True, exist_ok=True)

    with raw_file.open("w", encoding="utf-8") as file:
        file.write(json.dumps(valid_raw_event) + "\n")
        file.write('{"invalid_json":\n')

    process_raw_file(
        raw_file=raw_file,
        raw_base_dir=raw_base_dir,
        enriched_base_dir=enriched_base_dir,
    )

    output_file = (
        enriched_base_dir
        / "year=2026"
        / "month=07"
        / "day=21"
        / "hour=19"
        / "enriched_subscriber_events_test.parquet"
    )

    table = pq.read_table(output_file)

    assert table.num_rows == 1
    assert table["event_id"][0].as_py() == "test-event-0001"


def test_raw_file_is_not_modified(
    tmp_path: Path,
    valid_raw_event: dict,
) -> None:
    raw_base_dir = tmp_path / "raw"
    enriched_base_dir = tmp_path / "enriched"

    raw_file = (
        raw_base_dir
        / "year=2026"
        / "month=07"
        / "day=21"
        / "hour=19"
        / "subscriber_events_test.jsonl"
    )

    write_jsonl(raw_file, [valid_raw_event])

    original_content = raw_file.read_text(
        encoding="utf-8"
    )

    process_raw_file(
        raw_file=raw_file,
        raw_base_dir=raw_base_dir,
        enriched_base_dir=enriched_base_dir,
    )

    current_content = raw_file.read_text(
        encoding="utf-8"
    )

    assert raw_file.exists()
    assert current_content == original_content


def test_nonexistent_raw_file_raises_error(
    tmp_path: Path,
) -> None:
    nonexistent_file = (
        tmp_path
        / "raw"
        / "subscriber_events_missing.jsonl"
    )

    with pytest.raises(EnrichmentProcessingError):
        process_raw_file(
            raw_file=nonexistent_file,
            raw_base_dir=tmp_path / "raw",
            enriched_base_dir=tmp_path / "enriched",
        )