from pathlib import Path

from analytics.subscriber_profiles import (
    build_daily_subscriber_activity,
)

hourly_day_partition = Path(
    "data/curated/subscriber_activity_hourly/"
    "year=2026/month=07/day=22"
)

output_file = build_daily_subscriber_activity(
    hourly_day_partition
)

print(
    f"Created {output_file}"
)