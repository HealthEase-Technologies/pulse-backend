from pydantic import BaseModel
from typing import Optional
from datetime import datetime

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
    created_at: datetime
    updated_at: datetime
