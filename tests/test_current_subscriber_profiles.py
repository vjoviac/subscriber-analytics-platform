from pathlib import Path
import pyarrow.parquet as pq
import pytest

import pandas as pd

from analytics.subscriber_profiles import (
    CuratedDatasetError,
    discover_daily_activity_files,
    load_daily_activity_history,
    validate_daily_timestamps,
    validate_unique_daily_windows,
    load_validated_daily_activity_history,
    build_latest_subscriber_state,
    build_subscriber_activity_coverage,
    build_subscriber_lifetime_metrics,
    build_current_subscriber_profiles,
    validate_current_subscriber_profiles,
    publish_current_subscriber_profiles,
    build_current_subscriber_profiles_snapshot,
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

def test_build_latest_subscriber_state_uses_latest_daily_record() -> None:
    first_day = build_sample_daily_activity()

    second_day = build_sample_daily_activity()
    second_day["window_start"] = pd.Timestamp(
        "2026-07-22T00:00:00Z"
    )
    second_day["window_end"] = pd.Timestamp(
        "2026-07-23T00:00:00Z"
    )
    second_day["plan_name"] = "Premium"
    second_day["latest_device_model"] = "Galaxy S25"
    second_day["latest_cell_id"] = "CELL_002"
    second_day["latest_city"] = "Monterrey"

    dataframe = pd.concat(
        [
            second_day,
            first_day,
        ],
        ignore_index=True,
    )

    result = build_latest_subscriber_state(
        dataframe
    )

    assert len(result) == 1
    assert result.iloc[0]["subscriber_id"] == "SUB_000001"
    assert result.iloc[0]["plan"] == "Premium"
    assert result.iloc[0]["device_model"] == "Galaxy S25"
    assert result.iloc[0]["cell_id"] == "CELL_002"
    assert result.iloc[0]["city"] == "Monterrey"
    assert pd.isna(result.iloc[0]["country"])

def test_build_latest_subscriber_state_returns_one_row_per_subscriber() -> None:
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

    result = build_latest_subscriber_state(
        dataframe
    )

    assert len(result) == 2
    assert result["subscriber_id"].is_unique
    assert set(result["subscriber_id"]) == {
        "SUB_000001",
        "SUB_000002",
    }

def test_build_subscriber_activity_coverage_calculates_dates_and_days() -> None:
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
            second_day,
            first_day,
        ],
        ignore_index=True,
    )

    result = build_subscriber_activity_coverage(
        dataframe
    )

    coverage = result.iloc[0]

    assert coverage["subscriber_id"] == "SUB_000001"
    assert coverage["first_activity_at"] == pd.Timestamp(
        "2026-07-21T00:00:00Z"
    )
    assert coverage["last_activity_at"] == pd.Timestamp(
        "2026-07-22T00:00:00Z"
    )
    assert coverage["active_day_count"] == 2

def test_build_subscriber_activity_coverage_groups_by_subscriber() -> None:
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

    result = build_subscriber_activity_coverage(
        dataframe
    )

    assert len(result) == 2
    assert result["subscriber_id"].is_unique
    assert set(result["active_day_count"]) == {1}

def test_build_subscriber_lifetime_metrics_sums_daily_metrics() -> None:
    first_day = build_sample_daily_activity()

    second_day = build_sample_daily_activity()
    second_day["window_start"] = pd.Timestamp(
        "2026-07-22T00:00:00Z"
    )
    second_day["window_end"] = pd.Timestamp(
        "2026-07-23T00:00:00Z"
    )
    second_day["event_count"] = 20
    second_day["total_bytes_dl"] = 20000
    second_day["total_bytes_ul"] = 2000
    second_day["total_bytes"] = 22000

    dataframe = pd.concat(
        [
            first_day,
            second_day,
        ],
        ignore_index=True,
    )

    result = build_subscriber_lifetime_metrics(
        dataframe
    )

    metrics = result.iloc[0]

    assert metrics["lifetime_event_count"] == 30
    assert metrics["lifetime_total_bytes_dl"] == 30000
    assert metrics["lifetime_total_bytes_ul"] == 3000
    assert metrics["lifetime_total_bytes"] == 33000

