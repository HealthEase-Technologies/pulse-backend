from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.schemas.biomarker import BiomarkerType


# =============================================================================
# REQUEST SCHEMAS
# =============================================================================

class ThresholdCreate(BaseModel):
    """Create or update a custom threshold for a patient's biomarker"""
    biomarker_type: BiomarkerType
    warning_low: Optional[float] = Field(None, description="Warning threshold - low value")
    warning_high: Optional[float] = Field(None, description="Warning threshold - high value")
    critical_low: Optional[float] = Field(None, description="Critical threshold - low value")
    critical_high: Optional[float] = Field(None, description="Critical threshold - high value")


# =============================================================================
# RESPONSE SCHEMAS
# =============================================================================

class ThresholdResponse(BaseModel):
    """Full threshold record response"""
    id: str
    patient_user_id: str
    set_by_user_id: str
    set_by_role: str
    biomarker_type: str
    warning_low: Optional[float] = None
    warning_high: Optional[float] = None
    critical_low: Optional[float] = None
    critical_high: Optional[float] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class EffectiveThreshold(BaseModel):
    """Resolved threshold after applying hierarchy (provider > patient > global)"""
    biomarker_type: str
    warning_low: Optional[float] = None
    warning_high: Optional[float] = None
    critical_low: Optional[float] = None
    critical_high: Optional[float] = None
    source: str  # 'provider', 'patient', or 'global'
