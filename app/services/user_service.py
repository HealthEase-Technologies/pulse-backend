from app.config.database import supabase, supabase_admin
from app.schemas.user import UserRegister
from fastapi import HTTPException, status
from typing import List, Optional

class UserService:
    """Service layer for user-related business logic"""

    @staticmethod
    async def register_user(user_data: UserRegister) -> dict:
        """
        Register a new user in the database
        Creates records in both users table and role-specific table (patients/providers/admins)
        Uses service_role key to bypass RLS during registration

        Args:
            user_data: User registration data

        Returns:
            dict: Created user data

        Raises:
            HTTPException: If user already exists or creation fails
        """
        # Use admin client (service_role) for registration to bypass RLS
        # Check if user already exists by cognito_id
        existing_user = supabase_admin.table("users").select("*").eq(
            "cognito_id", user_data.cognito_id
        ).execute()

        if existing_user.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already registered"
            )

        # Check if email already exists
        existing_email = supabase_admin.table("users").select("*").eq(
            "email", user_data.email
        ).execute()

        if existing_email.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Prepare user data for users table (no full_name, phone here)
        user_dict = {
            "cognito_id": user_data.cognito_id,
            "username": user_data.username,
            "email": user_data.email,
            "role": int(user_data.role)
        }

        # Insert new user into users table using admin client
        result = supabase_admin.table("users").insert(user_dict).execute()

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create user"
            )

        created_user = result.data[0]
        user_id = created_user["id"]

        # Create record in role-specific table
        role_data = {
            "user_id": user_id,
            "full_name": user_data.full_name
        }

        try:
            if user_data.role == 1:  # Patient
                supabase_admin.table("patients").insert(role_data).execute()
            elif user_data.role == 2:  # Provider
                supabase_admin.table("providers").insert(role_data).execute()
            elif user_data.role == 3:  # Admin
                supabase_admin.table("admins").insert(role_data).execute()
        except Exception as e:
            # Rollback: delete the user record if role-specific creation fails
            supabase_admin.table("users").delete().eq("id", user_id).execute()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create role-specific profile: {str(e)}"
            )

        # Fetch and return complete profile (with full_name from role-specific table)
        complete_profile = await UserService.get_complete_user_profile(created_user["cognito_id"])
        return complete_profile if complete_profile else created_user

    @staticmethod
    async def get_all_users() -> List[dict]:
        """
        Get all users from the database

        Returns:
            List[dict]: List of all users

        Raises:
            HTTPException: If query fails
        """
        try:
            result = supabase.table("users").select("*").execute()
            return result.data
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch users: {str(e)}"
            )

    @staticmethod
    async def get_user_by_id(user_id: str) -> Optional[dict]:
        """
        Get a user by their database ID

        Args:
            user_id: User's database UUID

        Returns:
            dict: User data or None if not found
        """
        result = supabase.table("users").select("*").eq("id", user_id).execute()
        return result.data[0] if result.data else None

    @staticmethod
    async def get_user_by_cognito_id(cognito_id: str) -> Optional[dict]:
        """
        Get a user by their Cognito ID

        Args:
            cognito_id: User's Cognito UUID

        Returns:
            dict: User data or None if not found
        """
        result = supabase.table("users").select("*").eq("cognito_id", cognito_id).execute()
        return result.data[0] if result.data else None

    @staticmethod
    async def get_complete_user_profile(cognito_id: str) -> Optional[dict]:
        """
        Get complete user profile by joining users table with role-specific table
        Uses admin client to ensure access to all data

        Args:
            cognito_id: User's Cognito UUID

        Returns:
            dict: Complete user data including full_name and role-specific fields
        """
        # Get user from users table using admin client
        user_result = supabase_admin.table("users").select("*").eq("cognito_id", cognito_id).execute()

        if not user_result.data:
            return None

        user = user_result.data[0]
        user_id = user["id"]
        role = user["role"]

        # Fetch from role-specific table using admin client
        role_data = None
        if role == 1:  # Patient
            result = supabase_admin.table("patients").select("*").eq("user_id", user_id).execute()
            role_data = result.data[0] if result.data else {}
        elif role == 2:  # Provider
            result = supabase_admin.table("providers").select("*").eq("user_id", user_id).execute()
            role_data = result.data[0] if result.data else {}
        elif role == 3:  # Admin
            result = supabase_admin.table("admins").select("*").eq("user_id", user_id).execute()
            role_data = result.data[0] if result.data else {}

        # Merge user data with role-specific data
        # IMPORTANT: Keep user table id, rename role table id to avoid conflict
        if role_data:
            role_data_copy = role_data.copy()
            if 'id' in role_data_copy:
                role_data_copy['profile_id'] = role_data_copy.pop('id')  # Rename provider/patient/admin id
            complete_profile = {**user, **role_data_copy}
        else:
            complete_profile = user

        return complete_profile

    @staticmethod
    async def update_user(user_id: str, update_data: dict) -> dict:
        """
        Update user information

        Args:
            user_id: User's database UUID
            update_data: Dictionary of fields to update

        Returns:
            dict: Updated user data

        Raises:
            HTTPException: If user not found or update fails
        """
        result = supabase.table("users").update(update_data).eq("id", user_id).execute()

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found or update failed"
            )

        return result.data[0]
