import os

from dotenv import load_dotenv

load_dotenv()


AWS_PROFILE = os.getenv("AWS_PROFILE", "subscriber-analytics")
AWS_REGION = os.getenv("AWS_REGION", "us-east-2")
S3_BUCKET = os.getenv(
    "S3_BUCKET",
    "subscriber-analytics-platform-dev",
)