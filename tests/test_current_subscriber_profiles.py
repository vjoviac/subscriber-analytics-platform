from pathlib import Path

import pytest

import pandas as pd

from analytics.subscriber_profiles import (
    CuratedDatasetError,
    discover_daily_activity_files,
    load_daily_activity_history,
    validate_daily_timestamps,
    validate_unique_daily_windows,
    load_validated_daily_activity_history,
)


def create_daily_file(
    base_directory: Path,
    year: int,
    month: int,
    day: int,
) -> Path:
    daily_partition = (
        base_directory
        / f"year={year:04d}"
        / f"month={month:02d}"
        / f"day={day:02d}"
    )

    daily_partition.mkdir(
        parents=True,
        exist_ok=True,
    )

    daily_file = (
        daily_partition
        / "subscriber_activity_daily.parquet"
    )

    daily_file.touch()

    return daily_file


def build_sample_daily_activity() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "subscriber_id": "SUB_000001",
                "imsi": "334030000000001",
                "msisdn": "+525500000001",
                "customer_segment": "Consumer",
                "subscriber_status": "ACTIVE",
                "plan_id": "PLAN_001",
                "plan_name": "Unlimited",
                "plan_type": "Postpaid",
                "monthly_data_allowance_gb": 100,
                "max_download_mbps": 500,
                "max_upload_mbps": 100,
                "technology_access": "5G",
                "latest_tac": "35693803",
                "latest_device_vendor": "Samsung",
                "latest_device_model": "Galaxy S24",
                "latest_device_os": "Android",
                "latest_device_technology": "5G",
                "latest_cell_id": "CELL_001",
                "latest_city": "Mexico City",
                "latest_state": "Ciudad de México",
                "latest_network_technology": "5G",
                "event_count": 10,
                "total_bytes_dl": 10000,
                "total_bytes_ul": 1000,
                "total_bytes": 11000,
                "latency_sum": 400.0,
                "latency_sample_count": 10,
                "packet_loss_sum": 0.20,
                "packet_loss_sample_count": 10,
                "window_start": pd.Timestamp(
                    "2026-07-21T00:00:00Z"
                ),
                "window_end": pd.Timestamp(
                    "2026-07-22T00:00:00Z"
                ),
            }
        ]
    )

def write_daily_activity_file(
    base_directory: Path,
    dataframe: pd.DataFrame,
    year: int,
    month: int,
    day: int,
) -> Path:
    daily_partition = (
        base_directory
        / f"year={year:04d}"
        / f"month={month:02d}"
        / f"day={day:02d}"
    )

    daily_partition.mkdir(
        parents=True,
        exist_ok=True,
    )

    daily_file = (
        daily_partition
        / "subscriber_activity_daily.parquet"
    )

    dataframe.to_parquet(
        daily_file,
        index=False,
    )

    return daily_file

def test_load_daily_activity_history_combines_files(
    tmp_path: Path,
) -> None:
    daily_activity_directory = (
        tmp_path / "subscriber_activity_daily"
    )

    first_dataframe = build_sample_daily_activity()

    second_dataframe = build_sample_daily_activity()
    second_dataframe["window_start"] = pd.Timestamp(
        "2026-07-22T00:00:00Z"
    )
    second_dataframe["window_end"] = pd.Timestamp(
        "2026-07-23T00:00:00Z"
    )

    first_file = write_daily_activity_file(
        daily_activity_directory,
        first_dataframe,
        2026,
        7,
        21,
    )

    second_file = write_daily_activity_file(
        daily_activity_directory,
        second_dataframe,
        2026,
        7,
        22,
    )

    result = load_daily_activity_history(
        [first_file, second_file]
    )

    assert len(result) == 2
    assert set(result["window_start"]) == {
        pd.Timestamp("2026-07-21T00:00:00Z"),
        pd.Timestamp("2026-07-22T00:00:00Z"),
    }


def test_load_daily_activity_history_rejects_empty_file_list() -> None:
    with pytest.raises(
        CuratedDatasetError,
        match="No daily activity files were provided",
    ):
        load_daily_activity_history([])


def test_load_daily_activity_history_rejects_missing_columns(
    tmp_path: Path,
) -> None:
    dataframe = build_sample_daily_activity().drop(
        columns=["total_bytes"]
    )

    daily_file = (
        tmp_path / "subscriber_activity_daily.parquet"
    )

    dataframe.to_parquet(
        daily_file,
        index=False,
    )

    with pytest.raises(
        CuratedDatasetError,
        match="Missing required daily columns: total_bytes",
    ):
        load_daily_activity_history([daily_file])

def test_discover_daily_activity_files_returns_sorted_files(
    tmp_path: Path,
) -> None:
    daily_activity_directory = (
        tmp_path / "subscriber_activity_daily"
    )

    second_file = create_daily_file(
        daily_activity_directory,
        2026,
        7,
        22,
    )

    first_file = create_daily_file(
        daily_activity_directory,
        2026,
        7,
        21,
    )

    result = discover_daily_activity_files(
        daily_activity_directory
    )

    assert result == [
        first_file,
        second_file,
    ]


def test_discover_daily_activity_files_rejects_missing_directory(
    tmp_path: Path,
) -> None:
    daily_activity_directory = (
        tmp_path / "subscriber_activity_daily"
    )

    with pytest.raises(
        FileNotFoundError,
        match="Daily activity directory not found",
    ):
        discover_daily_activity_files(
            daily_activity_directory
        )