def test_build_subscriber_lifetime_metrics_calculates_weighted_averages(
) -> None:
    first_day = build_sample_daily_activity()
    first_day["latency_sum"] = 400.0
    first_day["latency_sample_count"] = 10
    first_day["packet_loss_sum"] = 0.20
    first_day["packet_loss_sample_count"] = 10

    second_day = build_sample_daily_activity()
    second_day["window_start"] = pd.Timestamp(
        "2026-07-22T00:00:00Z"
    )
    second_day["window_end"] = pd.Timestamp(
        "2026-07-23T00:00:00Z"
    )
    second_day["latency_sum"] = 900.0
    second_day["latency_sample_count"] = 30
    second_day["packet_loss_sum"] = 0.90
    second_day["packet_loss_sample_count"] = 30

    dataframe = pd.concat(
        [
            first_day,
            second_day,
        ],
        ignore_index=True,
    )

    result = build_subscriber_lifetime_metrics(
        dataframe
    )

    metrics = result.iloc[0]

    assert metrics["lifetime_latency_sum"] == pytest.approx(
        1300.0
    )
    assert (
        metrics["lifetime_latency_sample_count"]
        == 40
    )
    assert metrics[
        "lifetime_avg_latency_ms"
    ] == pytest.approx(32.5)

    assert metrics[
        "lifetime_packet_loss_sum"
    ] == pytest.approx(1.10)
    assert (
        metrics[
            "lifetime_packet_loss_sample_count"
        ]
        == 40
    )
    assert metrics[
        "lifetime_avg_packet_loss_pct"
    ] == pytest.approx(0.0275)

def test_build_subscriber_lifetime_metrics_returns_null_averages_for_zero_samples(
) -> None:
    dataframe = build_sample_daily_activity()

    dataframe["latency_sum"] = 0.0
    dataframe["latency_sample_count"] = 0
    dataframe["packet_loss_sum"] = 0.0
    dataframe["packet_loss_sample_count"] = 0

    result = build_subscriber_lifetime_metrics(
        dataframe
    )

    metrics = result.iloc[0]

    assert pd.isna(
        metrics["lifetime_avg_latency_ms"]
    )
    assert pd.isna(
        metrics["lifetime_avg_packet_loss_pct"]
    )

def test_build_current_subscriber_profiles_combines_profile_components(
) -> None:
    first_day = build_sample_daily_activity()

    second_day = build_sample_daily_activity()
    second_day["window_start"] = pd.Timestamp(
        "2026-07-22T00:00:00Z"
    )
    second_day["window_end"] = pd.Timestamp(
        "2026-07-23T00:00:00Z"
    )
    second_day["latest_device_model"] = "Galaxy S25"
    second_day["latest_city"] = "Monterrey"
    second_day["event_count"] = 20
    second_day["total_bytes"] = 22000

    dataframe = pd.concat(
        [
            first_day,
            second_day,
        ],
        ignore_index=True,
    )

    profile_updated_at = pd.Timestamp(
        "2026-07-24T12:00:00Z"
    ).to_pydatetime()

    result = build_current_subscriber_profiles(
        dataframe,
        profile_updated_at=profile_updated_at,
    )

    profile = result.iloc[0]

    assert len(result) == 1
    assert profile["subscriber_id"] == "SUB_000001"
    assert profile["device_model"] == "Galaxy S25"
    assert profile["city"] == "Monterrey"

    assert profile["first_activity_at"] == pd.Timestamp(
        "2026-07-21T00:00:00Z"
    )
    assert profile["last_activity_at"] == pd.Timestamp(
        "2026-07-22T00:00:00Z"
    )
    assert profile["active_day_count"] == 2

    assert profile["lifetime_event_count"] == 30
    assert profile["lifetime_total_bytes"] == 33000

    assert profile["profile_version"] == 1
    assert profile["profile_updated_at"] == pd.Timestamp(
        "2026-07-24T12:00:00Z"
    )

