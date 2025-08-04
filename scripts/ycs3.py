#!/usr/bin/env -S uv run --quiet --script

# /// script
# dependencies = [
#   "boto3",
# ]
# ///
import sys
import boto3

AWS_BUCKET_NAME = "snatcher"
AWS_ACCESS_KEY = ""
AWS_SECRET_KEY = ""


def upload_to_s3(file_path):
    # Use the filename from the path as the S3 key
    file_name = file_path.split("/")[-1]

    client = boto3.client(
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        service_name="s3",
        endpoint_url="https://storage.yandexcloud.net",
    )

    with open(file_path, "rb") as f:
        client.upload_fileobj(f, AWS_BUCKET_NAME, file_name)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: uv run ycs3.py <path_to_file>")
        sys.exit(1)

    upload_to_s3(sys.argv[1])
