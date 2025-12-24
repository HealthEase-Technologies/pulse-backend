from fastapi import APIRouter, HTTPException, status
from app.schemas.user import UserRegister, UserResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/register", response_model=UserResponse)
async def register_user(user_data: UserRegister):
    """
    Register a new user after Cognito signup
    This endpoint is called by frontend after successful Cognito registration
    """
    try:
        return await UserService.register_user(user_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )
