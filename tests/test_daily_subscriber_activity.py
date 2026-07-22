from pathlib import Path

import pandas as pd
import pytest

from analytics.subscriber_profiles import (
    CuratedDatasetError,
    build_daily_subscriber_activity,
)


def build_sample_hourly_curated_data() -> pd.DataFrame:
    """
    Build hourly curated rows for two subscribers.

    SUB_000001 appears in two hourly windows so that daily
    aggregation and latest-context selection can be tested.
    """
    return pd.DataFrame(
        {
            "subscriber_id": [
                "SUB_000001",
                "SUB_000001",
                "SUB_000002",
            ],
            "imsi": [
                "334030000000001",
                "334030000000001",
                "334030000000002",
            ],
            "msisdn": [
                "+525500000001",
                "+525500000001",
                "+525500000002",
            ],
            "customer_segment": [
                "Consumer",
                "Consumer",
                "Business",
            ],
            "subscriber_status": [
                "ACTIVE",
                "ACTIVE",
                "ACTIVE",
            ],
            "plan_id": [
                "PLAN_001",
                "PLAN_001",
                "PLAN_002",
            ],
            "plan_name": [
                "Unlimited",
                "Unlimited",
                "Business Pro",
            ],
            "plan_type": [
                "Postpaid",
                "Postpaid",
                "Postpaid",
            ],
            "monthly_data_allowance_gb": [
                100,
                100,
                200,
            ],
            "max_download_mbps": [
                500,
                500,
                1000,
            ],
            "max_upload_mbps": [
                100,
                100,
                200,
            ],
            "technology_access": [
                "5G",
                "5G",
                "5G",
            ],
            "latest_tac": [
                "35693803",
                "35693803",
                "35209900",
            ],
            "latest_device_vendor": [
                "Samsung",
                "Samsung",
                "Apple",
            ],
            "latest_device_model": [
                "Galaxy S24",
                "Galaxy S24 Ultra",
                "iPhone 15",
            ],
            "latest_device_os": [
                "Android",
                "Android",
                "iOS",
            ],
            "latest_device_technology": [
                "5G",
                "5G",
                "5G",
            ],
            "latest_cell_id": [
                "CELL_001",
                "CELL_002",
                "CELL_003",
            ],
            "latest_city": [
                "Puebla",
                "Mexico City",
                "Monterrey",
            ],
            "latest_state": [
                "Puebla",
                "Ciudad de México",
                "Nuevo León",
            ],
            "latest_network_technology": [
                "4G",
                "5G",
                "5G",
            ],
            "event_count": [
                2,
                3,
                1,
            ],
            "total_bytes_dl": [
                6000,
                9000,
                4000,
            ],
            "total_bytes_ul": [
                600,
                900,
                400,
            ],
            "total_bytes": [
                6600,
                9900,
                4400,
            ],
            "latency_sum": [
                100.0,
                300.0,
                40.0,
            ],
            "latency_sample_count": [
                2,
                3,
                1,
            ],
            "packet_loss_sum": [
                0.04,
                0.09,
                0.01,
            ],
            "packet_loss_sample_count": [
                2,
                3,
                1,
            ],
            "window_start": pd.to_datetime(
                [
                    "2024-06-01T00:00:00Z",
                    "2024-06-01T01:00:00Z",
                    "2024-06-01T00:00:00Z",
                ],
                utc=True,
            ),
            "window_end": pd.to_datetime(
                [
                    "2024-06-01T01:00:00Z",
                    "2024-06-01T02:00:00Z",
                    "2024-06-01T01:00:00Z",
                ],
                utc=True,
            ),
        }
    )


def write_hourly_partition(
    dataframe: pd.DataFrame,
    hourly_day_partition: Path,
) -> None:
    """
    Write one hourly Parquet file for every hour represented
    in the sample DataFrame.
    """
    dataframe = dataframe.copy()

    dataframe["window_start"] = pd.to_datetime(
        dataframe["window_start"],
        utc=True,
    )

    for hour, hourly_data in dataframe.groupby(
        dataframe["window_start"].dt.hour
    ):
        hour_directory = (
            hourly_day_partition
            / f"hour={hour:02d}"
        )

        hour_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        hourly_data.to_parquet(
            hour_directory
            / "subscriber_activity_hourly.parquet",
            index=False,
        )


@pytest.fixture
def hourly_day_partition(tmp_path: Path) -> Path:
    """
    Create a valid temporary hourly partition for one day.
    """
    partition = (
        tmp_path
        / "subscriber_activity_hourly"
        / "year=2024"
        / "month=06"
        / "day=01"
    )

    dataframe = build_sample_hourly_curated_data()

    write_hourly_partition(
        dataframe,
        partition,
    )

    return partition

def test_build_daily_subscriber_activity_creates_one_row_per_subscriber(
    hourly_day_partition: Path,
    tmp_path: Path,
):
    output_file = (
        tmp_path
        / "subscriber_activity_daily.parquet"
    )

    result = build_daily_subscriber_activity(
        hourly_day_partition,
        output_file=output_file,
    )

    curated = pd.read_parquet(result)

    assert result.exists()
    assert len(curated) == 2
    assert curated["subscriber_id"].is_unique

    assert set(curated["subscriber_id"]) == {
        "SUB_000001",
        "SUB_000002",
    }

