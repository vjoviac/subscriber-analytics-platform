from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError


AWS_PROFILE = "subscriber-analytics"
AWS_REGION = "us-east-2"
S3_BUCKET = "subscriber-analytics-platform-dev"


def build_s3_key(local_file: Path) -> str:
    """
    Convert a local path such as:

    data/raw/year=2026/month=07/day=16/hour=16/file.jsonl

    into an S3 object key such as:

    raw/year=2026/month=07/day=16/hour=16/file.jsonl
    """
    try:
        relative_path = local_file.relative_to("data")
    except ValueError as error:
        raise ValueError(
            "The file must be located inside the data directory."
        ) from error

    return relative_path.as_posix()


def upload_file_to_s3(
    local_file: Path,
    bucket: str = S3_BUCKET,
) -> str:
    if not local_file.exists():
        raise FileNotFoundError(
            f"Local file not found: {local_file}"
        )

    session = boto3.Session(
        profile_name=AWS_PROFILE,
        region_name=AWS_REGION,
    )

    s3_client = session.client("s3")
    object_key = build_s3_key(local_file)

    try:
        s3_client.upload_file(
            Filename=str(local_file),
            Bucket=bucket,
            Key=object_key,
        )
    except (BotoCoreError, ClientError) as error:
        raise RuntimeError(
            f"Unable to upload {local_file} to S3."
        ) from error

    return f"s3://{bucket}/{object_key}"