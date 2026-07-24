from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


class CuratedDatasetError(Exception):
    """Raised when a curated dataset cannot be generated."""


REQUIRED_COLUMNS = {
    "event_id",
    "timestamp",
    "imsi",
    "msisdn",
    "tac",
    "cell_id",
    "application_id",
    "bytes_dl",
    "bytes_ul",
    "total_bytes",
    "latency_ms",
    "packet_loss_pct",
    "subscriber_id",
    "plan_id",
    "customer_segment",
    "subscriber_status",
    "subscriber_enrichment_status",
    "plan_name",
    "plan_type",
    "monthly_data_allowance_gb",
    "max_download_mbps",
    "max_upload_mbps",
    "technology_access",
    "device_vendor",
    "device_model",
    "device_os",
    "max_supported_technology",
    "city",
    "state",
    "network_technology",
    "application_name",
    "application_category",
}

HOURLY_REQUIRED_COLUMNS = {
    "subscriber_id",
    "imsi",
    "msisdn",
    "customer_segment",
    "subscriber_status",
    "plan_id",
    "plan_name",
    "plan_type",
    "monthly_data_allowance_gb",
    "max_download_mbps",
    "max_upload_mbps",
    "technology_access",
    "latest_tac",
    "latest_device_vendor",
    "latest_device_model",
    "latest_device_os",
    "latest_device_technology",
    "latest_cell_id",
    "latest_city",
    "latest_state",
    "latest_network_technology",
    "event_count",
    "total_bytes_dl",
    "total_bytes_ul",
    "total_bytes",
    "latency_sum",
    "latency_sample_count",
    "packet_loss_sum",
    "packet_loss_sample_count",
    "window_start",
    "window_end",
}

DAILY_REQUIRED_COLUMNS = {
    "subscriber_id",
    "imsi",
    "msisdn",
    "customer_segment",
    "subscriber_status",
    "plan_id",
    "plan_name",
    "plan_type",
    "monthly_data_allowance_gb",
    "max_download_mbps",
    "max_upload_mbps",
    "technology_access",
    "latest_tac",
    "latest_device_vendor",
    "latest_device_model",
    "latest_device_os",
    "latest_device_technology",
    "latest_cell_id",
    "latest_city",
    "latest_state",
    "latest_network_technology",
    "event_count",
    "total_bytes_dl",
    "total_bytes_ul",
    "total_bytes",
    "latency_sum",
    "latency_sample_count",
    "packet_loss_sum",
    "packet_loss_sample_count",
    "window_start",
    "window_end",
}

def validate_required_columns(dataframe: pd.DataFrame) -> None:
    missing_columns = REQUIRED_COLUMNS - set(dataframe.columns)

    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise CuratedDatasetError(
            f"Missing required enriched columns: {missing}"
        )

def validate_daily_required_columns(
    dataframe: pd.DataFrame,
) -> None:
    missing_columns = DAILY_REQUIRED_COLUMNS - set(
        dataframe.columns
    )

    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise CuratedDatasetError(
            f"Missing required daily columns: {missing}"
        )

def discover_daily_activity_files(
    daily_activity_directory: Path,
) -> list[Path]:
    daily_activity_directory = Path(
        daily_activity_directory
    )

    if not daily_activity_directory.exists():
        raise FileNotFoundError(
            "Daily activity directory not found: "
            f"{daily_activity_directory}"
        )

    if not daily_activity_directory.is_dir():
        raise NotADirectoryError(
            "Expected a daily activity directory: "
            f"{daily_activity_directory}"
        )

    input_files = sorted(
        daily_activity_directory.glob(
            "year=*/month=*/day=*/"
            "subscriber_activity_daily.parquet"
        )
    )

    if not input_files:
        raise FileNotFoundError(
            "No daily subscriber activity files found in: "
            f"{daily_activity_directory}"
        )

    return input_files

