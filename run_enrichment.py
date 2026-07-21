import argparse
import logging
from pathlib import Path
from ingestion.s3_loader import upload_file_to_s3

from enrichment.enrichment_processor import (
    process_raw_file,
)


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | %(levelname)s | "
            "%(name)s | %(message)s"
        ),
    )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input-file",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--upload-to-s3",
        action="store_true",
        help=(
            "Upload the generated enriched Parquet file "
            "to Amazon S3."
        ),
    )

    return parser.parse_args()

logger = logging.getLogger(__name__)

def main() -> None:
    configure_logging()

    args = parse_arguments()

    output_file = process_raw_file(
        raw_file=args.input_file,
    )

    print(
        f"Enriched file created at: "
        f"{output_file}"
    )

    if args.upload_to_s3:
        s3_uri = upload_file_to_s3(output_file)

        logger.info(
            "Enriched file uploaded successfully: %s",
            s3_uri,
        )


if __name__ == "__main__":
    main()