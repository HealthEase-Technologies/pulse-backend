from app.config.database import supabase_admin
from app.utils.s3 import s3_service
from fastapi import HTTPException, status
from typing import List, Dict, Optional
from datetime import datetime, timezone


class AdminService:
    """Service layer for admin-related business logic"""

    @staticmethod
    async def get_all_providers(license_status: Optional[str] = None) -> List[Dict]:
        """
        Get all providers with their license status

        Args:
            license_status: Filter by license status (pending/approved/rejected)

        Returns:
            List of providers with user info
        """
        try:
            # Query providers table
            query = supabase_admin.table("providers").select(
                "id, user_id, full_name, license_url, license_key, license_status, "
                "license_verified_at, license_verified_by, years_of_experience, specialisation, about, "
                "created_at, updated_at"
            )

            if license_status:
                query = query.eq("license_status", license_status)

            result = query.execute()

            if not result.data:
                return []

            # Enrich with user email/username
            providers = []
            for provider in result.data:
                user_result = supabase_admin.table("users").select(
                    "email, username"
                ).eq("id", provider["user_id"]).execute()

                if user_result.data:
                    provider["email"] = user_result.data[0]["email"]
                    provider["username"] = user_result.data[0]["username"]

                providers.append(provider)

            return providers

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch providers: {str(e)}"
            )

    @staticmethod
    async def update_license_status(
        provider_id: str,
        new_status: str,
        admin_id: str
    ) -> Dict:
        """
        Update provider license status (approve/reject)

        Args:
            provider_id: Provider's ID
            new_status: New status (approved/rejected)
            admin_id: Admin user ID performing the action

        Returns:
            Updated provider data
        """
        # Validate status
        if new_status not in ['approved', 'rejected']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid status. Must be 'approved' or 'rejected'"
            )

        try:
            # Update provider license status
            update_data = {
                "license_status": new_status,
                "license_verified_at": datetime.now(timezone.utc).isoformat(),
                "license_verified_by": admin_id,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            result = supabase_admin.table("providers").update(update_data).eq(
                "id", provider_id
            ).execute()

            if not result.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Provider not found"
                )

            # Log admin action
            await AdminService.log_admin_action(
                admin_id=admin_id,
                action=f"license_{new_status}",
                target_user_id=result.data[0]["user_id"],
                details={
                    "provider_id": provider_id,
                    "previous_status": "pending",
                    "new_status": new_status
                }
            )

            return result.data[0]

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update license status: {str(e)}"
            )

    @staticmethod
    async def get_all_users() -> List[Dict]:
        """
        Get all users with their role-specific data

        Returns:
            List of users with complete profiles
        """
        try:
            # Get all users
            users_result = supabase_admin.table("users").select("*").execute()

            if not users_result.data:
                return []

            complete_users = []

            for user in users_result.data:
                user_id = user["id"]
                role = user["role"]

                # Fetch role-specific data
                if role == 1:  # Patient
                    profile_result = supabase_admin.table("patients").select("full_name").eq(
                        "user_id", user_id
                    ).execute()
                    user["full_name"] = profile_result.data[0]["full_name"] if profile_result.data else None
                    user["role_name"] = "Patient"

                elif role == 2:  # Provider
                    profile_result = supabase_admin.table("providers").select(
                        "full_name, license_status"
                    ).eq("user_id", user_id).execute()
                    if profile_result.data:
                        user["full_name"] = profile_result.data[0]["full_name"]
                        user["license_status"] = profile_result.data[0].get("license_status")
                    user["role_name"] = "Provider"

                elif role == 3:  # Admin
                    profile_result = supabase_admin.table("admins").select("full_name").eq(
                        "user_id", user_id
                    ).execute()
                    user["full_name"] = profile_result.data[0]["full_name"] if profile_result.data else None
                    user["role_name"] = "Admin"

                complete_users.append(user)

            return complete_users

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch users: {str(e)}"
            )

    @staticmethod
    async def get_provider_license_url(provider_id: str, admin_id: str) -> str:
        """
        Generate presigned URL for viewing a provider's license

        Args:
            provider_id: Provider's ID
            admin_id: Admin user ID requesting the license

        Returns:
            Presigned URL for viewing the license
        """
        try:
            # Get provider's license key
            provider_result = supabase_admin.table("providers").select(
                "license_key, user_id"
            ).eq("id", provider_id).execute()

            if not provider_result.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Provider not found"
                )

            license_key = provider_result.data[0].get("license_key")

            if not license_key:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No license found for this provider"
                )

            # Generate presigned URL (valid for 1 hour)
            presigned_url = s3_service.generate_presigned_url(license_key, expiration=3600)

            # Log admin action
            await AdminService.log_admin_action(
                admin_id=admin_id,
                action="view_license",
                target_user_id=provider_result.data[0]["user_id"],
                details={"provider_id": provider_id}
            )

            return presigned_url

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate license URL: {str(e)}"
            )

    @staticmethod
    async def update_provider(
        provider_id: str,
        update_data: Dict,
        admin_id: str
    ) -> Dict:
        """
        Update provider profile data

        Args:
            provider_id: Provider's ID
            update_data: Dictionary with fields to update
            admin_id: Admin user ID performing the action

        Returns:
            Updated provider data
        """
        try:
            # Add timestamp
            update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

            # Get provider before update for logging
            provider_result = supabase_admin.table("providers").select("user_id").eq(
                "id", provider_id
            ).execute()

            if not provider_result.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Provider not found"
                )

            # Update provider
            result = supabase_admin.table("providers").update(update_data).eq(
                "id", provider_id
            ).execute()

            if not result.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Failed to update provider"
                )

            # Log admin action
            await AdminService.log_admin_action(
                admin_id=admin_id,
                action="update_provider",
                target_user_id=provider_result.data[0]["user_id"],
                details={
                    "provider_id": provider_id,
                    "updated_fields": list(update_data.keys())
                }
            )

            return result.data[0]

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update provider: {str(e)}"
            )

    # Delete provider method disabled - not in use due to AWS Cognito credential issues
    # Use reject license status instead to deactivate providers
    # Uncomment and fix AWS Cognito credentials to re-enable this functionality
    #
    # @staticmethod
    # async def delete_provider(provider_id: str, admin_id: str) -> Dict:
    #     """
    #     Delete a provider completely from all systems
    #
    #     This ensures data integrity by removing the provider from:
    #     1. S3 (license file)
    #     2. Cognito (authentication)
    #     3. Supabase (database - cascades to provider table)
    #
    #     Args:
    #         provider_id: Provider's ID
    #         admin_id: Admin user ID performing the action
    #
    #     Returns:
    #         Success message
    #     """
    #     # Implementation commented out - see delete_provider_disabled.txt for code

    @staticmethod
    async def log_admin_action(
        admin_id: str,
        action: str,
        target_user_id: Optional[str] = None,
        details: Optional[Dict] = None
    ) -> None:
        """
        Log admin action to audit trail

        Args:
            admin_id: Admin user ID
            action: Action performed (e.g., 'license_approved', 'user_deleted')
            target_user_id: Target user ID (if applicable)
            details: Additional details as JSON
        """
        try:
            # Get admin's database ID from admins table
            admin_result = supabase_admin.table("admins").select("id").eq(
                "user_id", admin_id
            ).execute()

            if not admin_result.data:
                return  # Skip logging if admin record not found

            admin_db_id = admin_result.data[0]["id"]

            log_data = {
                "admin_id": admin_db_id,
                "action": action,
                "target_user_id": target_user_id,
                "details": details,
                "created_at": datetime.now(timezone.utc).isoformat()
            }

            supabase_admin.table("admin_audit_logs").insert(log_data).execute()

        except Exception as e:
            # Don't fail the main operation if logging fails
            print(f"Failed to log admin action: {str(e)}")


# Create singleton instance
admin_service = AdminService()
