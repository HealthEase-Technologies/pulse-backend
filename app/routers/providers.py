from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from app.auth.dependencies import get_current_provider
from app.services.provider_service import provider_service
from app.schemas.provider import LicenseUploadResponse, ProviderProfileResponse
from typing import Dict, Optional
from datetime import datetime, timezone

router = APIRouter(prefix="/providers", tags=["providers"])

@router.post("/upload-license", response_model=LicenseUploadResponse)
async def upload_medical_license(
    file: UploadFile = File(...),
    years_of_experience: Optional[int] = Form(None),
    specialisation: str = Form(...),
    about: Optional[str] = Form(None),
    current_user: Dict = Depends(get_current_provider)
):
    """
    Upload medical license document to S3 with provider details (Provider only)

    Requirements: U-FR-8-1, U-FR-2-7
    """
    try:
        # Validate file type (accept images and PDFs)
        allowed_types = ['image/jpeg', 'image/png', 'image/jpg', 'application/pdf']
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Allowed types: {', '.join(allowed_types)}"
            )

        # Validate file size (max 10MB)
        contents = await file.read()
        if len(contents) > 10 * 1024 * 1024:  # 10MB in bytes
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File size exceeds 10MB limit"
            )

        # Validate years of experience
        if years_of_experience is not None and (years_of_experience < 0 or years_of_experience > 60):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Years of experience must be between 0 and 60"
            )

        # Validate specialisation
        if not specialisation or not specialisation.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Specialisation is required"
            )

        # Validate about length
        if about and len(about) > 500:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="About description must be 500 characters or less"
            )

        # Upload using provider service
        user_id = current_user["db_user"]["id"]
        result = await provider_service.upload_license(
            user_id=user_id,
            file_content=contents,
            file_name=file.filename,
            content_type=file.content_type,
            years_of_experience=years_of_experience,
            specialisation=specialisation.strip(),
            about=about.strip() if about and about.strip() else None
        )

        return LicenseUploadResponse(
            message="Medical license uploaded successfully. Pending admin verification.",
            license_url=result["license_url"],
            license_key=result["license_key"],
            uploaded_at=result["uploaded_at"]
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload license: {str(e)}"
        )

@router.get("/profile", response_model=ProviderProfileResponse)
async def get_provider_profile(
    current_user: Dict = Depends(get_current_provider)
):
    """Get current provider's profile"""
    try:
        user_id = current_user["db_user"]["id"]

        provider_data = await provider_service.get_provider_profile(user_id)

        if not provider_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Provider profile not found"
            )

        # Parse datetime fields
        created_at = provider_data.get("created_at")
        updated_at = provider_data.get("updated_at")

        # Handle different datetime formats
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        elif not isinstance(created_at, datetime):
            created_at = datetime.now(timezone.utc)

        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
        elif not isinstance(updated_at, datetime):
            updated_at = datetime.now(timezone.utc)

        # Use provider table id (not user table id)
        provider_id = provider_data.get("id") or current_user["db_user"].get("profile_id")

        return ProviderProfileResponse(
            id=provider_id,
            full_name=provider_data["full_name"],
            email=current_user["db_user"]["email"],
            phone=provider_data.get("phone"),
            license_url=provider_data.get("license_url"),
            license_status=provider_data.get("license_status", "pending"),
            years_of_experience=provider_data.get("years_of_experience"),
            specialisation=provider_data.get("specialisation"),
            about=provider_data.get("about"),
            created_at=created_at,
            updated_at=updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        # Log the actual error for debugging
        import traceback
        print(f"Error in get_provider_profile: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load provider profile: {str(e)}"
        )

@router.get("/license-url")
async def get_license_presigned_url(
    current_user: Dict = Depends(get_current_provider)
):
    """
    Get presigned URL to view uploaded license

    Returns a temporary URL (valid for 1 hour) to view the license document
    """
    user_id = current_user["db_user"]["id"]

    provider_data = await provider_service.get_provider_profile(user_id)

    if not provider_data or not provider_data.get("license_key"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No license found for this provider"
        )

    try:
        presigned_url = provider_service.get_license_presigned_url(
            license_key=provider_data["license_key"],
            expiration=3600  # 1 hour
        )

        return {
            "url": presigned_url,
            "expires_in": 3600,
            "license_status": provider_data.get("license_status", "pending")
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate view URL: {str(e)}"
        )