def test_build_current_subscriber_profiles_rejects_naive_update_timestamp(
) -> None:
    dataframe = build_sample_daily_activity()

    profile_updated_at = pd.Timestamp(
        "2026-07-24T12:00:00"
    ).to_pydatetime()

    with pytest.raises(
        CuratedDatasetError,
        match="profile_updated_at must be timezone-aware",
    ):
        build_current_subscriber_profiles(
            dataframe,
            profile_updated_at=profile_updated_at,
        )

def test_build_current_subscriber_profiles_returns_unique_subscribers(
) -> None:
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

    result = build_current_subscriber_profiles(
        dataframe
    )

    assert len(result) == 2
    assert result["subscriber_id"].is_unique

def build_sample_current_profiles() -> tuple[
    pd.DataFrame,
    pd.DataFrame,
]:
    daily_history = build_sample_daily_activity()

    profiles = build_current_subscriber_profiles(
        daily_history,
        profile_updated_at=pd.Timestamp(
            "2026-07-24T12:00:00Z"
        ).to_pydatetime(),
    )

    return profiles, daily_history

def test_validate_current_subscriber_profiles_accepts_valid_profiles(
) -> None:
    profiles, daily_history = (
        build_sample_current_profiles()
    )

    validate_current_subscriber_profiles(
        profiles,
        daily_history,
    )


def test_validate_current_subscriber_profiles_rejects_duplicate_subscribers(
) -> None:
    profiles, daily_history = (
        build_sample_current_profiles()
    )

    profiles = pd.concat(
        [profiles, profiles],
        ignore_index=True,
    )

    with pytest.raises(
        CuratedDatasetError,
        match="duplicate subscriber IDs",
    ):
        validate_current_subscriber_profiles(
            profiles,
            daily_history,
        )


def test_validate_current_subscriber_profiles_rejects_negative_metrics(
) -> None:
    profiles, daily_history = (
        build_sample_current_profiles()
    )

    profiles.loc[
        0,
        "lifetime_event_count",
    ] = -1

    with pytest.raises(
        CuratedDatasetError,
        match="negative lifetime metrics",
    ):
        validate_current_subscriber_profiles(
            profiles,
            daily_history,
        )


def test_validate_current_subscriber_profiles_rejects_invalid_activity_range(
) -> None:
    profiles, daily_history = (
        build_sample_current_profiles()
    )

    profiles.loc[
        0,
        "first_activity_at",
    ] = pd.Timestamp("2026-07-25T00:00:00Z")

    with pytest.raises(
        CuratedDatasetError,
        match="invalid activity ranges",
    ):
        validate_current_subscriber_profiles(
            profiles,
            daily_history,
        )


def test_validate_current_subscriber_profiles_rejects_metric_mismatch(
) -> None:
    profiles, daily_history = (
        build_sample_current_profiles()
    )

    profiles.loc[
        0,
        "lifetime_total_bytes",
    ] += 1

    with pytest.raises(
        CuratedDatasetError,
        match="do not reconcile",
    ):
        validate_current_subscriber_profiles(
            profiles,
            daily_history,
        )

def test_publish_current_subscriber_profiles_creates_snapshot(
    tmp_path: Path,
) -> None:
    profiles, _ = build_sample_current_profiles()

    output_directory = (
        tmp_path / "subscriber_profiles_current"
    )

    result = publish_current_subscriber_profiles(
        profiles,
        output_directory,
    )

    published = pd.read_parquet(result)

    assert result == (
        output_directory
        / "subscriber_profiles_current.parquet"
    )
    assert result.exists()
    assert len(published) == 1
    assert published.iloc[0]["subscriber_id"] == (
        "SUB_000001"
    )

    assert not (
        output_directory
        / "subscriber_profiles_current.temporary.parquet"
    ).exists()

def test_publish_current_subscriber_profiles_replaces_existing_snapshot(
    tmp_path: Path,
) -> None:
    profiles, _ = build_sample_current_profiles()

    output_directory = (
        tmp_path / "subscriber_profiles_current"
    )

    publish_current_subscriber_profiles(
        profiles,
        output_directory,
    )

    updated_profiles = profiles.copy()
    updated_profiles["plan"] = "Premium"

    result = publish_current_subscriber_profiles(
        updated_profiles,
        output_directory,
    )

    published = pd.read_parquet(result)

    assert published.iloc[0]["plan"] == "Premium"
    assert not (
        output_directory
        / "subscriber_profiles_current.temporary.parquet"
    ).exists()

