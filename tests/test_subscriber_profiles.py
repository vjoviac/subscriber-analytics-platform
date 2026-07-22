from pathlib import Path

import pandas as pd
import pytest

from analytics.subscriber_profiles import (
    CuratedDatasetError,
    build_hourly_subscriber_activity,
)


def build_sample_enriched_data() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "event_id": "EVT_001",
                "timestamp": "2026-07-21T19:00:00Z",
                "imsi": "334030123456789",
                "msisdn": "+525512345678",
                "tac": "35111111",
                "cell_id": "CELL_001",
                "application_id": "app-001",
                "bytes_dl": 1000,
                "bytes_ul": 100,
                "total_bytes": 1100,
                "latency_ms": 40.0,
                "packet_loss_pct": 0.10,
                "subscriber_id": "SUB_000001",
                "plan_id": "PLAN_01",
                "customer_segment": "consumer",
                "subscriber_status": "active",
                "subscriber_enrichment_status": "MATCHED",
                "plan_name": "Unlimited",
                "plan_type": "postpaid",
                "monthly_data_allowance_gb": None,
                "max_download_mbps": 500,
                "max_upload_mbps": 100,
                "technology_access": ["4G", "5G"],
                "device_vendor": "Samsung",
                "device_model": "Galaxy A30",
                "device_os": "Android",
                "max_supported_technology": "4G",
                "city": "Querétaro",
                "state": "Querétaro",
                "network_technology": "4G",
                "application_name": "WhatsApp",
                "application_category": "Messaging",
            },
            {
                "event_id": "EVT_002",
                "timestamp": "2026-07-21T19:10:00Z",
                "imsi": "334030123456789",
                "msisdn": "+525512345678",
                "tac": "35693803",
                "cell_id": "CELL_002",
                "application_id": "app-002",
                "bytes_dl": 5000,
                "bytes_ul": 500,
                "total_bytes": 5500,
                "latency_ms": 60.0,
                "packet_loss_pct": 0.30,
                "subscriber_id": "SUB_000001",
                "plan_id": "PLAN_01",
                "customer_segment": "consumer",
                "subscriber_status": "active",
                "subscriber_enrichment_status": "MATCHED",
                "plan_name": "Unlimited",
                "plan_type": "postpaid",
                "monthly_data_allowance_gb": None,
                "max_download_mbps": 500,
                "max_upload_mbps": 100,
                "technology_access": ["4G", "5G"],
                "device_vendor": "Samsung",
                "device_model": "Galaxy S24",
                "device_os": "Android",
                "max_supported_technology": "5G",
                "city": "Ciudad de México",
                "state": "Ciudad de México",
                "network_technology": "5G",
                "application_name": "Netflix",
                "application_category": "Video Streaming",
            },
        ]
    )


def write_enriched_file(
    tmp_path: Path,
    dataframe: pd.DataFrame,
) -> Path:
    enriched_partition = (
        tmp_path
        / "data"
        / "enriched"
        / "year=2026"
        / "month=07"
        / "day=21"
        / "hour=19"
    )

    enriched_partition.mkdir(
        parents=True,
        exist_ok=True,
    )

    enriched_file = (
        enriched_partition
        / "enriched_subscriber_events_20260721_190000.parquet"
    )

    dataframe.to_parquet(
        enriched_file,
        index=False,
    )

    return enriched_partition

def test_build_hourly_subscriber_activity_creates_one_row_per_subscriber(
    tmp_path: Path,
) -> None:
    dataframe = build_sample_enriched_data()
    enriched_partition = write_enriched_file(tmp_path, dataframe)
    output_file = tmp_path / "subscriber_profiles.parquet"

    result = build_hourly_subscriber_activity(
        enriched_partition,
        output_file=output_file,
    )

    curated = pd.read_parquet(result)

    assert result.exists()
    assert len(curated) == 1
    assert curated.iloc[0]["subscriber_id"] == "SUB_000001"