def test_build_daily_subscriber_activity_sums_usage_metrics(
    hourly_day_partition: Path,
    tmp_path: Path,
):
    output_file = (
        tmp_path
        / "subscriber_activity_daily.parquet"
    )

    result = build_daily_subscriber_activity(
        hourly_day_partition,
        output_file=output_file,
    )

    profiles = pd.read_parquet(result)

    profile = profiles.loc[
        profiles["subscriber_id"] == "SUB_000001"
    ].iloc[0]

    assert profile["event_count"] == 5
    assert profile["total_bytes_dl"] == 15000
    assert profile["total_bytes_ul"] == 1500
    assert profile["total_bytes"] == 16500

def test_build_daily_subscriber_activity_calculates_weighted_averages(
    hourly_day_partition: Path,
    tmp_path: Path,
):
    output_file = (
        tmp_path
        / "subscriber_activity_daily.parquet"
    )

    result = build_daily_subscriber_activity(
        hourly_day_partition,
        output_file=output_file,
    )

    profiles = pd.read_parquet(result)

    profile = profiles.loc[
        profiles["subscriber_id"] == "SUB_000001"
    ].iloc[0]

    assert profile["latency_sum"] == pytest.approx(400.0)
    assert profile["latency_sample_count"] == 5
    assert profile["avg_latency_ms"] == pytest.approx(80.0)

    assert profile["packet_loss_sum"] == pytest.approx(0.13)
    assert profile["packet_loss_sample_count"] == 5
    assert profile["avg_packet_loss_pct"] == pytest.approx(
        0.026
    )

def test_build_daily_subscriber_activity_uses_latest_hourly_context(
    hourly_day_partition: Path,
    tmp_path: Path,
):
    output_file = (
        tmp_path
        / "subscriber_activity_daily.parquet"
    )

    result = build_daily_subscriber_activity(
        hourly_day_partition,
        output_file=output_file,
    )

    profiles = pd.read_parquet(result)

    profile = profiles.loc[
        profiles["subscriber_id"] == "SUB_000001"
    ].iloc[0]

    assert (
        profile["latest_device_model"]
        == "Galaxy S24 Ultra"
    )
    assert profile["latest_cell_id"] == "CELL_002"
    assert profile["latest_city"] == "Mexico City"
    assert profile["latest_network_technology"] == "5G"

def test_build_daily_subscriber_activity_rejects_multiple_days(
    tmp_path: Path,
):
    dataframe = build_sample_hourly_curated_data()

    next_day_record = dataframe.iloc[[0]].copy()

    next_day_record["window_start"] = pd.to_datetime(
        ["2024-06-02T00:00:00Z"],
        utc=True,
    )
    next_day_record["window_end"] = pd.to_datetime(
        ["2024-06-02T01:00:00Z"],
        utc=True,
    )

    dataframe = pd.concat(
        [
            dataframe,
            next_day_record,
        ],
        ignore_index=True,
    )

    partition = (
        tmp_path
        / "subscriber_activity_hourly"
        / "year=2024"
        / "month=06"
        / "day=01"
    )

    write_hourly_partition(
        dataframe,
        partition,
    )

    output_file = (
        tmp_path
        / "subscriber_activity_daily.parquet"
    )

    with pytest.raises(
        CuratedDatasetError,
        match=(
            "The hourly partition contains records from "
            "more than one daily window"
        ),
    ):
        build_daily_subscriber_activity(
            partition,
            output_file=output_file,
        )

def test_build_daily_subscriber_activity_rejects_partition_without_files(
    tmp_path: Path,
):
    partition = (
        tmp_path
        / "subscriber_activity_hourly"
        / "year=2024"
        / "month=06"
        / "day=01"
    )

    partition.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = (
        tmp_path
        / "subscriber_activity_daily.parquet"
    )

    with pytest.raises(
        FileNotFoundError,
        match="No hourly Parquet files found",
    ):
        build_daily_subscriber_activity(
            partition,
            output_file=output_file,
        )

def test_build_daily_subscriber_activity_rejects_empty_parquet(
    tmp_path: Path,
):
    partition = (
        tmp_path
        / "subscriber_activity_hourly"
        / "year=2024"
        / "month=06"
        / "day=01"
    )

    hour_directory = partition / "hour=00"

    hour_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    empty_dataframe = (
        build_sample_hourly_curated_data()
        .iloc[0:0]
        .copy()
    )

    empty_dataframe.to_parquet(
        hour_directory
        / "subscriber_activity_hourly.parquet",
        index=False,
    )

    output_file = (
        tmp_path
        / "subscriber_activity_daily.parquet"
    )

    with pytest.raises(
        CuratedDatasetError,
        match=(
            "No hourly subscriber activity data found "
            "in the hourly partition"
        ),
    ):
        build_daily_subscriber_activity(
            partition,
            output_file=output_file,
        )