def test_discover_daily_activity_files_rejects_empty_directory(
    tmp_path: Path,
) -> None:
    daily_activity_directory = (
        tmp_path / "subscriber_activity_daily"
    )

    daily_activity_directory.mkdir()

    with pytest.raises(
        FileNotFoundError,
        match="No daily subscriber activity files found",
    ):
        discover_daily_activity_files(
            daily_activity_directory
        )


def test_discover_daily_activity_files_rejects_file_path(
    tmp_path: Path,
) -> None:
    daily_activity_directory = (
        tmp_path / "subscriber_activity_daily"
    )

    daily_activity_directory.touch()

    with pytest.raises(
        NotADirectoryError,
        match="Expected a daily activity directory",
    ):
        discover_daily_activity_files(
            daily_activity_directory
        )

def test_validate_daily_timestamps_converts_values_to_utc() -> None:
    dataframe = build_sample_daily_activity()

    dataframe["window_start"] = "2026-07-21T00:00:00Z"
    dataframe["window_end"] = "2026-07-22T00:00:00Z"

    result = validate_daily_timestamps(dataframe)

    assert str(result["window_start"].dt.tz) == "UTC"
    assert str(result["window_end"].dt.tz) == "UTC"


def test_validate_daily_timestamps_rejects_invalid_start() -> None:
    dataframe = build_sample_daily_activity()
    dataframe["window_start"] = "invalid-timestamp"

    with pytest.raises(
        CuratedDatasetError,
        match="Invalid window_start values",
    ):
        validate_daily_timestamps(dataframe)


def test_validate_daily_timestamps_rejects_invalid_end() -> None:
    dataframe = build_sample_daily_activity()
    dataframe["window_end"] = "invalid-timestamp"

    with pytest.raises(
        CuratedDatasetError,
        match="Invalid window_end values",
    ):
        validate_daily_timestamps(dataframe)


def test_validate_daily_timestamps_rejects_non_positive_window() -> None:
    dataframe = build_sample_daily_activity()

    dataframe["window_end"] = dataframe["window_start"]

    with pytest.raises(
        CuratedDatasetError,
        match="must end after they start",
    ):
        validate_daily_timestamps(dataframe)

def test_validate_unique_daily_windows_rejects_duplicates() -> None:
    dataframe = build_sample_daily_activity()

    dataframe = pd.concat(
        [
            dataframe,
            dataframe.copy(),
        ],
        ignore_index=True,
    )

    with pytest.raises(
        CuratedDatasetError,
        match="Duplicate daily subscriber windows",
    ):
        validate_unique_daily_windows(dataframe)


def test_validate_unique_daily_windows_allows_different_days() -> None:
    first_day = build_sample_daily_activity()

    second_day = build_sample_daily_activity()
    second_day["window_start"] = pd.Timestamp(
        "2026-07-22T00:00:00Z"
    )
    second_day["window_end"] = pd.Timestamp(
        "2026-07-23T00:00:00Z"
    )

    dataframe = pd.concat(
        [
            first_day,
            second_day,
        ],
        ignore_index=True,
    )

    validate_unique_daily_windows(dataframe)


def test_validate_unique_daily_windows_allows_different_subscribers() -> None:
    first_subscriber = build_sample_daily_activity()

    second_subscriber = build_sample_daily_activity()
    second_subscriber["subscriber_id"] = "SUB_000002"
    second_subscriber["imsi"] = "334030000000002"
    second_subscriber["msisdn"] = "+525500000002"

    dataframe = pd.concat(
        [
            first_subscriber,
            second_subscriber,
        ],
        ignore_index=True,
    )

    validate_unique_daily_windows(dataframe)

def test_load_validated_daily_activity_history(
    tmp_path: Path,
) -> None:
    daily_activity_directory = (
        tmp_path / "subscriber_activity_daily"
    )

    first_day = build_sample_daily_activity()

    second_day = build_sample_daily_activity()
    second_day["window_start"] = pd.Timestamp(
        "2026-07-22T00:00:00Z"
    )
    second_day["window_end"] = pd.Timestamp(
        "2026-07-23T00:00:00Z"
    )

    write_daily_activity_file(
        daily_activity_directory,
        second_day,
        2026,
        7,
        22,
    )

    write_daily_activity_file(
        daily_activity_directory,
        first_day,
        2026,
        7,
        21,
    )

    result = load_validated_daily_activity_history(
        daily_activity_directory
    )

    assert len(result) == 2
    assert str(result["window_start"].dt.tz) == "UTC"
    assert str(result["window_end"].dt.tz) == "UTC"

def test_load_validated_daily_activity_history_rejects_cross_file_duplicates(
    tmp_path: Path,
) -> None:
    daily_activity_directory = (
        tmp_path / "subscriber_activity_daily"
    )

    dataframe = build_sample_daily_activity()

    write_daily_activity_file(
        daily_activity_directory,
        dataframe,
        2026,
        7,
        21,
    )

    write_daily_activity_file(
        daily_activity_directory,
        dataframe,
        2026,
        7,
        22,
    )

    with pytest.raises(
        CuratedDatasetError,
        match="Duplicate daily subscriber windows",
    ):
        load_validated_daily_activity_history(
            daily_activity_directory
        )

