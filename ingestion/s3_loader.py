from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from infrastructure.aws_config import (
    AWS_PROFILE,
    AWS_REGION,
    S3_BUCKET,
)


class S3UploadError(Exception):
    """
    Raised when a local file cannot be uploaded to S3.
    """


def build_s3_key(
    local_file: Path,
    data_base_dir: Path = Path("data"),
) -> str:
    """
    Build an S3 object key preserving the path below data/.

    Example:

    data/enriched/year=2026/month=07/file.parquet

    becomes:

    enriched/year=2026/month=07/file.parquet
    """
    local_file = Path(local_file)
    data_base_dir = Path(data_base_dir)

    try:
        relative_path = local_file.relative_to(data_base_dir)
    except ValueError as error:
        raise ValueError(
            f"The file must be located inside "
            f"{data_base_dir}."
        ) from error

    return relative_path.as_posix()


def upload_file_to_s3(
    local_file: Path,
    bucket: str = S3_BUCKET,
    data_base_dir: Path = Path("data"),
) -> str:
    """
    Upload a file from the local data directory to S3.

    The directory structure below data/ is preserved as the
    S3 object key.
    """
    local_file = Path(local_file)

    if not local_file.exists():
        raise FileNotFoundError(
            f"Local file not found: {local_file}"
        )

    if not local_file.is_file():
        raise ValueError(
            f"Local path is not a file: {local_file}"
        )

    object_key = build_s3_key(
        local_file=local_file,
        data_base_dir=data_base_dir,
    )

    session = boto3.Session(
        profile_name=AWS_PROFILE,
        region_name=AWS_REGION,
    )

    s3_client = session.client("s3")

    try:
        s3_client.upload_file(
            Filename=str(local_file),
            Bucket=bucket,
            Key=object_key,
        )
    except (BotoCoreError, ClientError) as error:
        raise S3UploadError(
            f"Unable to upload {local_file} "
            f"to s3://{bucket}/{object_key}."
        ) from error

    return f"s3://{bucket}/{object_key}"