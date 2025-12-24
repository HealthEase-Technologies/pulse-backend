import boto3
from botocore.exceptions import ClientError
from app.config.settings import settings
import uuid
from typing import Optional
import mimetypes

class S3Service:
    def __init__(self):
        # Configure S3 client with explicit endpoint for Middle East region
        client_config = {
            'aws_access_key_id': settings.aws_access_key_id,
            'aws_secret_access_key': settings.aws_secret_access_key,
            'region_name': settings.aws_region
        }

        # For me-central-1, use explicit endpoint URL
        if settings.aws_region == 'me-central-1':
            client_config['endpoint_url'] = f'https://s3.{settings.aws_region}.amazonaws.com'

        self.s3_client = boto3.client('s3', **client_config)
        self.bucket_name = settings.s3_bucket_name

    async def upload_file(
        self,
        file_content: bytes,
        file_name: str,
        folder: str = "",
        content_type: Optional[str] = None
    ) -> dict:
        """
        Upload a file to S3 bucket

        Args:
            file_content: The file content as bytes
            file_name: Original file name
            folder: Folder path in S3 (e.g., 'licenses')
            content_type: MIME type of the file

        Returns:
            dict with 'file_url' and 'file_key'
        """
        try:
            # Generate unique file name
            file_extension = file_name.split('.')[-1] if '.' in file_name else ''
            unique_filename = f"{uuid.uuid4()}.{file_extension}" if file_extension else str(uuid.uuid4())

            # Create full S3 key with folder
            s3_key = f"{folder}/{unique_filename}" if folder else unique_filename

            # Detect content type if not provided
            if not content_type:
                content_type = mimetypes.guess_type(file_name)[0] or 'application/octet-stream'

            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_content,
                ContentType=content_type
            )

            # Generate file URL with correct region
            # For most regions including me-central-1
            file_url = f"https://{self.bucket_name}.s3.{settings.aws_region}.amazonaws.com/{s3_key}"

            return {
                "file_url": file_url,
                "file_key": s3_key,
                "original_filename": file_name
            }

        except ClientError as e:
            raise Exception(f"Failed to upload file to S3: {str(e)}")

    async def delete_file(self, file_key: str) -> bool:
        """
        Delete a file from S3 bucket

        Args:
            file_key: The S3 key of the file to delete

        Returns:
            True if successful
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=file_key
            )
            return True
        except ClientError as e:
            raise Exception(f"Failed to delete file from S3: {str(e)}")

    def generate_presigned_url(self, file_key: str, expiration: int = 3600) -> str:
        """
        Generate a presigned URL for viewing a file from S3

        Args:
            file_key: The S3 key of the file
            expiration: URL expiration time in seconds (default 1 hour)

        Returns:
            Presigned URL string
        """
        try:
            # Use the same client configuration as initialized
            # This ensures me-central-1 uses the correct endpoint
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': file_key
                },
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            raise Exception(f"Failed to generate presigned URL: {str(e)}")

# Create a singleton instance
s3_service = S3Service()
