-- Subscriber Analytics Platform
-- Stable analytical contract over the curated native table
--
-- Grain:
-- One row per subscriber and daily activity window.
--
-- Direct telecom identifiers and low-level technical identifiers are
-- intentionally excluded from the analytical serving contract.
--
-- Required primary role: ACCOUNTADMIN

USE SECONDARY ROLES NONE;
USE ROLE ACCOUNTADMIN;

CREATE VIEW IF NOT EXISTS
    SUBSCRIBER_ANALYTICS.ANALYTICS.SUBSCRIBER_ACTIVITY_DAILY
    COMMENT = 'Dashboard-ready daily subscriber activity without direct telecom identifiers'
AS
SELECT
    TO_DATE(window_start) AS activity_date,
    subscriber_id,
    customer_segment,
    subscriber_status,
    plan_id,
    plan_name,
    plan_type,
    monthly_data_allowance_gb,
    max_download_mbps,
    max_upload_mbps,
    latest_device_vendor,
    latest_device_model,
    latest_device_os,
    latest_device_technology,
    latest_city,
    latest_state,
    latest_network_technology,
    event_count,
    total_bytes_dl,
    total_bytes_ul,
    total_bytes,
    latency_sum,
    latency_sample_count,
    packet_loss_sum,
    packet_loss_sample_count,
    avg_latency_ms,
    avg_packet_loss_pct,
    aggregation_grain,
    window_start,
    window_end
FROM SUBSCRIBER_ANALYTICS.CURATED.SUBSCRIBER_ACTIVITY_DAILY;