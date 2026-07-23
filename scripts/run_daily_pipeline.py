import argparse
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from time import perf_counter

import pandas as pd

from analytics.subscriber_profiles import (
    build_daily_subscriber_activity,
    build_hourly_subscriber_activity,
)
from config.settings import (
    DATA_DIRECTORY,
    DEFAULT_EVENT_COUNT,
    ENRICHED_DATA_DIRECTORY,
    HOURLY_ACTIVITY_DIRECTORY,
    RAW_DATA_DIRECTORY,
    REPORT_DIRECTORY,
)
from enrichment.enrichment_processor import (
    process_raw_file,
)
from generators.event_generator import (
    generate_events,
)
from infrastructure.logging_config import (
    configure_logging,
)
from main import build_output_file
from storage.storage_manager import (
    save_events_to_jsonl,
)

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class HourlyPipelinePaths:
    raw_file: Path
    enriched_file: Path
    hourly_file: Path

    @property
    def existing_paths(self) -> list[Path]:
        return [
            path
            for path in (
                self.raw_file,
                self.enriched_file,
                self.hourly_file,
            )
            if path.exists()
        ]

@dataclass
class PipelineRunReport:
    run_id: str
    processing_date: str
    requested_hours: list[int]
    events_per_hour: int
    execution_mode: str

    status: str = "RUNNING"
    validation_status: str = "NOT_RUN"

    started_at: str = ""
    completed_at: str | None = None
    duration_seconds: float | None = None

    processed_hours: list[int] = field(
        default_factory=list
    )
    skipped_hours: list[int] = field(
        default_factory=list
    )
    reprocessed_hours: list[int] = field(
        default_factory=list
    )

    generated_event_count: int = 0
    raw_event_count: int = 0
    hourly_event_count: int = 0
    daily_event_count: int = 0

    raw_files: list[str] = field(
        default_factory=list
    )
    enriched_files: list[str] = field(
        default_factory=list
    )
    hourly_files: list[str] = field(
        default_factory=list
    )

    daily_file: str | None = None
    log_file: str | None = None
    report_file: str | None = None

    error_type: str | None = None
    error_message: str | None = None

def build_run_id() -> str:
    return datetime.now(UTC).strftime(
        "%Y%m%dT%H%M%S%fZ"
    )


def determine_execution_mode(
    skip_existing: bool,
    overwrite: bool,
) -> str:
    if overwrite:
        return "OVERWRITE"

    if skip_existing:
        return "SKIP_EXISTING"

    return "SAFE"

def build_report_file(
    run_id: str,
    report_directory: Path = REPORT_DIRECTORY,
) -> Path:
    return (
        report_directory
        / f"pipeline_run_{run_id}.json"
    )

def write_pipeline_report(
    report: PipelineRunReport,
    report_file: Path,
) -> None:
    report_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with report_file.open(
        mode="w",
        encoding="utf-8",
    ) as output_file:
        json.dump(
            asdict(report),
            output_file,
            indent=2,
            ensure_ascii=False,
        )

def build_hourly_pipeline_paths(
    processing_time: datetime,
) -> HourlyPipelinePaths:
    timestamp = processing_time.strftime(
        "%Y%m%d_%H0000"
    )

    partition = (
        Path(f"year={processing_time.year:04d}")
        / f"month={processing_time.month:02d}"
        / f"day={processing_time.day:02d}"
        / f"hour={processing_time.hour:02d}"
    )

    raw_file = (
        RAW_DATA_DIRECTORY
        / partition
        / f"subscriber_events_{timestamp}.jsonl"
    )

    enriched_file = (
        ENRICHED_DATA_DIRECTORY
        / partition
        / (
            "enriched_subscriber_events_"
            f"{timestamp}.parquet"
        )
    )

    hourly_file = (
        HOURLY_ACTIVITY_DIRECTORY
        / partition
        / "subscriber_activity_hourly.parquet"
    )

    return HourlyPipelinePaths(
        raw_file=raw_file,
        enriched_file=enriched_file,
        hourly_file=hourly_file,
    )

