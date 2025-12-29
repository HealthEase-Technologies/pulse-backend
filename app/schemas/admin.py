from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class LicenseStatus(str, Enum):
    """Provider license status options"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class AdminAction(str, Enum):
    """Admin action types for audit logging"""
    LICENSE_APPROVED = "license_approved"
    LICENSE_REJECTED = "license_rejected"
    VIEW_LICENSE = "view_license"
    UPDATE_PROVIDER = "update_provider"
    DELETE_PROVIDER = "delete_provider"
    UPDATE_USER = "update_user"
    DELETE_USER = "delete_user"


class AdminAuditLogResponse(BaseModel):
    """Admin audit log response schema"""
    id: str
    admin_id: str
    action: str
    target_user_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "admin_id": "123e4567-e89b-12d3-a456-426614174001",
                "action": "license_approved",
                "target_user_id": "123e4567-e89b-12d3-a456-426614174002",
                "details": {
                    "provider_id": "123e4567-e89b-12d3-a456-426614174003",
                    "previous_status": "pending",
                    "new_status": "approved"
                },
                "created_at": "2024-01-15T14:30:00Z"
            }
        }


class ProviderListResponse(BaseModel):
    """Provider list item response"""
    id: str
    user_id: str
    full_name: str
    email: Optional[str] = None
    username: Optional[str] = None
    license_url: Optional[str] = None
    license_key: Optional[str] = None
    license_status: str
    license_verified_at: Optional[datetime] = None
    license_verified_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "123e4567-e89b-12d3-a456-426614174001",
                "full_name": "Dr. John Smith",
                "email": "dr.smith@example.com",
                "username": "drsmith",
                "license_url": "https://s3.amazonaws.com/licenses/...",
                "license_key": "licenses/license_123.pdf",
                "license_status": "pending",
                "license_verified_at": None,
                "license_verified_by": None,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }


class UpdateLicenseStatusRequest(BaseModel):
    """Request to update provider license status"""
    status: LicenseStatus = Field(..., description="New license status (approved/rejected)")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "approved"
            }
        }


class UpdateLicenseStatusResponse(BaseModel):
    """Response after updating license status"""
    message: str
    provider_id: str
    new_status: str
    verified_at: datetime
    verified_by: str


class ProviderUpdateRequest(BaseModel):
    """Request to update provider information"""
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    license_status: Optional[LicenseStatus] = None

    class Config:
        json_schema_extra = {
            "example": {
                "full_name": "Dr. Jane Smith",
                "license_status": "approved"
            }
        }


class UserWithRoleResponse(BaseModel):
    """User response with role-specific data"""
    id: str
    cognito_id: str
    username: str
    email: str
    role: int
    role_name: str
    full_name: Optional[str] = None
    is_active: bool
    created_at: datetime
    license_status: Optional[str] = None  # Only for providers

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "cognito_id": "123e4567-e89b-12d3-a456-426614174001",
                "username": "johnsmith",
                "email": "john@example.com",
                "role": 1,
                "role_name": "Patient",
                "full_name": "John Smith",
                "is_active": True,
                "created_at": "2024-01-01T00:00:00Z",
                "license_status": None
            }
        }


class LicenseUrlResponse(BaseModel):
    """Response with presigned URL for license"""
    url: str = Field(..., description="Presigned URL for viewing the license")
    expires_in: int = Field(default=3600, description="URL expiration time in seconds")

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://s3.amazonaws.com/licenses/...?presigned-params",
                "expires_in": 3600
            }
        }


class DeleteProviderResponse(BaseModel):
    """Response after deleting provider"""
    message: str
    deleted_user_id: str

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Provider Dr. John Smith deleted successfully",
                "deleted_user_id": "123e4567-e89b-12d3-a456-426614174001"
            }
        }