def build_hourly_output_path(
    enriched_partition: Path,
    curated_base_dir: Path = Path("data/curated"),
) -> Path:
    enriched_partition = Path(enriched_partition)

    try:
        partition_path = enriched_partition.relative_to(
            Path("data/enriched")
        )
    except ValueError as error:
        raise CuratedDatasetError(
            "The enriched partition must be located inside data/enriched."
        ) from error

    output_directory = (
        curated_base_dir
        / "subscriber_activity_hourly"
        / partition_path
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    return output_directory / "subscriber_activity_hourly.parquet"


def build_top_applications(dataframe: pd.DataFrame) -> pd.DataFrame:
    valid_applications = dataframe[
        dataframe["application_id"].notna()
    ].copy()

    if valid_applications.empty:
        return pd.DataFrame(
            columns=[
                "subscriber_id",
                "top_application_id",
                "top_application_name",
                "top_application_category",
                "top_application_bytes",
            ]
        )

    application_usage = (
        valid_applications
        .groupby(
            [
                "subscriber_id",
                "application_id",
                "application_name",
                "application_category",
            ],
            dropna=False,
            as_index=False,
        )
        .agg(
            top_application_bytes=("total_bytes", "sum")
        )
    )

    application_usage = application_usage.sort_values(
        by=[
            "subscriber_id",
            "top_application_bytes",
            "application_id",
        ],
        ascending=[True, False, True],
    )

    top_applications = (
        application_usage
        .drop_duplicates(
            subset=["subscriber_id"],
            keep="first",
        )
        .rename(
            columns={
                "application_id": "top_application_id",
                "application_name": "top_application_name",
                "application_category": (
                    "top_application_category"
                ),
            }
        )
    )

    return top_applications


def build_hourly_subscriber_activity(
    enriched_partition: Path,
    output_file: Path | None = None,
) -> Path:
    enriched_partition = Path(enriched_partition)

    if not enriched_partition.exists():
        raise FileNotFoundError(
            f"Enriched partition not found: {enriched_partition}"
        )

    if not enriched_partition.is_dir():
        raise NotADirectoryError(
            f"Expected an enriched partition directory: "
            f"{enriched_partition}"
        )

    input_files = sorted(
        enriched_partition.glob("*.parquet")
    )

    if not input_files:
        raise FileNotFoundError(
            f"No Parquet files found in: {enriched_partition}"
        )

    dataframes = [
        pd.read_parquet(input_file)
        for input_file in input_files
    ]

    dataframe = pd.concat(
        dataframes,
        ignore_index=True,
    )

    validate_required_columns(dataframe)

    dataframe = dataframe[
        dataframe["subscriber_enrichment_status"] == "MATCHED"
    ].copy()

    if dataframe.empty:
        raise CuratedDatasetError(
            "No matched subscribers were found in the "
            "enriched partition."
        )

    dataframe["timestamp"] = pd.to_datetime(
        dataframe["timestamp"],
        utc=True,
        errors="coerce",
    )

    dataframe = dataframe[
        dataframe["timestamp"].notna()
    ].copy()

    if dataframe.empty:
        raise CuratedDatasetError(
            "No valid timestamps were found in the "
            "enriched partition."
        )

    event_hours = (
        dataframe["timestamp"]
        .dt.floor("h")
        .unique()
    )

    if len(event_hours) != 1:
        raise CuratedDatasetError(
            "The enriched partition contains events from more than "
            "one hourly window."
        )

    window_start = pd.Timestamp(event_hours[0])
    window_end = window_start + pd.Timedelta(hours=1)

    dataframe = dataframe.sort_values(
        by=["subscriber_id", "timestamp"]
    )

    latest_records = (
        dataframe
        .drop_duplicates(
            subset=["subscriber_id"],
            keep="last",
        )
        [
            [
                "subscriber_id",
                "imsi",
                "msisdn",
                "customer_segment",
                "subscriber_status",
                "plan_id",
                "plan_name",
                "plan_type",
                "monthly_data_allowance_gb",
                "max_download_mbps",
                "max_upload_mbps",
                "technology_access",
                "tac",
                "device_vendor",
                "device_model",
                "device_os",
                "max_supported_technology",
                "cell_id",
                "city",
                "state",
                "network_technology",
            ]
        ]
        .rename(
            columns={
                "tac": "latest_tac",
                "device_vendor": "latest_device_vendor",
                "device_model": "latest_device_model",
                "device_os": "latest_device_os",
                "max_supported_technology": (
                    "latest_device_technology"
                ),
                "cell_id": "latest_cell_id",
                "city": "latest_city",
                "state": "latest_state",
                "network_technology": (
                    "latest_network_technology"
                ),
            }
        )
    )

    usage_metrics = (
        dataframe
        .groupby("subscriber_id")
        .agg(
            event_count=("event_id", "count"),

            total_bytes_dl=("bytes_dl", "sum"),
            total_bytes_ul=("bytes_ul", "sum"),
            total_bytes=("total_bytes", "sum"),

            avg_latency_ms=("latency_ms", "mean"),
            avg_packet_loss_pct=("packet_loss_pct", "mean"),

            latency_sum=("latency_ms", "sum"),
            latency_sample_count=("latency_ms", "count"),

            packet_loss_sum=("packet_loss_pct", "sum"),
            packet_loss_sample_count=("packet_loss_pct", "count"),
        )
        .reset_index()
    )

    usage_metrics["avg_latency_ms"] = (
        usage_metrics["avg_latency_ms"].round(2)
    )

    usage_metrics["avg_packet_loss_pct"] = (
        usage_metrics["avg_packet_loss_pct"].round(4)
    )

    top_applications = build_top_applications(dataframe)

    subscriber_activity = (
        latest_records
        .merge(
            usage_metrics,
            on="subscriber_id",
            how="inner",
        )
        .merge(
            top_applications,
            on="subscriber_id",
            how="left",
        )
    )

    subscriber_activity["aggregation_grain"] = "hourly"
    subscriber_activity["window_start"] = window_start
    subscriber_activity["window_end"] = window_end
    subscriber_activity["curated_at"] = datetime.now(
        timezone.utc
    )

    subscriber_activity = subscriber_activity.sort_values(
        by="subscriber_id"
    ).reset_index(drop=True)

    if output_file is None:
        output_file = build_hourly_output_path(
            enriched_partition
        )
    else:
        output_file = Path(output_file)
        output_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    table = pa.Table.from_pandas(
        subscriber_activity,
        preserve_index=False,
    )

    pq.write_table(
        table,
        output_file,
        compression="snappy",
    )
    
    return output_file

#Code for daily subscriber activity.

def validate_hourly_required_columns(dataframe: pd.DataFrame) -> None:
    missing_columns = HOURLY_REQUIRED_COLUMNS - set(dataframe.columns)

    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise CuratedDatasetError(
            f"Missing required hourly columns: {missing}"
        )

def build_daily_output_path(
    hourly_day_partition: Path,
    curated_base_dir: Path = Path("data/curated"),
    ) -> Path:
    hourly_day_partition = Path(hourly_day_partition)
    
    try:
        partition_path = hourly_day_partition.relative_to(
            Path("data/curated/subscriber_activity_hourly")
        )
    except ValueError as error:
        raise CuratedDatasetError(
            "The hourly partition must be located inside data/curated/subscriber_activity_hourly."
        ) from error

    output_directory = (
        curated_base_dir
        / "subscriber_activity_daily"
        / partition_path
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    return output_directory / "subscriber_activity_daily.parquet"

def validate_hourly_partition(
    hourly_day_partition: Path,
) -> list[Path]:
    hourly_day_partition = Path(hourly_day_partition)

    if not hourly_day_partition.exists():
        raise FileNotFoundError(
            f"Hourly partition not found: {hourly_day_partition}"
        )

    if not hourly_day_partition.is_dir():
        raise NotADirectoryError(
            f"Expected an hourly partition directory: "
            f"{hourly_day_partition}"
        )

    input_files = sorted(
        hourly_day_partition.glob(
            "hour=*/subscriber_activity_hourly.parquet"
        )
    )

    if not input_files:
        raise FileNotFoundError(
            f"No hourly Parquet files found in: "
            f"{hourly_day_partition}"
        )

    return input_files

def build_daily_subscriber_activity(
    hourly_day_partition: Path,
    output_file: Path | None = None,
) -> Path:
    hourly_day_partition = Path(hourly_day_partition)

    input_files = validate_hourly_partition(hourly_day_partition)

    dataframes = [
        pd.read_parquet(input_file)
        for input_file in input_files
    ]

    dataframe = pd.concat(
        dataframes,
        ignore_index=True,
    )

    if dataframe.empty:
        raise CuratedDatasetError(
            "No hourly subscriber activity data found in the "
            "hourly partition."
        )

    validate_hourly_required_columns(dataframe)

    dataframe["window_start"] = pd.to_datetime(
        dataframe["window_start"],
        utc=True,
        errors="coerce",
    )

    dataframe["window_end"] = pd.to_datetime(
        dataframe["window_end"],
        utc=True,
        errors="coerce",
    )

    if dataframe["window_start"].isna().any():
        raise CuratedDatasetError(
            "Invalid window_start values were found in the "
            "hourly partition."
        )

    if dataframe["window_end"].isna().any():
        raise CuratedDatasetError(
            "Invalid window_end values were found in the "
            "hourly partition."
        )

    event_days = (
        dataframe["window_start"]
        .dt.floor("D")
        .unique()
    )

    if len(event_days) != 1:
        raise CuratedDatasetError(
            "The hourly partition contains records from "
            "more than one daily window."
        )

    window_start = pd.Timestamp(event_days[0])
    window_end = window_start + pd.Timedelta(days=1)

    invalid_windows = (
        (dataframe["window_start"] < window_start)
        | (dataframe["window_start"] >= window_end)
        | (dataframe["window_end"] <= window_start)
        | (dataframe["window_end"] > window_end)
    )

    if invalid_windows.any():
        raise CuratedDatasetError(
            "The hourly partition contains windows outside "
            "the expected daily range."
        )

    latest_records = (
        dataframe
        .sort_values(
            by=["subscriber_id", "window_end", "window_start",]
        )
        .drop_duplicates(
            subset=["subscriber_id"],
            keep="last",
        )
        [
            [
                "subscriber_id",
                "imsi",
                "msisdn",
                "customer_segment",
                "subscriber_status",
                "plan_id",
                "plan_name",
                "plan_type",
                "monthly_data_allowance_gb",
                "max_download_mbps",
                "max_upload_mbps",
                "technology_access",
                "latest_tac",
                "latest_device_vendor",
                "latest_device_model",
                "latest_device_os",
                "latest_device_technology",
                "latest_cell_id",
                "latest_city",
                "latest_state",
                "latest_network_technology",
            ]
        ]
    )

    daily_metrics = (
        dataframe
        .groupby("subscriber_id")
        .agg(
            event_count=("event_count", "sum"),

            total_bytes_dl=("total_bytes_dl", "sum"),
            total_bytes_ul=("total_bytes_ul", "sum"),
            total_bytes=("total_bytes", "sum"),

            latency_sum=("latency_sum", "sum"),
            latency_sample_count=(
                "latency_sample_count",
                "sum",
            ),

            packet_loss_sum=("packet_loss_sum", "sum"),
            packet_loss_sample_count=(
                "packet_loss_sample_count",
                "sum",
            ),
        )
        .reset_index()
    )

    daily_metrics["avg_latency_ms"] = (
        daily_metrics["latency_sum"]
        .div(
            daily_metrics["latency_sample_count"]
            .replace(0, pd.NA)
        )
        .round(2)
    )

    daily_metrics["avg_packet_loss_pct"] = (
        daily_metrics["packet_loss_sum"]
        .div(
            daily_metrics["packet_loss_sample_count"]
            .replace(0, pd.NA)
        )
        .round(4)
    )

    subscriber_activity = latest_records.merge(
        daily_metrics,
        on="subscriber_id",
        how="inner",
    )

    subscriber_activity["aggregation_grain"] = "daily"
    subscriber_activity["window_start"] = window_start
    subscriber_activity["window_end"] = window_end
    subscriber_activity["curated_at"] = datetime.now(
        timezone.utc
    )

    subscriber_activity = subscriber_activity.sort_values(
        by="subscriber_id"
    ).reset_index(drop=True)

    if output_file is None:
        output_file = build_daily_output_path(
            hourly_day_partition
        )
    else:
        output_file = Path(output_file)
        output_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    table = pa.Table.from_pandas(
        subscriber_activity,
        preserve_index=False,
    )

    pq.write_table(
        table,
        output_file,
        compression="snappy",
    )

    return output_file

def load_daily_activity_history(
    input_files: list[Path],
) -> pd.DataFrame:
    if not input_files:
        raise CuratedDatasetError(
            "No daily activity files were provided."
        )

    dataframes = [
        pd.read_parquet(Path(input_file))
        for input_file in input_files
    ]

    dataframe = pd.concat(
        dataframes,
        ignore_index=True,
    )

    if dataframe.empty:
        raise CuratedDatasetError(
            "No daily subscriber activity records were found."
        )

    validate_daily_required_columns(dataframe)

    return dataframe

def validate_daily_timestamps(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    validated_dataframe = dataframe.copy()

    validated_dataframe["window_start"] = pd.to_datetime(
        validated_dataframe["window_start"],
        utc=True,
        errors="coerce",
    )

    validated_dataframe["window_end"] = pd.to_datetime(
        validated_dataframe["window_end"],
        utc=True,
        errors="coerce",
    )

    if validated_dataframe["window_start"].isna().any():
        raise CuratedDatasetError(
            "Invalid window_start values were found in the "
            "daily activity history."
        )

    if validated_dataframe["window_end"].isna().any():
        raise CuratedDatasetError(
            "Invalid window_end values were found in the "
            "daily activity history."
        )

    invalid_windows = (
        validated_dataframe["window_end"]
        <= validated_dataframe["window_start"]
    )

    if invalid_windows.any():
        raise CuratedDatasetError(
            "Daily activity windows must end after they start."
        )

    return validated_dataframe

def validate_unique_daily_windows(
    dataframe: pd.DataFrame,
) -> None:
    duplicate_mask = dataframe.duplicated(
        subset=[
            "subscriber_id",
            "window_start",
            "window_end",
        ],
        keep=False,
    )

    if duplicate_mask.any():
        raise CuratedDatasetError(
            "Duplicate daily subscriber windows were found."
        )

def load_validated_daily_activity_history(
    daily_activity_directory: Path,
) -> pd.DataFrame:
    input_files = discover_daily_activity_files(
        daily_activity_directory
    )

    dataframe = load_daily_activity_history(
        input_files
    )

    dataframe = validate_daily_timestamps(
        dataframe
    )

    validate_unique_daily_windows(
        dataframe
    )

    return dataframe