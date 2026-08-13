import os
from urllib.parse import quote_plus


def require_environment_variable(name: str) -> str:
    value = os.getenv(name)

    if value is None or not value.strip():
        raise RuntimeError(
            f"Required environment variable is not configured: {name}"
        )

    return value


postgres_database = require_environment_variable("POSTGRES_DB")
postgres_user = require_environment_variable("POSTGRES_USER")
postgres_password = require_environment_variable("POSTGRES_PASSWORD")

SECRET_KEY = require_environment_variable("SUPERSET_SECRET_KEY")

SQLALCHEMY_DATABASE_URI = (
    "postgresql+psycopg2://"
    f"{quote_plus(postgres_user)}:"
    f"{quote_plus(postgres_password)}"
    f"@postgres:5432/{quote_plus(postgres_database)}"
)