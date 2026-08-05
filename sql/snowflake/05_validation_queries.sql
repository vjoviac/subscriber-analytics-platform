-- Subscriber Analytics Platform
-- Reconciliation and example analytical queries
--
-- All queries use the approved analytical view and the read-only role.
--
-- Required primary role: SUBSCRIBER_ANALYTICS_READER

USE SECONDARY ROLES NONE;
USE ROLE SUBSCRIBER_ANALYTICS_READER;
USE WAREHOUSE SUBSCRIBER_ANALYTICS_WH;
USE DATABASE SUBSCRIBER_ANALYTICS;
USE SCHEMA ANALYTICS;

ALTER SESSION SET TIMEZONE = 'UTC';

-- 1. Analytical contract reconciliation

SELECT
    COUNT(*)                              AS row_count,
    COUNT(DISTINCT activity_date)         AS daily_windows,
    COUNT(DISTINCT subscriber_id)         AS subscribers,
    SUM(event_count)                      AS event_count,
    SUM(total_bytes_dl)                   AS total_bytes_dl,
    SUM(total_bytes_ul)                   AS total_bytes_ul,
    SUM(total_bytes)                      AS total_bytes,
    SUM(total_bytes)
        - SUM(total_bytes_dl)
        - SUM(total_bytes_ul)             AS byte_reconciliation_difference,
    COUNT_IF(
        aggregation_grain <> 'daily'
    )                                     AS invalid_grains,
    COUNT_IF(
        DATEDIFF('day', window_start, window_end) <> 1
    )                                     AS invalid_daily_windows,
    ROUND(
        SUM(latency_sum) /
        NULLIF(SUM(latency_sample_count), 0),
        2
    )                                     AS weighted_avg_latency_ms,
    ROUND(
        SUM(packet_loss_sum) /
        NULLIF(SUM(packet_loss_sample_count), 0),
        4
    )                                     AS weighted_avg_packet_loss_pct
FROM SUBSCRIBER_ACTIVITY_DAILY;

-- 2. Grain uniqueness
-- Expected result: no rows.

SELECT
    activity_date,
    subscriber_id,
    COUNT(*) AS duplicate_count
FROM SUBSCRIBER_ACTIVITY_DAILY
GROUP BY
    activity_date,
    subscriber_id
HAVING COUNT(*) > 1;

-- 3. Daily traffic and quality trend

SELECT
    activity_date,
    COUNT(DISTINCT subscriber_id) AS active_subscribers,
    SUM(event_count)              AS event_count,
    SUM(total_bytes_dl)           AS total_bytes_dl,
    SUM(total_bytes_ul)           AS total_bytes_ul,
    SUM(total_bytes)              AS total_bytes,
    ROUND(
        SUM(latency_sum) /
        NULLIF(SUM(latency_sample_count), 0),
        2
    )                             AS weighted_avg_latency_ms,
    ROUND(
        SUM(packet_loss_sum) /
        NULLIF(SUM(packet_loss_sample_count), 0),
        4
    )                             AS weighted_avg_packet_loss_pct
FROM SUBSCRIBER_ACTIVITY_DAILY
GROUP BY activity_date
ORDER BY activity_date;

-- 4. Traffic and quality by location and network technology

SELECT
    latest_state,
    latest_city,
    latest_network_technology,
    COUNT(DISTINCT subscriber_id) AS subscribers,
    SUM(event_count)              AS event_count,
    SUM(total_bytes)              AS total_bytes,
    ROUND(
        SUM(total_bytes) / POWER(1024, 3),
        3
    )                             AS total_gib,
    ROUND(
        SUM(latency_sum) /
        NULLIF(SUM(latency_sample_count), 0),
        2
    )                             AS weighted_avg_latency_ms,
    ROUND(
        SUM(packet_loss_sum) /
        NULLIF(SUM(packet_loss_sample_count), 0),
        4
    )                             AS weighted_avg_packet_loss_pct
FROM SUBSCRIBER_ACTIVITY_DAILY
GROUP BY
    latest_state,
    latest_city,
    latest_network_technology
ORDER BY
    total_bytes DESC,
    latest_state,
    latest_city;

-- 5. Plan-level comparison

SELECT
    plan_id,
    plan_name,
    plan_type,
    monthly_data_allowance_gb,
    COUNT(DISTINCT subscriber_id) AS subscribers,
    COUNT(*)                      AS subscriber_days,
    SUM(event_count)              AS event_count,
    SUM(total_bytes)              AS total_bytes,
    ROUND(
        SUM(total_bytes) / POWER(1024, 3),
        3
    )                             AS total_gib,
    ROUND(
        SUM(total_bytes) /
        POWER(1024, 3) /
        NULLIF(COUNT(*), 0),
        3
    )                             AS avg_gib_per_subscriber_day,
    ROUND(
        SUM(latency_sum) /
        NULLIF(SUM(latency_sample_count), 0),
        2
    )                             AS weighted_avg_latency_ms,
    ROUND(
        SUM(packet_loss_sum) /
        NULLIF(SUM(packet_loss_sample_count), 0),
        4
    )                             AS weighted_avg_packet_loss_pct
FROM SUBSCRIBER_ACTIVITY_DAILY
GROUP BY
    plan_id,
    plan_name,
    plan_type,
    monthly_data_allowance_gb
ORDER BY
    total_bytes DESC,
    plan_id;