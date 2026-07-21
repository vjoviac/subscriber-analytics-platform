import json
import logging
from pathlib import Path
from datetime import datetime

import pyarrow as pa
import pyarrow.parquet as pq

from enrichment.event_enricher import enrich_event

ENRICHED_EVENT_SCHEMA = pa.schema(
    [
        pa.field("event_id", pa.string(), nullable=False),
        pa.field("timestamp", pa.timestamp("us",tz="UTC"), nullable=False),
        pa.field("imsi", pa.string()),
        pa.field("msisdn", pa.string()),
        pa.field("tac", pa.string()),
        pa.field("cell_id", pa.string()),
        pa.field("application_id", pa.string()),
        pa.field("bytes_dl", pa.int64()),
        pa.field("bytes_ul", pa.int64()),
        pa.field("total_bytes", pa.int64()),
        pa.field("latency_ms", pa.int64()),
        pa.field("packet_loss_pct", pa.float64()),

        pa.field("subscriber_id", pa.string()),
        pa.field("plan_id", pa.string()),
        pa.field("customer_segment", pa.string()),
        pa.field("subscriber_status", pa.string()),
        pa.field(
            "subscriber_enrichment_status",
            pa.string(),
        ),
        pa.field(
            "subscriber_enrichment_reason",
            pa.string(),
        ),

        pa.field("plan_name", pa.string()),
        pa.field("plan_type", pa.string()),
        pa.field(
            "monthly_data_allowance_gb",
            pa.int64(),
        ),
        pa.field("max_download_mbps", pa.int64()),
        pa.field("max_upload_mbps", pa.int64()),
        pa.field(
            "technology_access",
            pa.list_(pa.string()),
        ),
        pa.field(
            "plan_enrichment_status",
            pa.string(),
        ),
        pa.field(
            "plan_enrichment_reason",
            pa.string(),
        ),

        pa.field("device_vendor", pa.string()),
        pa.field("device_model", pa.string()),
        pa.field("device_os", pa.string()),
        pa.field(
            "max_supported_technology",
            pa.string(),
        ),
        pa.field(
            "device_enrichment_status",
            pa.string(),
        ),
        pa.field(
            "device_enrichment_reason",
            pa.string(),
        ),

        pa.field("city", pa.string()),
        pa.field("state", pa.string()),
        pa.field(
            "network_technology",
            pa.string(),
        ),
        pa.field(
            "network_enrichment_status",
            pa.string(),
        ),
        pa.field(
            "network_enrichment_reason",
            pa.string(),
        ),

        pa.field("application_name", pa.string()),
        pa.field(
            "application_category",
            pa.string(),
        ),
        pa.field(
            "application_traffic_profile",
            pa.string(),
        ),
        pa.field(
            "application_latency_sensitivity",
            pa.string(),
        ),
        pa.field(
            "application_packet_loss_sensitivity",
            pa.string(),
        ),
        pa.field(
            "application_enrichment_status",
            pa.string(),
        ),
        pa.field(
            "application_enrichment_reason",
            pa.string(),
        ),
    ]
)

logger = logging.getLogger(__name__)


class EnrichmentProcessingError(Exception):
    """
    Raised when an enrichment file cannot be processed.
    """

def prepare_event_for_parquet(
    enriched_event: dict,
) -> dict:
    """
    Convert enriched event values to their Parquet types.
    """
    prepared_event = dict(enriched_event)

    timestamp = prepared_event.get("timestamp")

    if isinstance(timestamp, str):
        prepared_event["timestamp"] = (
            datetime.fromisoformat(timestamp)
        )

    return prepared_event

def build_enriched_output_path(
    raw_file: Path,
    raw_base_dir: Path = Path("data/raw"),
    enriched_base_dir: Path = Path("data/enriched"),
) -> Path:
    """
    Build the enriched output path while preserving the raw
    Hive-style partition structure.

    Example:
        data/raw/year=2026/month=07/day=21/hour=19/file.jsonl

    Becomes:
        data/enriched/year=2026/month=07/day=21/hour=19/
        enriched_file.parquet
    """
    try:
        relative_path = raw_file.relative_to(raw_base_dir)
    except ValueError as exc:
        raise EnrichmentProcessingError(
            f"Raw file '{raw_file}' is not located under "
            f"'{raw_base_dir}'"
        ) from exc

    output_directory = (
        enriched_base_dir / relative_path.parent
    )

    output_filename = (
        f"enriched_{relative_path.stem}.parquet"
    )

    return output_directory / output_filename


def process_raw_file(
    raw_file: Path,
    raw_base_dir: Path = Path("data/raw"),
    enriched_base_dir: Path = Path("data/enriched"),
) -> Path:
    """
    Read a raw JSONL file, enrich each valid event, and write
    the resulting records to a compressed Parquet file.

    Invalid JSON records and records that cannot be enriched are
    logged and skipped without stopping the complete file.
    """
    if not raw_file.exists():
        raise EnrichmentProcessingError(
            f"Raw file not found: {raw_file}"
        )

    if not raw_file.is_file():
        raise EnrichmentProcessingError(
            f"Raw path is not a file: {raw_file}"
        )

    output_file = build_enriched_output_path(
        raw_file=raw_file,
        raw_base_dir=raw_base_dir,
        enriched_base_dir=enriched_base_dir,
    )

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    processed_records = 0
    skipped_records = 0
    enriched_events: list[dict] = []

    try:
        with raw_file.open(
            mode="r",
            encoding="utf-8",
        ) as source:
            for line_number, line in enumerate(
                source,
                start=1,
            ):
                stripped_line = line.strip()

                if not stripped_line:
                    continue

                try:
                    raw_event = json.loads(stripped_line)
                    enriched_event = enrich_event(raw_event)

                    enriched_events.append(prepare_event_for_parquet(enriched_event))
                    processed_records += 1

                except json.JSONDecodeError as exc:
                    skipped_records += 1

                    logger.warning(
                        "Skipping invalid JSON record in %s "
                        "at line %s: %s",
                        raw_file,
                        line_number,
                        exc,
                    )

                except Exception:
                    skipped_records += 1

                    logger.exception(
                        "Failed to enrich record in %s "
                        "at line %s",
                        raw_file,
                        line_number,
                    )

    except OSError as exc:
        raise EnrichmentProcessingError(
            f"Unable to read raw file '{raw_file}'"
        ) from exc

    if not enriched_events:
        raise EnrichmentProcessingError(
            f"No valid records were enriched from '{raw_file}'"
        )

    temporary_output_file = output_file.with_suffix(
        ".parquet.tmp"
    )

    try:
        table = pa.Table.from_pylist(
            enriched_events,
            schema=ENRICHED_EVENT_SCHEMA,
        )

        pq.write_table(
            table,
            temporary_output_file,
            compression="snappy",
        )

        temporary_output_file.replace(output_file)

    except (OSError, pa.ArrowException) as exc:
        temporary_output_file.unlink(missing_ok=True)

        raise EnrichmentProcessingError(
            f"Unable to write enriched Parquet file "
            f"'{output_file}'"
        ) from exc

    logger.info(
        "Enrichment completed for %s: "
        "%s processed, %s skipped, output=%s",
        raw_file,
        processed_records,
        skipped_records,
        output_file,
    )

    return output_file