def parse_date(value: str) -> date:
    """
    Convert a YYYY-MM-DD argument into a date object.
    """
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            f"Invalid date '{value}'. "
            "Expected format: YYYY-MM-DD."
        ) from error


def parse_hour(value: str) -> int:
    """
    Validate an hour supplied through the command line.
    """
    try:
        hour = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            f"Invalid hour '{value}'. Expected an integer."
        ) from error

    if not 0 <= hour <= 23:
        raise argparse.ArgumentTypeError(
            f"Invalid hour '{hour}'. "
            "Expected a value between 0 and 23."
        )

    return hour


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the subscriber analytics pipeline for one day."
        )
    )

    parser.add_argument(
        "--date",
        type=parse_date,
        required=True,
        help="Processing date in YYYY-MM-DD format.",
    )

    parser.add_argument(
        "--hours",
        type=parse_hour,
        nargs="+",
        required=True,
        help=(
            "Hours to process. Example: "
            "--hours 8 9 10 11"
        ),
    )

    parser.add_argument(
        "--events-per-hour",
        type=int,
        default=DEFAULT_EVENT_COUNT,
        help=(
            "Number of events to generate per hour. "
            f"Default: {DEFAULT_EVENT_COUNT}."
        ),
    )

    processing_mode = parser.add_mutually_exclusive_group()

    processing_mode.add_argument(
        "--skip-existing",
        action="store_true",
        help=(
            "Skip hours whose raw, enriched or hourly "
            "outputs already exist."
        ),
    )

    processing_mode.add_argument(
        "--overwrite",
        action="store_true",
        help=(
            "Delete existing outputs for the requested "
            "hours before processing them again."
        ),
    )

    return parser


def validate_arguments(
    hours: list[int],
    events_per_hour: int,
) -> list[int]:
    if events_per_hour <= 0:
        raise ValueError(
            "events-per-hour must be greater than zero."
        )

    unique_hours = sorted(set(hours))

    if len(unique_hours) != len(hours):
        logger.warning(
            "Warning: duplicate hours were removed."
        )

    return unique_hours


def build_processing_time(
    processing_date: date,
    hour: int,
) -> datetime:
    return datetime(
        year=processing_date.year,
        month=processing_date.month,
        day=processing_date.day,
        hour=hour,
        tzinfo=UTC,
    )


def build_enriched_partition(
    processing_time: datetime,
) -> Path:
    return (
        ENRICHED_DATA_DIRECTORY
        / f"year={processing_time.year:04d}"
        / f"month={processing_time.month:02d}"
        / f"day={processing_time.day:02d}"
        / f"hour={processing_time.hour:02d}"
    )


def build_hourly_day_partition(
    processing_date: date,
) -> Path:
    return (
        HOURLY_ACTIVITY_DIRECTORY
        / f"year={processing_date.year:04d}"
        / f"month={processing_date.month:02d}"
        / f"day={processing_date.day:02d}"
    )

def prepare_hour_for_processing(
    paths: HourlyPipelinePaths,
    skip_existing: bool,
    overwrite: bool,
) -> str:
    existing_paths = paths.existing_paths

    if not existing_paths:
        return "PROCESS"

    if skip_existing:
        logger.warning(
            "hour_action=skip reason=existing_outputs "
            "existing_files=%s",
            [str(path) for path in existing_paths],
        )

        return "SKIP"

    if overwrite:
        logger.warning(
            "hour_action=reprocess reason=existing_outputs "
            "existing_files=%s",
            [str(path) for path in existing_paths],
        )

        for path in existing_paths:
            logger.info(
                "action=delete path=%s",
                path,
            )
            path.unlink()

        remove_empty_parent_directories(
            paths=existing_paths
        )

        return "REPROCESS"

    existing_outputs = "\n".join(
        f"  - {path}"
        for path in existing_paths
    )

    raise FileExistsError(
        "Pipeline outputs already exist for the "
        "requested hour.\n"
        f"{existing_outputs}\n"
        "Use --skip-existing to keep them or "
        "--overwrite to rebuild them."
    )

