from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime

class LicenseUploadRequest(BaseModel):
    """Request model for license upload with provider details"""
    years_of_experience: Optional[int] = Field(None, ge=0, le=60, description="Years of medical experience (0-60)")
    specialisation: str = Field(..., min_length=1, max_length=200, description="Medical specialisation/field")
    about: Optional[str] = Field(None, max_length=500, description="Short description about the healthcare provider")

    @field_validator('specialisation')
    @classmethod
    def validate_specialisation(cls, v: str) -> str:
        """Ensure specialisation is not empty or just whitespace"""
        if not v or not v.strip():
            raise ValueError('Specialisation cannot be empty')
        return v.strip()

    @field_validator('about')
    @classmethod
    def validate_about(cls, v: Optional[str]) -> Optional[str]:
        """Clean up about text"""
        if v:
            return v.strip() if v.strip() else None
        return v

class LicenseUploadResponse(BaseModel):
    message: str
    license_url: str
    license_key: str
    uploaded_at: datetime

class ProviderProfileResponse(BaseModel):
    id: str
    full_name: str
    email: str
    phone: Optional[str] = None
    license_url: Optional[str] = None
    license_status: Optional[str] = "pending"
    years_of_experience: Optional[int] = None
    specialisation: Optional[str] = None
    about: Optional[str] = None
    created_at: datetime
    updated_at: datetime
