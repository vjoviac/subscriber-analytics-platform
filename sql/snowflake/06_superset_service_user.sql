-- Subscriber Analytics Platform
-- Apache Superset technical identity
--
-- Before running this script, define the RSA public key only in the
-- current Snowflake session:
--
-- SET superset_rsa_public_key = '<PUBLIC_KEY_WITHOUT_PEM_HEADERS>';
--
-- Never commit the private key, its passphrase, or a populated
-- public-key session variable.

USE SECONDARY ROLES NONE;

-- Create and maintain the non-human identity.

USE ROLE USERADMIN;

CREATE USER IF NOT EXISTS SUPERSET_SERVICE_USER
    TYPE = SERVICE
    RSA_PUBLIC_KEY = $superset_rsa_public_key
    COMMENT = 'Read-only Apache Superset analytical identity';

-- Assign only the approved analytical reader role.

USE ROLE SECURITYADMIN;

GRANT ROLE SUBSCRIBER_ANALYTICS_READER
    TO USER SUPERSET_SERVICE_USER;

-- Configure deterministic session defaults after role assignment.

USE ROLE USERADMIN;

ALTER USER SUPERSET_SERVICE_USER SET
    TYPE = SERVICE
    RSA_PUBLIC_KEY = $superset_rsa_public_key
    DEFAULT_ROLE = 'SUBSCRIBER_ANALYTICS_READER'
    DEFAULT_WAREHOUSE = 'SUBSCRIBER_ANALYTICS_WH'
    DEFAULT_NAMESPACE = 'SUBSCRIBER_ANALYTICS.ANALYTICS'
    COMMENT = 'Read-only Apache Superset analytical identity';