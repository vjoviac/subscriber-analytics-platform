from pathlib import Path

from analytics.subscriber_profiles import (
    build_hourly_subscriber_activity,
)

enriched_partitions = sorted(
    Path(
        "data/enriched/year=2026/month=07/day=22"
    ).glob(
        "hour=*"
    )
)

print(
    f"Found {len(enriched_partitions)} partitions."
)

for partition in enriched_partitions:

    print(
        f"Processing {partition}"
    )

    output_file = build_hourly_subscriber_activity(
        partition
    )

    print(
        f"Created {output_file}"
    )