from app.utils.s3 import s3_service
from app.config.database import supabase, supabase_admin
from datetime import datetime, timezone
from typing import Dict, Optional


class ProviderService:
    """Service layer for provider-related business logic"""

    @staticmethod
    async def upload_license(
        user_id: str,
        file_content: bytes,
        file_name: str,
        content_type: str
    ) -> Dict:
        """
        Upload medical license to S3 and update provider record

        Args:
            user_id: The user's ID
            file_content: File content as bytes
            file_name: Original file name
            content_type: MIME type of the file

        Returns:
            dict with upload details
        """
        # Upload to S3
        upload_result = await s3_service.upload_file(
            file_content=file_content,
            file_name=file_name,
            folder="licenses",
            content_type=content_type
        )

        # Update provider record in database
        updated_at = datetime.now(timezone.utc).isoformat()

        # First check if record exists in providers table
        provider_result = supabase_admin.table("providers").select("*").eq(
            "user_id", user_id
        ).execute()

        if provider_result.data:
            # Update existing provider record
            update_result = supabase_admin.table("providers").update({
                "license_url": upload_result["file_url"],
                "license_key": upload_result["file_key"],
                "license_status": "pending",
                "updated_at": updated_at
            }).eq("user_id", user_id).execute()
        else:
            # If no provider record exists, create one (use admin client for INSERT)
            # Get user info first
            user_result = supabase_admin.table("users").select("*").eq("id", user_id).execute()
            if not user_result.data:
                raise Exception("User not found")

            user = user_result.data[0]

            # Create provider record using admin client to bypass RLS
            insert_result = supabase_admin.table("providers").insert({
                "user_id": user_id,
                "full_name": user.get("full_name", ""),
                "license_url": upload_result["file_url"],
                "license_key": upload_result["file_key"],
                "license_status": "pending"
            }).execute()

        return {
            "license_url": upload_result["file_url"],
            "license_key": upload_result["file_key"],
            "uploaded_at": datetime.now(timezone.utc)
        }

    @staticmethod
    async def get_provider_profile(user_id: str) -> Optional[Dict]:
        """
        Get provider profile data
        Uses admin client to bypass RLS

        Args:
            user_id: The user's ID

        Returns:
            Provider profile data
        """
        result = supabase_admin.table("providers").select("*").eq("user_id", user_id).execute()

        if not result.data:
            return None

        return result.data[0]

    @staticmethod
    def get_license_presigned_url(license_key: str, expiration: int = 3600) -> str:
        """
        Generate presigned URL for viewing license

        Args:
            license_key: S3 key of the license file
            expiration: URL expiration in seconds (default 1 hour)

        Returns:
            Presigned URL
        """
        return s3_service.generate_presigned_url(license_key, expiration)


# Create singleton instance
provider_service = ProviderService()
