from pathlib import Path

from enrichment.enrichment_processor import (
    process_raw_file,
)

raw_files = sorted(
    Path(
        "data/raw/year=2026/month=07/day=22"
    ).glob(
        "hour=*/*.jsonl"
    )
)

print(
    f"Found {len(raw_files)} raw files."
)

for raw_file in raw_files:

    print(
        f"Processing {raw_file}"
    )

    output_file = process_raw_file(
        raw_file
    )

    print(
        f"Created {output_file}"
    )