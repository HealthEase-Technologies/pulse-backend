from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class BiomarkerType(str, Enum):
    """Supported biomarker types"""
    HEART_RATE = "heart_rate"
    BLOOD_PRESSURE_SYSTOLIC = "blood_pressure_systolic"
    BLOOD_PRESSURE_DIASTOLIC = "blood_pressure_diastolic"
    GLUCOSE = "glucose"
    STEPS = "steps"
    SLEEP = "sleep"


class BiomarkerSource(str, Enum):
    """Source of biomarker data"""
    DEVICE = "device"
    MANUAL = "manual"


class BiomarkerRangeResponse(BaseModel):
    """Biomarker reference range schema"""
    id: str
    biomarker_type: str
    unit: str
    min_normal: Optional[float] = None
    max_normal: Optional[float] = None
    min_optimal: Optional[float] = None
    max_optimal: Optional[float] = None
    critical_low: Optional[float] = None
    critical_high: Optional[float] = None
    description: Optional[str] = None
    created_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "biomarker_type": "heart_rate",
                "unit": "bpm",
                "min_normal": 60,
                "max_normal": 100,
                "min_optimal": 60,
                "max_optimal": 80,
                "critical_low": 40,
                "critical_high": 120,
                "description": "Resting heart rate for adults",
                "created_at": "2024-01-15T10:00:00Z"
            }
        }


class InsertBiomarkerRequest(BaseModel):
    """Request to insert biomarker data"""
    biomarker_type: BiomarkerType = Field(..., description="Type of biomarker")
    value: float = Field(..., ge=0, description="Biomarker value (must be non-negative)")
    unit: str = Field(..., description="Unit of measurement (bpm, mmHg, mg/dL, steps, hours)")
    source: BiomarkerSource = Field(default=BiomarkerSource.MANUAL, description="Source of data")
    device_id: Optional[str] = Field(None, description="Device ID if source is device")
    recorded_at: Optional[datetime] = Field(None, description="When the reading was taken (defaults to now)")
    notes: Optional[str] = Field(None, max_length=500, description="Optional notes for manual entries")

    class Config:
        json_schema_extra = {
            "example": {
                "biomarker_type": "heart_rate",
                "value": 72,
                "unit": "bpm",
                "source": "manual",
                "device_id": None,
                "recorded_at": "2024-01-15T10:00:00Z",
                "notes": "Taken after morning walk"
            }
        }


class BiomarkerResponse(BaseModel):
    """Biomarker data response schema"""
    id: str
    user_id: str
    device_id: Optional[str] = None
    biomarker_type: str
    value: float
    unit: str
    source: str
    recorded_at: datetime
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "123e4567-e89b-12d3-a456-426614174001",
                "device_id": None,
                "biomarker_type": "heart_rate",
                "value": 72,
                "unit": "bpm",
                "source": "manual",
                "recorded_at": "2024-01-15T10:00:00Z",
                "notes": "Taken after morning walk",
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T10:00:00Z"
            }
        }


class LatestBiomarkerReading(BaseModel):
    """Latest biomarker reading summary"""
    biomarker_type: str
    value: float
    unit: str
    recorded_at: datetime
    source: str
    status: Optional[str] = Field(None, description="Health status: normal, optimal, critical_low, critical_high")

    class Config:
        json_schema_extra = {
            "example": {
                "biomarker_type": "heart_rate",
                "value": 72,
                "unit": "bpm",
                "recorded_at": "2024-01-15T10:00:00Z",
                "source": "manual",
                "status": "optimal"
            }
        }


class BiomarkerDashboardSummary(BaseModel):
    """Dashboard summary of all latest biomarker readings"""
    heart_rate: Optional[LatestBiomarkerReading] = None
    blood_pressure_systolic: Optional[LatestBiomarkerReading] = None
    blood_pressure_diastolic: Optional[LatestBiomarkerReading] = None
    glucose: Optional[LatestBiomarkerReading] = None
    steps: Optional[LatestBiomarkerReading] = None
    sleep: Optional[LatestBiomarkerReading] = None

    class Config:
        json_schema_extra = {
            "example": {
                "heart_rate": {
                    "biomarker_type": "heart_rate",
                    "value": 72,
                    "unit": "bpm",
                    "recorded_at": "2024-01-15T10:00:00Z",
                    "source": "device",
                    "status": "optimal"
                },
                "steps": {
                    "biomarker_type": "steps",
                    "value": 8500,
                    "unit": "steps",
                    "recorded_at": "2024-01-15T10:00:00Z",
                    "source": "device",
                    "status": "normal"
                }
            }
        }
