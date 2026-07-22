import argparse
from datetime import UTC, date, datetime
from pathlib import Path

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


def validate_pipeline_counts(
    raw_event_count: int,
    hourly_day_partition: Path,
    daily_output_file: Path,
) -> None:
    hourly_files = sorted(
        hourly_day_partition.glob(
            "hour=*/subscriber_activity_hourly.parquet"
        )
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
    print(f"Generated events: {raw_event_count}")
    print(f"Hourly events:    {hourly_event_count}")
    print(f"Daily events:     {daily_event_count}")

    if not (
        raw_event_count
        == hourly_event_count
        == daily_event_count
    ):
        raise RuntimeError(
            "Pipeline count validation failed: "
            "generated, hourly and daily event counts "
            "do not match."
        )

    print("Validation result: PASSED")


def run_daily_pipeline(
    processing_date: date,
    hours: list[int],
    events_per_hour: int,
) -> Path:
    generated_event_count = 0

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

        generated_event_count += len(events)

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
        raw_event_count=generated_event_count,
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
    )


if __name__ == "__main__":
    main()