def remove_empty_parent_directories(
    paths: list[Path],
) -> None:
    data_directory = DATA_DIRECTORY.resolve()

    for path in paths:
        parent = path.parent

        while parent.exists():
            resolved_parent = parent.resolve()

            if resolved_parent == data_directory:
                break

            try:
                parent.rmdir()
            except OSError:
                break

            parent = parent.parent

def validate_pipeline_counts(
    processing_date: date,
    hourly_day_partition: Path,
    daily_output_file: Path,
) -> dict[str, int]:
    raw_day_partition = (
        RAW_DATA_DIRECTORY
        / f"year={processing_date.year:04d}"
        / f"month={processing_date.month:02d}"
        / f"day={processing_date.day:02d}"
    )

    raw_files = sorted(
        raw_day_partition.glob("hour=*/*.jsonl")
    )

    if not raw_files:
        raise FileNotFoundError(
            f"No raw JSONL files found in: "
            f"{raw_day_partition}"
        )

    raw_event_count = sum(
        count_jsonl_records(raw_file)
        for raw_file in raw_files
    )

    hourly_files = sorted(
        hourly_day_partition.glob(
            "hour=*/subscriber_activity_hourly.parquet"
        )
    )

    if not hourly_files:
        raise FileNotFoundError(
            f"No hourly Parquet files found in: "
            f"{hourly_day_partition}"
        )

    hourly_event_count = sum(
        int(
            pd.read_parquet(
                hourly_file,
                columns=["event_count"],
            )["event_count"].sum()
        )
        for hourly_file in hourly_files
    )

    daily_dataframe = pd.read_parquet(
        daily_output_file,
        columns=["event_count"],
    )

    daily_event_count = int(
        daily_dataframe["event_count"].sum()
    )

    logger.info(
        "stage=validation status=completed "
        "raw_events=%d hourly_events=%d "
        "daily_events=%d",
        raw_event_count,
        hourly_event_count,
        daily_event_count,
    )

    if not (
        raw_event_count
        == hourly_event_count
        == daily_event_count
    ):
        raise RuntimeError(
            "Pipeline count validation failed: "
            "raw, hourly and daily event counts "
            "do not match."
        )

    logger.info(
        "stage=validation result=passed"
    )
    return {
        "raw_event_count": raw_event_count,
        "hourly_event_count": hourly_event_count,
        "daily_event_count": daily_event_count,
    }

def count_jsonl_records(file_path: Path) -> int:
    """
    Count non-empty records in a JSONL file.
    """
    with file_path.open(
        mode="r",
        encoding="utf-8",
    ) as input_file:
        return sum(
            1
            for line in input_file
            if line.strip()
        )