def test_publish_current_subscriber_profiles_preserves_existing_snapshot_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profiles, _ = build_sample_current_profiles()

    output_directory = (
        tmp_path / "subscriber_profiles_current"
    )

    output_file = publish_current_subscriber_profiles(
        profiles,
        output_directory,
    )

    original_write_table = pq.write_table

    def failing_write_table(*args, **kwargs) -> None:
        original_write_table(*args, **kwargs)
        raise RuntimeError("Simulated publication failure")

    monkeypatch.setattr(
        pq,
        "write_table",
        failing_write_table,
    )

    updated_profiles = profiles.copy()
    updated_profiles["plan"] = "Premium"

    with pytest.raises(
        RuntimeError,
        match="Simulated publication failure",
    ):
        publish_current_subscriber_profiles(
            updated_profiles,
            output_directory,
        )

    preserved = pd.read_parquet(output_file)

    assert preserved.iloc[0]["plan"] == "Unlimited"
    assert not (
        output_directory
        / "subscriber_profiles_current.temporary.parquet"
    ).exists()

def test_build_current_subscriber_profiles_snapshot_builds_complete_snapshot(
    tmp_path: Path,
) -> None:
    daily_activity_directory = (
        tmp_path / "subscriber_activity_daily"
    )

    output_directory = (
        tmp_path / "subscriber_profiles_current"
    )

    first_day = build_sample_daily_activity()

    second_day = build_sample_daily_activity()
    second_day["window_start"] = pd.Timestamp(
        "2026-07-22T00:00:00Z"
    )
    second_day["window_end"] = pd.Timestamp(
        "2026-07-23T00:00:00Z"
    )
    second_day["latest_device_model"] = "Galaxy S25"
    second_day["latest_city"] = "Monterrey"
    second_day["event_count"] = 20
    second_day["total_bytes_dl"] = 20000
    second_day["total_bytes_ul"] = 2000
    second_day["total_bytes"] = 22000

    write_daily_activity_file(
        daily_activity_directory,
        first_day,
        2026,
        7,
        21,
    )

    write_daily_activity_file(
        daily_activity_directory,
        second_day,
        2026,
        7,
        22,
    )

    profile_updated_at = pd.Timestamp(
        "2026-07-24T12:00:00Z"
    ).to_pydatetime()

    result = (
        build_current_subscriber_profiles_snapshot(
            daily_activity_directory,
            output_directory,
            profile_updated_at=profile_updated_at,
        )
    )

    profiles = pd.read_parquet(result)
    profile = profiles.iloc[0]

    assert result == (
        output_directory
        / "subscriber_profiles_current.parquet"
    )
    assert len(profiles) == 1
    assert profiles["subscriber_id"].is_unique

    assert profile["device_model"] == "Galaxy S25"
    assert profile["city"] == "Monterrey"
    assert profile["active_day_count"] == 2
    assert profile["lifetime_event_count"] == 30
    assert profile["lifetime_total_bytes"] == 33000
    assert profile["profile_version"] == 1
    assert profile["profile_updated_at"] == pd.Timestamp(
        "2026-07-24T12:00:00Z"
    )

def test_build_current_subscriber_profiles_snapshot_does_not_publish_invalid_history(
    tmp_path: Path,
) -> None:
    daily_activity_directory = (
        tmp_path / "subscriber_activity_daily"
    )

    output_directory = (
        tmp_path / "subscriber_profiles_current"
    )

    duplicate_data = build_sample_daily_activity()

    write_daily_activity_file(
        daily_activity_directory,
        duplicate_data,
        2026,
        7,
        21,
    )

    write_daily_activity_file(
        daily_activity_directory,
        duplicate_data,
        2026,
        7,
        22,
    )

    with pytest.raises(
        CuratedDatasetError,
        match="Duplicate daily subscriber windows",
    ):
        build_current_subscriber_profiles_snapshot(
            daily_activity_directory,
            output_directory,
        )

    assert not (
        output_directory
        / "subscriber_profiles_current.parquet"
    ).exists()