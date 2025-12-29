from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.auth.dependencies import get_current_admin
from app.services.admin_service import admin_service
from app.schemas.admin import (
    UpdateLicenseStatusRequest,
    ProviderUpdateRequest,
    ProviderListResponse,
    LicenseUrlResponse,
    DeleteProviderResponse,
    UserWithRoleResponse
)
from typing import Dict, List, Optional, Any

router = APIRouter(prefix="/admins", tags=["admins"])


@router.get("/providers", response_model=Dict[str, Any])
async def get_all_providers(
    license_status: Optional[str] = Query(None, description="Filter by license status"),
    current_user: Dict = Depends(get_current_admin)
):
    """
    Get all providers with their license status (Admin only)

    Query params:
    - license_status: Filter by 'pending', 'approved', or 'rejected'

    Requirements: U-FR-2-7 (Admin license verification)
    """
    try:
        providers = await admin_service.get_all_providers(license_status=license_status)
        return {
            "total": len(providers),
            "providers": providers
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch providers: {str(e)}"
        )


@router.patch("/providers/{provider_id}/license-status")
async def update_provider_license_status(
    provider_id: str,
    status_update: UpdateLicenseStatusRequest,
    current_user: Dict = Depends(get_current_admin)
):
    """
    Approve or reject a provider's medical license (Admin only)

    Requirements: U-FR-2-7 (Admin license verification)
    """
    try:
        admin_user_id = current_user["db_user"]["id"]

        updated_provider = await admin_service.update_license_status(
            provider_id=provider_id,
            new_status=status_update.status,
            admin_id=admin_user_id
        )

        return {
            "message": f"License {status_update.status} successfully",
            "provider": updated_provider
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update license status: {str(e)}"
        )


@router.get("/providers/{provider_id}/license-url", response_model=LicenseUrlResponse)
async def get_provider_license_url(
    provider_id: str,
    current_user: Dict = Depends(get_current_admin)
):
    """
    Get presigned URL for viewing a provider's license (Admin only)

    Requirements: U-FR-2-7 (Admin license verification)
    """
    try:
        admin_user_id = current_user["db_user"]["id"]

        presigned_url = await admin_service.get_provider_license_url(
            provider_id=provider_id,
            admin_id=admin_user_id
        )

        return {
            "url": presigned_url
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get license URL: {str(e)}"
        )


@router.patch("/providers/{provider_id}")
async def update_provider(
    provider_id: str,
    provider_update: ProviderUpdateRequest,
    current_user: Dict = Depends(get_current_admin)
):
    """
    Update provider profile data (Admin only)

    Requirements: U-FR-2-4 (Admin provider management)
    """
    try:
        admin_user_id = current_user["db_user"]["id"]

        # Convert Pydantic model to dict and remove None values
        update_data = {k: v for k, v in provider_update.model_dump().items() if v is not None}

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )

        updated_provider = await admin_service.update_provider(
            provider_id=provider_id,
            update_data=update_data,
            admin_id=admin_user_id
        )

        return {
            "message": "Provider updated successfully",
            "provider": updated_provider
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update provider: {str(e)}"
        )


@router.delete("/providers/{provider_id}", response_model=DeleteProviderResponse)
async def delete_provider(
    provider_id: str,
    current_user: Dict = Depends(get_current_admin)
):
    """
    Delete a provider (Admin only)

    Requirements: U-FR-2-4 (Admin provider management)
    """
    try:
        admin_user_id = current_user["db_user"]["id"]

        result = await admin_service.delete_provider(
            provider_id=provider_id,
            admin_id=admin_user_id
        )

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete provider: {str(e)}"
        )


@router.get("/users", response_model=Dict[str, Any])
async def get_all_users(
    current_user: Dict = Depends(get_current_admin)
):
    """
    Get all users in the system (Admin only)

    Requirements: U-FR-2-4 (Admin user management)
    """
    try:
        users = await admin_service.get_all_users()
        return {
            "total": len(users),
            "users": users
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch users: {str(e)}"
        )
