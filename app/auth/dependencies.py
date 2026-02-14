from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.auth.cognito import cognito_auth
from app.services.user_service import UserService
from app.schemas.user import UserRole
from typing import Dict

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict:
    """Get current authenticated user from JWT token with complete profile"""
    try:
        token = credentials.credentials

        # Verify token with Cognito
        decoded_token = await cognito_auth.verify_token(token)

        # Get complete user profile (users table + role-specific table)
        cognito_id = decoded_token['sub']  # 'sub' is the user ID in Cognito

        complete_user = await UserService.get_complete_user_profile(cognito_id)

        if not complete_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found in database. Please complete registration by calling POST /api/v1/users/register"
            )

        return {
            "cognito_data": decoded_token,
            "db_user": complete_user
        }

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_patient(
    current_user: Dict = Depends(get_current_user)
) -> Dict:
    """Ensure current user is a patient"""
    if current_user["db_user"]["role"] != UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Patient role required"
        )
    return current_user

async def get_current_provider(
    current_user: Dict = Depends(get_current_user)
) -> Dict:
    """Ensure current user is a healthcare provider"""
    if current_user["db_user"]["role"] != UserRole.PROVIDER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Healthcare provider role required"
        )
    return current_user

async def get_current_admin(
    current_user: Dict = Depends(get_current_user)
) -> Dict:
    """Ensure current user is an admin"""
    if current_user["db_user"]["role"] != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Admin role required"
        )
    return current_user