import os

from dotenv import load_dotenv

load_dotenv()


AWS_PROFILE = os.getenv("AWS_PROFILE", "subscriber-analytics")
AWS_REGION = os.getenv("AWS_REGION", "us-east-2")
S3_BUCKET = os.getenv(
    "S3_BUCKET",
    "subscriber-analytics-platform-dev",
)

DEFAULT_EVENT_COUNT = int(
    os.getenv("DEFAULT_EVENT_COUNT", "100")
)

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")