def run_daily_pipeline(
    processing_date: date,
    hours: list[int],
    events_per_hour: int,
    skip_existing: bool = False,
    overwrite: bool = False,
) -> Path:
    run_id = build_run_id()
    started_at = datetime.now(UTC)
    start_counter = perf_counter()

    log_file = configure_logging(
        run_id=run_id
    )

    report_file = build_report_file(
        run_id=run_id
    )

    report = PipelineRunReport(
        run_id=run_id,
        processing_date=processing_date.isoformat(),
        requested_hours=hours,
        events_per_hour=events_per_hour,
        execution_mode=determine_execution_mode(
            skip_existing=skip_existing,
            overwrite=overwrite,
        ),
        started_at=started_at.isoformat(),
        log_file=str(log_file),
        report_file=str(report_file),
    )

    logger.info(
        "pipeline_status=started run_id=%s "
        "processing_date=%s hours=%s "
        "events_per_hour=%d execution_mode=%s",
        run_id,
        processing_date.isoformat(),
        hours,
        events_per_hour,
        report.execution_mode,
    )

    try:
        for hour in hours:
            processing_time = build_processing_time(
                processing_date,
                hour,
            )

            paths = build_hourly_pipeline_paths(
                processing_time
            )

            processing_action = (
                prepare_hour_for_processing(
                    paths=paths,
                    skip_existing=skip_existing,
                    overwrite=overwrite,
                )
            )

            if processing_action == "SKIP":
                report.skipped_hours.append(hour)

                logger.info(
                    "hour=%02d status=skipped",
                    hour,
                )
                continue

            if processing_action == "REPROCESS":
                report.reprocessed_hours.append(hour)

                logger.info(
                    "hour=%02d status=reprocessing",
                    hour,
                )

            logger.info(
                "hour=%02d stage=generation "
                "status=started",
                hour,
            )

            events = generate_events(
                total_events=events_per_hour,
                event_time=processing_time,
            )

            raw_output_file = build_output_file(
                processing_time=processing_time,
            )

            save_events_to_jsonl(
                events=events,
                output_file=raw_output_file,
            )

            logger.info(
                "hour=%02d stage=generation "
                "status=completed events=%d "
                "output_file=%s",
                hour,
                len(events),
                raw_output_file,
            )

            logger.info(
                "hour=%02d stage=enrichment "
                "status=started",
                hour,
            )

            enriched_output_file = process_raw_file(
                raw_output_file
            )

            logger.info(
                "hour=%02d stage=enrichment "
                "status=completed output_file=%s",
                hour,
                enriched_output_file,
            )

            enriched_partition = (
                build_enriched_partition(
                    processing_time
                )
            )

            logger.info(
                "hour=%02d "
                "stage=hourly_aggregation "
                "status=started",
                hour,
            )

            hourly_output_file = (
                build_hourly_subscriber_activity(
                    enriched_partition
                )
            )

            logger.info(
                "hour=%02d "
                "stage=hourly_aggregation "
                "status=completed output_file=%s",
                hour,
                hourly_output_file,
            )

            report.processed_hours.append(hour)
            report.generated_event_count += len(events)

            report.raw_files.append(
                str(raw_output_file)
            )
            report.enriched_files.append(
                str(enriched_output_file)
            )
            report.hourly_files.append(
                str(hourly_output_file)
            )

        hourly_day_partition = (
            build_hourly_day_partition(
                processing_date
            )
        )

        logger.info(
            "stage=daily_aggregation status=started"
        )

        daily_output_file = (
            build_daily_subscriber_activity(
                hourly_day_partition
            )
        )

        logger.info(
            "stage=daily_aggregation "
            "status=completed output_file=%s",
            daily_output_file,
        )

        report.daily_file = str(daily_output_file)

        validation_counts = validate_pipeline_counts(
            processing_date=processing_date,
            hourly_day_partition=(
                hourly_day_partition
            ),
            daily_output_file=daily_output_file,
        )

        report.raw_event_count = (
            validation_counts["raw_event_count"]
        )
        report.hourly_event_count = (
            validation_counts["hourly_event_count"]
        )
        report.daily_event_count = (
            validation_counts["daily_event_count"]
        )

        report.validation_status = "PASSED"
        report.status = "SUCCEEDED"

        return daily_output_file

    except Exception as error:
        report.status = "FAILED"

        if isinstance(error, RuntimeError):
            report.validation_status = "FAILED"

        report.error_type = type(error).__name__
        report.error_message = str(error)

        logger.exception(
            "pipeline_status=failed run_id=%s",
            run_id,
        )

        raise

    finally:
        completed_at = datetime.now(UTC)

        report.completed_at = (
            completed_at.isoformat()
        )

        report.duration_seconds = round(
            perf_counter() - start_counter,
            3,
        )

        write_pipeline_report(
            report=report,
            report_file=report_file,
        )

        logger.info(
            "pipeline_status=%s run_id=%s "
            "duration_seconds=%.3f "
            "report_file=%s",
            report.status.lower(),
            run_id,
            report.duration_seconds,
            report_file,
        )


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()

    hours = validate_arguments(
        hours=args.hours,
        events_per_hour=args.events_per_hour,
    )

    run_daily_pipeline(
        processing_date=args.date,
        hours=hours,
        events_per_hour=args.events_per_hour,
        skip_existing=args.skip_existing,
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    main()