-- Subscriber Analytics Platform
-- Snowflake storage integration and native curated table
--
-- Required primary role: ACCOUNTADMIN
--
-- Before running this script, define the AWS role ARN only in the
-- current Snowflake session:
--
-- SET aws_role_arn =
--     'arn:aws:iam::<AWS_ACCOUNT_ID>:role/<SNOWFLAKE_S3_ROLE>';
--
-- Never commit the real AWS account ID or role ARN.

USE SECONDARY ROLES NONE;
USE ROLE ACCOUNTADMIN;

CREATE STORAGE INTEGRATION IF NOT EXISTS
    S3_SUBSCRIBER_ACTIVITY_DAILY_INT
    TYPE = EXTERNAL_STAGE
    STORAGE_PROVIDER = 'S3'
    ENABLED = TRUE
    STORAGE_AWS_ROLE_ARN = $aws_role_arn
    STORAGE_ALLOWED_LOCATIONS = (
        's3://subscriber-analytics-platform-dev/curated/subscriber_activity_daily/'
    )
    COMMENT = 'Read-only access to canonical daily subscriber activity';

CREATE FILE FORMAT IF NOT EXISTS
    SUBSCRIBER_ANALYTICS.CURATED.PARQUET_FORMAT
    TYPE = PARQUET
    USE_LOGICAL_TYPE = TRUE
    BINARY_AS_TEXT = FALSE
    COMMENT = 'Parquet format with logical timestamp support';

CREATE STAGE IF NOT EXISTS
    SUBSCRIBER_ANALYTICS.CURATED.SUBSCRIBER_ACTIVITY_DAILY_STAGE
    URL = 's3://subscriber-analytics-platform-dev/curated/subscriber_activity_daily/'
    STORAGE_INTEGRATION = S3_SUBSCRIBER_ACTIVITY_DAILY_INT
    FILE_FORMAT = SUBSCRIBER_ANALYTICS.CURATED.PARQUET_FORMAT
    COMMENT = 'Canonical curated daily subscriber activity in Amazon S3';

CREATE TABLE IF NOT EXISTS
    SUBSCRIBER_ANALYTICS.CURATED.SUBSCRIBER_ACTIVITY_DAILY (
        subscriber_id VARCHAR NOT NULL,
        imsi VARCHAR,
        msisdn VARCHAR,
        customer_segment VARCHAR,
        subscriber_status VARCHAR,
        plan_id VARCHAR,
        plan_name VARCHAR,
        plan_type VARCHAR,
        monthly_data_allowance_gb NUMBER(10, 2),
        max_download_mbps NUMBER(38, 0),
        max_upload_mbps NUMBER(38, 0),
        technology_access ARRAY,
        latest_tac VARCHAR,
        latest_device_vendor VARCHAR,
        latest_device_model VARCHAR,
        latest_device_os VARCHAR,
        latest_device_technology VARCHAR,
        latest_cell_id VARCHAR,
        latest_city VARCHAR,
        latest_state VARCHAR,
        latest_network_technology VARCHAR,
        event_count NUMBER(38, 0) NOT NULL,
        total_bytes_dl NUMBER(38, 0) NOT NULL,
        total_bytes_ul NUMBER(38, 0) NOT NULL,
        total_bytes NUMBER(38, 0) NOT NULL,
        latency_sum NUMBER(38, 0) NOT NULL,
        latency_sample_count NUMBER(38, 0) NOT NULL,
        packet_loss_sum NUMBER(18, 4) NOT NULL,
        packet_loss_sample_count NUMBER(38, 0) NOT NULL,
        avg_latency_ms NUMBER(12, 2),
        avg_packet_loss_pct NUMBER(12, 4),
        aggregation_grain VARCHAR NOT NULL,
        window_start TIMESTAMP_TZ(6) NOT NULL,
        window_end TIMESTAMP_TZ(6) NOT NULL,
        curated_at TIMESTAMP_TZ(6) NOT NULL,
        source_filename VARCHAR NOT NULL,
        source_file_content_key VARCHAR NOT NULL,
        source_file_last_modified TIMESTAMP_TZ(9) NOT NULL,
        loaded_at TIMESTAMP_TZ(9) NOT NULL
    )
    COMMENT = 'Native daily subscriber activity loaded from canonical Parquet files in Amazon S3';