import argparse
import logging

from datetime import UTC, datetime
from pathlib import Path

from config.settings import (
    DEFAULT_EVENT_COUNT,
    RAW_DATA_DIRECTORY,
)
from generators.event_generator import generate_events
from infrastructure.logging_config import configure_logging
from ingestion.s3_loader import upload_file_to_s3
from storage.storage_manager import save_events_to_jsonl


logger = logging.getLogger(__name__)


def build_run_id() -> str:
    """
    Build a unique identifier for one ingestion execution.
    """
    return datetime.now(UTC).strftime(
        "%Y%m%dT%H%M%S%fZ"
    )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate synthetic telecom subscriber events."
        )
    )

    parser.add_argument(
        "--events",
        type=int,
        default=DEFAULT_EVENT_COUNT,
        help=(
            "Total number of events to generate. "
            f"Default: {DEFAULT_EVENT_COUNT}."
        ),
    )

    parser.add_argument(
        "--upload-s3",
        action="store_true",
        help=(
            "Upload the generated JSONL file "
            "to Amazon S3."
        ),
    )

    return parser.parse_args()


def validate_arguments(
    events: int,
) -> None:
    if events <= 0:
        raise ValueError(
            "--events must be greater than zero."
        )


def build_output_file(
    processing_time: datetime | None = None,
) -> Path:
    now = processing_time or datetime.now(UTC)

    file_name = now.strftime(
        "subscriber_events_%Y%m%d_%H%M%S.jsonl"
    )

    return (
        RAW_DATA_DIRECTORY
        / f"year={now:%Y}"
        / f"month={now:%m}"
        / f"day={now:%d}"
        / f"hour={now:%H}"
        / file_name
    )


def main() -> None:
    run_id = build_run_id()

    log_file = configure_logging(
        run_id=run_id
    )

    logger.info(
        "process=event_generation "
        "status=started run_id=%s",
        run_id,
    )

    try:
        args = parse_arguments()

        validate_arguments(
            events=args.events
        )

        events = generate_events(
            total_events=args.events
        )

        output_file = build_output_file()

        save_events_to_jsonl(
            events=events,
            output_file=output_file,
        )

        logger.info(
            "process=event_generation "
            "status=completed events=%d "
            "output_file=%s",
            len(events),
            output_file,
        )

        if args.upload_s3:
            logger.info(
                "process=s3_upload "
                "status=started local_file=%s",
                output_file,
            )

            s3_uri = upload_file_to_s3(
                output_file
            )

            logger.info(
                "process=s3_upload "
                "status=completed s3_uri=%s",
                s3_uri,
            )

        logger.info(
            "process=event_generation "
            "status=succeeded run_id=%s "
            "log_file=%s",
            run_id,
            log_file,
        )

    except Exception:
        logger.exception(
            "process=event_generation "
            "status=failed run_id=%s",
            run_id,
        )
        raise


if __name__ == "__main__":
    main()