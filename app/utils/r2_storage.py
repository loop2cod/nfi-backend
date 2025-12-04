"""
Cloudflare R2 Storage Utility
Handles file uploads to Cloudflare R2 using AWS S3-compatible API
"""
import os
import uuid
from typing import Dict
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

# R2 Configuration from environment variables
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME")
R2_PUBLIC_HOST = os.getenv("R2_PUBLIC_HOST")

# Initialize S3 client configured for Cloudflare R2
s3_client = boto3.client(
    's3',
    endpoint_url=f'https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com',
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY,
    config=Config(signature_version='s3v4'),
    region_name='auto'
)


def generate_presigned_upload_url(
    file_extension: str,
    content_type: str,
    folder: str = "profile-pictures",
    expires_in: int = 3600
) -> Dict[str, str]:
    """
    Generate a presigned URL for uploading files to R2

    Args:
        file_extension: File extension (e.g., 'jpg', 'png')
        content_type: MIME type (e.g., 'image/jpeg')
        folder: Folder path in the bucket
        expires_in: URL expiration time in seconds

    Returns:
        Dictionary with uploadUrl, publicUrl, and key
    """
    # Generate unique filename
    file_id = str(uuid.uuid4())
    key = f"{folder}/{file_id}.{file_extension}"

    try:
        # Generate presigned POST URL for upload
        upload_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': R2_BUCKET_NAME,
                'Key': key,
                'ContentType': content_type
            },
            ExpiresIn=expires_in
        )

        # Generate public URL (assuming bucket is publicly accessible)
        public_url = f"{R2_PUBLIC_HOST}/{key}"

        return {
            "upload_url": upload_url,
            "public_url": public_url,
            "key": key
        }
    except ClientError as e:
        raise Exception(f"Failed to generate presigned URL: {str(e)}")


def upload_file_directly(
    file_content: bytes,
    file_extension: str,
    content_type: str,
    folder: str = "profile-pictures"
) -> Dict[str, str]:
    """
    Upload file directly to R2 (server-side upload)

    Args:
        file_content: Binary file content
        file_extension: File extension
        content_type: MIME type
        folder: Folder path in the bucket

    Returns:
        Dictionary with publicUrl and key
    """
    # Generate unique filename
    file_id = str(uuid.uuid4())
    key = f"{folder}/{file_id}.{file_extension}"

    try:
        # Upload file to R2
        s3_client.put_object(
            Bucket=R2_BUCKET_NAME,
            Key=key,
            Body=file_content,
            ContentType=content_type
        )

        # Generate public URL
        public_url = f"{R2_PUBLIC_HOST}/{key}"

        return {
            "public_url": public_url,
            "key": key
        }
    except ClientError as e:
        raise Exception(f"Failed to upload file: {str(e)}")


def delete_file(key: str) -> bool:
    """
    Delete file from R2

    Args:
        key: File key/path in the bucket

    Returns:
        True if successful, False otherwise
    """
    try:
        s3_client.delete_object(
            Bucket=R2_BUCKET_NAME,
            Key=key
        )
        return True
    except ClientError as e:
        print(f"Failed to delete file: {str(e)}")
        return False
