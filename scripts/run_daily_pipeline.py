import argparse
from datetime import UTC, date, datetime
from pathlib import Path

from dataclasses import dataclass
import shutil

import pandas as pd

from analytics.subscriber_profiles import (
    build_daily_subscriber_activity,
    build_hourly_subscriber_activity,
)
from enrichment.enrichment_processor import (
    process_raw_file,
)
from generators.event_generator import (
    generate_events,
)
from main import (
    build_output_file,
    save_events_to_jsonl,
)

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

def build_hourly_pipeline_paths(
    processing_time: datetime,
) -> HourlyPipelinePaths:
    timestamp = processing_time.strftime(
        "%Y%m%d_%H0000"
    )

    partition = (
        f"year={processing_time.year:04d}"
        f"/month={processing_time.month:02d}"
        f"/day={processing_time.day:02d}"
        f"/hour={processing_time.hour:02d}"
    )

    raw_file = (
        Path("data/raw")
        / partition
        / f"subscriber_events_{timestamp}.jsonl"
    )

    enriched_file = (
        Path("data/enriched")
        / partition
        / f"enriched_subscriber_events_{timestamp}.parquet"
    )

    hourly_file = (
        Path(
            "data/curated/subscriber_activity_hourly"
        )
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
        default=500,
        help="Number of events to generate per hour.",
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
        print(
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
        Path("data/enriched")
        / f"year={processing_time.year:04d}"
        / f"month={processing_time.month:02d}"
        / f"day={processing_time.day:02d}"
        / f"hour={processing_time.hour:02d}"
    )


def build_hourly_day_partition(
    processing_date: date,
) -> Path:
    return (
        Path(
            "data/curated/subscriber_activity_hourly"
        )
        / f"year={processing_date.year:04d}"
        / f"month={processing_date.month:02d}"
        / f"day={processing_date.day:02d}"
    )

def prepare_hour_for_processing(
    paths: HourlyPipelinePaths,
    skip_existing: bool,
    overwrite: bool,
) -> bool:
    existing_paths = paths.existing_paths

    if not existing_paths:
        return True

    if skip_existing:
        print(
            "Existing outputs detected. "
            "Skipping this hour:"
        )

        for path in existing_paths:
            print(f"  - {path}")

        return False

    if overwrite:
        print(
            "Existing outputs detected. "
            "Removing them before reprocessing:"
        )

        for path in existing_paths:
            print(f"  - {path}")
            path.unlink()

        remove_empty_parent_directories(
            paths=existing_paths
        )

        return True

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
    data_directory = Path("data").resolve()

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
) -> None:
    raw_day_partition = (
        Path("data/raw")
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

    print()
    print("Pipeline validation")
    print("-------------------")
    print(f"Raw events:     {raw_event_count}")
    print(f"Hourly events:  {hourly_event_count}")
    print(f"Daily events:   {daily_event_count}")

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

    print("Validation result: PASSED")

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
    
    print(
        f"Starting pipeline for {processing_date.isoformat()}"
    )
    print(
        f"Hours: {', '.join(f'{hour:02d}' for hour in hours)}"
    )
    print(f"Events per hour: {events_per_hour}")
    print()

    for hour in hours:
        processing_time = build_processing_time(
            processing_date,
            hour,
        )

        paths = build_hourly_pipeline_paths(
            processing_time
        )

        should_process = prepare_hour_for_processing(
            paths=paths,
            skip_existing=skip_existing,
            overwrite=overwrite,
        )

        if not should_process:
            print()
            continue

        print(
            f"[{hour:02d}:00] Generating raw events..."
        )

        events = generate_events(
            total_events=events_per_hour,
            event_time=processing_time,
        )

        raw_output_file = build_output_file(
            processing_time=processing_time,
        )

        save_events_to_jsonl(
            events,
            raw_output_file,
        )

        print(
            f"[{hour:02d}:00] Raw file: "
            f"{raw_output_file}"
        )

        print(
            f"[{hour:02d}:00] Enriching raw events..."
        )

        enriched_output_file = process_raw_file(
            raw_output_file
        )

        print(
            f"[{hour:02d}:00] Enriched file: "
            f"{enriched_output_file}"
        )

        enriched_partition = build_enriched_partition(
            processing_time
        )

        print(
            f"[{hour:02d}:00] Building hourly metrics..."
        )

        hourly_output_file = (
            build_hourly_subscriber_activity(
                enriched_partition
            )
        )

        print(
            f"[{hour:02d}:00] Hourly file: "
            f"{hourly_output_file}"
        )
        print()

    hourly_day_partition = build_hourly_day_partition(
        processing_date
    )

    print("Building daily subscriber activity...")

    daily_output_file = (
        build_daily_subscriber_activity(
            hourly_day_partition
        )
    )

    print(f"Daily file: {daily_output_file}")

    validate_pipeline_counts(
        processing_date=processing_date,
        hourly_day_partition=hourly_day_partition,
        daily_output_file=daily_output_file,
    )

    return daily_output_file


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