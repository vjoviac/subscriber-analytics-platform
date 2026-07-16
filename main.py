from datetime import UTC, datetime
from pathlib import Path

from generators.event_generator import generate_events
from storage.storage_manager import save_events_to_jsonl
from ingestion.s3_loader import upload_file_to_s3


def build_output_file() -> Path:

    now = datetime.now(UTC)

    file_name = now.strftime(
        "subscriber_events_%Y%m%d_%H%M%S.jsonl"
    )

    return Path(
        "data"
    ) / Path(
        "raw"
    ) / Path(
        f"year={now:%Y}"
    ) / Path(
        f"month={now:%m}"
    ) / Path(
        f"day={now:%d}"
    ) / Path(
        f"hour={now:%H}"
    ) / Path(
        file_name
    )


def main() -> None:
    total_events = 100

    events = generate_events(total_events)
    output_file = build_output_file()

    save_events_to_jsonl(
        events=events,
        output_file=output_file,
    )

    s3_uri = upload_file_to_s3(output_file)

    print(
        f"Generated {total_events} events: "
        f"{output_file}"
    )

    print(f"Uploaded file to: {s3_uri}")


if __name__ == "__main__":
    main()