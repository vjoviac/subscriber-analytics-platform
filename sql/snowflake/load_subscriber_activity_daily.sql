-- Load curated daily subscriber activity from Amazon S3.
--
-- The COPY operation is idempotent for unchanged files because
-- FORCE remains disabled. Snowflake skips files already loaded
-- successfully into the target table.
--
-- The loader role intentionally has no warehouse OPERATE privilege.
-- SUBSCRIBER_ANALYTICS_WH suspends automatically after 60 seconds.
--
-- Required primary role: SUBSCRIBER_ANALYTICS_LOADER

USE SECONDARY ROLES NONE;
USE ROLE SUBSCRIBER_ANALYTICS_LOADER;
USE WAREHOUSE SUBSCRIBER_ANALYTICS_WH;
USE DATABASE SUBSCRIBER_ANALYTICS;
USE SCHEMA CURATED;

ALTER SESSION SET TIMEZONE = 'UTC';

COPY INTO SUBSCRIBER_ACTIVITY_DAILY
FROM @SUBSCRIBER_ACTIVITY_DAILY_STAGE
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
INCLUDE_METADATA = (
    source_filename = METADATA$FILENAME,
    source_file_content_key = METADATA$FILE_CONTENT_KEY,
    source_file_last_modified = METADATA$FILE_LAST_MODIFIED,
    loaded_at = METADATA$START_SCAN_TIME
)
ON_ERROR = ABORT_STATEMENT
FORCE = FALSE;

SELECT
    COUNT(*) AS row_count,
    COUNT(DISTINCT subscriber_id)
        AS unique_subscriber_count,

    SUM(event_count) AS total_event_count,
    SUM(total_bytes_dl) AS total_bytes_dl,
    SUM(total_bytes_ul) AS total_bytes_ul,
    SUM(total_bytes) AS total_bytes,

    COUNT_IF(
        total_bytes <> total_bytes_dl + total_bytes_ul
    ) AS byte_mismatch_count,

    COUNT_IF(
        avg_latency_ms <>
        ROUND(
            latency_sum /
            NULLIF(latency_sample_count, 0),
            2
        )
    ) AS latency_mismatch_count,

    COUNT_IF(
        avg_packet_loss_pct <>
        ROUND(
            packet_loss_sum /
            NULLIF(packet_loss_sample_count, 0),
            4
        )
    ) AS packet_loss_mismatch_count,

    COUNT_IF(
        aggregation_grain <> 'daily'
    ) AS grain_mismatch_count,

    COUNT_IF(
        window_end <> DATEADD(day, 1, window_start)
    ) AS window_mismatch_count,

    COUNT_IF(
        source_filename IS NULL
        OR source_file_content_key IS NULL
        OR source_file_last_modified IS NULL
        OR loaded_at IS NULL
    ) AS lineage_null_count
FROM SUBSCRIBER_ACTIVITY_DAILY;

SELECT
    subscriber_id,
    window_start,
    window_end,
    COUNT(*) AS duplicate_count
FROM SUBSCRIBER_ACTIVITY_DAILY
GROUP BY
    subscriber_id,
    window_start,
    window_end
HAVING COUNT(*) > 1;