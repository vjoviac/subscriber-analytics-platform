# infrastructure/logging_config.py

import logging
from pathlib import Path

from config.settings import (
    LOG_DIRECTORY,
    LOG_LEVEL,
)


LOG_FORMAT = (
    "%(asctime)s | %(levelname)s | "
    "%(name)s | %(message)s"
)

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging(
    run_id: str,
    log_directory: Path = LOG_DIRECTORY,
) -> Path:
    """
    Configure console and file logging for one pipeline run.

    Returns the generated log file path.
    """
    log_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    log_file = (
        log_directory
        / f"pipeline_{run_id}.log"
    )

    numeric_level = getattr(
        logging,
        LOG_LEVEL,
        logging.INFO,
    )

    formatter = logging.Formatter(
        fmt=LOG_FORMAT,
        datefmt=DATE_FORMAT,
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Avoid duplicated handlers when tests or repeated
    # executions configure logging more than once.
    root_logger.handlers.clear()

    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(
        filename=log_file,
        encoding="utf-8",
    )
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(formatter)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    return log_file