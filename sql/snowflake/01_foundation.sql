-- Subscriber Analytics Platform
-- Snowflake analytical warehouse foundation
--
-- This script creates account-level cost controls and the logical
-- database foundation. It is safe to rerun because it does not replace
-- existing objects.
--
-- Required primary role: ACCOUNTADMIN

USE SECONDARY ROLES NONE;
USE ROLE ACCOUNTADMIN;

CREATE DATABASE IF NOT EXISTS SUBSCRIBER_ANALYTICS
    COMMENT = 'Analytical warehouse for curated subscriber data';

CREATE SCHEMA IF NOT EXISTS SUBSCRIBER_ANALYTICS.CURATED
    COMMENT = 'Native tables loaded from canonical curated Parquet datasets';

CREATE SCHEMA IF NOT EXISTS SUBSCRIBER_ANALYTICS.ANALYTICS
    COMMENT = 'Stable analytical views over curated subscriber activity';

CREATE RESOURCE MONITOR IF NOT EXISTS SUBSCRIBER_ANALYTICS_MONITOR
    WITH
        CREDIT_QUOTA = 10
        FREQUENCY = MONTHLY
        START_TIMESTAMP = IMMEDIATELY
        TRIGGERS
            ON 50 PERCENT DO NOTIFY
            ON 80 PERCENT DO SUSPEND
            ON 100 PERCENT DO SUSPEND_IMMEDIATE;

CREATE WAREHOUSE IF NOT EXISTS SUBSCRIBER_ANALYTICS_WH
    WITH
        WAREHOUSE_TYPE = STANDARD
        WAREHOUSE_SIZE = XSMALL
        AUTO_SUSPEND = 60
        AUTO_RESUME = TRUE
        INITIALLY_SUSPENDED = TRUE
        RESOURCE_MONITOR = SUBSCRIBER_ANALYTICS_MONITOR
        COMMENT = 'Cost-controlled warehouse for subscriber analytics';