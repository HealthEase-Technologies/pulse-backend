from app.schemas.user import UserRole
from typing import Dict


class AuthService:
    """Service layer for authentication-related business logic"""

    @staticmethod
    def format_user_info(db_user: dict, cognito_data: dict) -> dict:
        """
        Format user information for API response

        Args:
            db_user: User data from database
            cognito_data: Decoded Cognito JWT token data

        Returns:
            dict: Formatted user information
        """
        return {
            "user_id": db_user["id"],
            "cognito_id": db_user["cognito_id"],
            "username": db_user.get("username"),
            "email": db_user["email"],
            "full_name": db_user["full_name"],
            "role": db_user["role"],
            "is_active": db_user["is_active"],
            "created_at": db_user.get("created_at"),
            "token_issued_at": cognito_data.get("iat"),
            "token_expires_at": cognito_data.get("exp")
        }

    @staticmethod
    def format_token_verification(db_user: dict) -> dict:
        """
        Format token verification response

        Args:
            db_user: User data from database

        Returns:
            dict: Token verification response
        """
        return {
            "valid": True,
            "user_id": db_user["id"],
            "role": db_user["role"]
        }
