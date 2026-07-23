# config/settings.py

import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


def get_positive_integer(
    variable_name: str,
    default: int,
) -> int:
    raw_value = os.getenv(
        variable_name,
        str(default),
    )

    try:
        value = int(raw_value)
    except ValueError as error:
        raise ValueError(
            f"{variable_name} must be an integer. "
            f"Received: {raw_value!r}"
        ) from error

    if value <= 0:
        raise ValueError(
            f"{variable_name} must be greater than zero. "
            f"Received: {value}"
        )

    return value


DATA_DIRECTORY = Path(
    os.getenv("DATA_DIRECTORY", "data")
)

RAW_DATA_DIRECTORY = Path(
    os.getenv(
        "RAW_DATA_DIRECTORY",
        str(DATA_DIRECTORY / "raw"),
    )
)

ENRICHED_DATA_DIRECTORY = Path(
    os.getenv(
        "ENRICHED_DATA_DIRECTORY",
        str(DATA_DIRECTORY / "enriched"),
    )
)

CURATED_DATA_DIRECTORY = Path(
    os.getenv(
        "CURATED_DATA_DIRECTORY",
        str(DATA_DIRECTORY / "curated"),
    )
)

HOURLY_ACTIVITY_DIRECTORY = Path(
    os.getenv(
        "HOURLY_ACTIVITY_DIRECTORY",
        str(
            CURATED_DATA_DIRECTORY
            / "subscriber_activity_hourly"
        ),
    )
)

DAILY_ACTIVITY_DIRECTORY = Path(
    os.getenv(
        "DAILY_ACTIVITY_DIRECTORY",
        str(
            CURATED_DATA_DIRECTORY
            / "subscriber_activity_daily"
        ),
    )
)

LOG_DIRECTORY = Path(
    os.getenv("LOG_DIRECTORY", "logs")
)

REPORT_DIRECTORY = Path(
    os.getenv(
        "REPORT_DIRECTORY",
        "reports/pipeline_runs",
    )
)

DEFAULT_EVENT_COUNT = get_positive_integer(
    variable_name="DEFAULT_EVENT_COUNT",
    default=500,
)

LOG_LEVEL = os.getenv(
    "LOG_LEVEL",
    "INFO",
).upper()