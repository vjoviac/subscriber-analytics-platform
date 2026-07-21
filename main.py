import argparse
import logging

from datetime import UTC, datetime
from pathlib import Path

from generators.event_generator import generate_events
from storage.storage_manager import save_events_to_jsonl
from ingestion.s3_loader import upload_file_to_s3
from infrastructure.aws_config import DEFAULT_EVENT_COUNT

from infrastructure.logging_config import configure_logging

#Temporary import for testing
from generators.event_generator import generate_event
from enrichment.event_enricher import enrich_event
import json

logger = logging.getLogger(__name__)

def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate synthetic telecom subscriber events."
    )
    parser.add_argument(
        "--events",
        type=int,
        default=DEFAULT_EVENT_COUNT,
        help="Total number of events to generate (default: 100)",
    )
    parser.add_argument(
        "--upload-s3",
        action="store_true",
        help="Upload the generated JSONL file to Amazon S3.",
    )
    return parser.parse_args()

def build_output_file() -> Path:

    now = datetime.now(UTC)

    file_name = now.strftime(
        "subscriber_events_%Y%m%d_%H%M%S.jsonl"
    )

    return (
        Path("data")
        / "raw"
        / f"year={now:%Y}"
        / f"month={now:%m}"
        / f"day={now:%d}"
        / f"hour={now:%H}"
        / file_name
    )


def main() -> None:
    try:
        configure_logging()
        args = parse_arguments()
        
        events = generate_events(args.events)

        output_file = build_output_file()

        save_events_to_jsonl(
            events=events,
            output_file=output_file,
        )

        logger.info(
            "Generated %s events at %s",
            args.events,
            output_file,
        )

        if args.upload_s3:
            s3_uri = upload_file_to_s3(output_file)
            logger.info(
                "Uploaded file to %s",
                s3_uri,
            )
    except Exception:
        logger.exception("Ingestion process failed.")
        raise


if __name__ == "__main__":
    main()