def test_build_hourly_subscriber_activity_calculates_usage_metrics(
    tmp_path: Path,
) -> None:
    dataframe = build_sample_enriched_data()
    enriched_partition = write_enriched_file(tmp_path, dataframe)
    output_file = tmp_path / "subscriber_profiles.parquet"

    result = build_hourly_subscriber_activity(
        enriched_partition,
        output_file=output_file,
    )

    profiles = pd.read_parquet(result)

    profile = profiles.iloc[0]

    assert profile["event_count"] == 2
    assert profile["total_bytes_dl"] == 6000
    assert profile["total_bytes_ul"] == 600
    assert profile["total_bytes"] == 6600
    assert profile["avg_latency_ms"] == 50.0
    assert profile["avg_packet_loss_pct"] == 0.2

    subscriber_1 = profiles.loc[
        profiles["subscriber_id"] == "SUB_000001"
    ].iloc[0]

    assert subscriber_1["latency_sum"] == 100.0
    assert subscriber_1["latency_sample_count"] == 2

    assert subscriber_1["packet_loss_sum"] == 0.4
    assert subscriber_1["packet_loss_sample_count"] == 2

def test_build_hourly_subscriber_activity_uses_latest_context(
    tmp_path: Path,
) -> None:
    dataframe = build_sample_enriched_data()
    enriched_partition = write_enriched_file(tmp_path, dataframe)
    output_file = tmp_path / "subscriber_profiles.parquet"

    result = build_hourly_subscriber_activity(
        enriched_partition,
        output_file=output_file,
    )

    profile = pd.read_parquet(result).iloc[0]

    assert profile["latest_tac"] == "35693803"
    assert profile["latest_device_model"] == "Galaxy S24"
    assert profile["latest_device_technology"] == "5G"
    assert profile["latest_cell_id"] == "CELL_002"
    assert profile["latest_city"] == "Ciudad de México"
    assert profile["latest_network_technology"] == "5G"

def test_build_hourly_subscriber_activity_selects_top_application_by_traffic(
    tmp_path: Path,
) -> None:
    dataframe = build_sample_enriched_data()
    enriched_partition = write_enriched_file(tmp_path, dataframe)
    output_file = tmp_path / "subscriber_profiles.parquet"

    result = build_hourly_subscriber_activity(
        enriched_partition,
        output_file=output_file,
    )

    profile = pd.read_parquet(result).iloc[0]

    assert profile["top_application_id"] == "app-002"
    assert profile["top_application_name"] == "Netflix"
    assert profile["top_application_bytes"] == 5500

def test_build_hourly_subscriber_activity_excludes_unmatched_subscribers(
    tmp_path: Path,
) -> None:
    dataframe = build_sample_enriched_data()

    unmatched = dataframe.iloc[0].copy()
    unmatched["event_id"] = "EVT_003"
    unmatched["subscriber_id"] = "UNKNOWN"
    unmatched["subscriber_enrichment_status"] = "NOT_FOUND"

    dataframe = pd.concat(
        [
            dataframe,
            unmatched.to_frame().T,
        ],
        ignore_index=True,
    )

    enriched_partition = write_enriched_file(tmp_path, dataframe)
    output_file = tmp_path / "subscriber_profiles.parquet"

    result = build_hourly_subscriber_activity(
        enriched_partition,
        output_file=output_file,
    )

    curated = pd.read_parquet(result)

    assert len(curated) == 1
    assert "UNKNOWN" not in curated["subscriber_id"].tolist()

def test_build_hourly_subscriber_activity_rejects_missing_columns(
    tmp_path: Path,
) -> None:
    dataframe = build_sample_enriched_data().drop(
        columns=["total_bytes"]
    )

    enriched_partition = write_enriched_file(tmp_path, dataframe)
    output_file = tmp_path / "subscriber_profiles.parquet"

    with pytest.raises(
        CuratedDatasetError,
        match="Missing required enriched columns",
    ):
        build_hourly_subscriber_activity(
            enriched_partition,
            output_file=output_file,
        )

def test_build_hourly_subscriber_activity_rejects_empty_matched_dataset(
    tmp_path: Path,
) -> None:
    dataframe = build_sample_enriched_data()
    dataframe["subscriber_enrichment_status"] = "NOT_FOUND"

    enriched_partition = write_enriched_file(tmp_path, dataframe)
    output_file = tmp_path / "subscriber_profiles.parquet"

    with pytest.raises(
        CuratedDatasetError,
        match="No matched subscribers",
    ):
        build_hourly_subscriber_activity(
            enriched_partition,
            output_file=output_file,
        )