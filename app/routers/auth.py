from fastapi import APIRouter, Depends
from app.auth.dependencies import get_current_user, get_current_patient, get_current_provider, get_current_admin
from app.services.auth_service import AuthService
from typing import Dict

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/me")
async def get_current_user_info(current_user: Dict = Depends(get_current_user)):
    """Get current user information"""
    return AuthService.format_user_info(
        db_user=current_user["db_user"],
        cognito_data=current_user["cognito_data"]
    )


@router.post("/verify")
async def verify_token(current_user: Dict = Depends(get_current_user)):
    """Verify if token is valid"""
    return AuthService.format_token_verification(current_user["db_user"])
