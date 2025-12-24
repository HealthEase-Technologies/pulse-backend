from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

# Note: Health data tracking schemas below are prepared for future implementation
# Currently, only basic patient health goals are tracked via patients.py router
# These schemas will be used when implementing advanced health tracking features
# (heart rate monitoring, blood pressure tracking, steps counting, etc.)

class HealthMetricType(str, Enum):
    HEART_RATE = "heart_rate"
    BLOOD_PRESSURE = "blood_pressure"  
    STEPS = "steps"
    SLEEP = "sleep"
    BLOOD_GLUCOSE = "blood_glucose"

class BloodPressure(BaseModel):
    systolic: int = Field(..., ge=70, le=250, description="Systolic blood pressure (top number)")
    diastolic: int = Field(..., ge=40, le=150, description="Diastolic blood pressure (bottom number)")
    
    def __str__(self):
        return f"{self.systolic}/{self.diastolic}"
    
    @property
    def category(self) -> str:
        """Return blood pressure category based on AHA guidelines"""
        if self.systolic < 120 and self.diastolic < 80:
            return "Normal"
        elif self.systolic < 130 and self.diastolic < 80:
            return "Elevated"
        elif self.systolic < 140 or self.diastolic < 90:
            return "High Blood Pressure Stage 1"
        elif self.systolic < 180 or self.diastolic < 120:
            return "High Blood Pressure Stage 2"
        else:
            return "Hypertensive Crisis"

class HealthDataCreate(BaseModel):
    heart_rate: Optional[int] = Field(None, ge=40, le=200, description="Heart rate in BPM")
    blood_pressure: Optional[BloodPressure] = Field(None, description="Blood pressure reading")
    steps: Optional[int] = Field(None, ge=0, le=100000, description="Daily step count")
    sleep_hours: Optional[float] = Field(None, ge=0, le=24, description="Hours of sleep")
    blood_glucose: Optional[float] = Field(None, ge=0, le=500, description="Blood glucose mg/dL")

class HealthDataUpdate(BaseModel):
    heart_rate: Optional[int] = Field(None, ge=40, le=200)
    blood_pressure: Optional[BloodPressure] = None
    steps: Optional[int] = Field(None, ge=0, le=100000)
    sleep_hours: Optional[float] = Field(None, ge=0, le=24)
    blood_glucose: Optional[float] = Field(None, ge=0, le=500)

class HealthDataResponse(BaseModel):
    id: str
    user_id: str
    heart_rate: Optional[int]
    blood_pressure: Optional[BloodPressure]
    steps: Optional[int]
    sleep_hours: Optional[float]
    blood_glucose: Optional[float]
    recorded_at: datetime
    created_at: datetime
    
    @classmethod
    def from_db_row(cls, row: dict):
        """Convert database row to response model"""
        bp = None
        if row.get('blood_pressure_systolic') and row.get('blood_pressure_diastolic'):
            bp = BloodPressure(
                systolic=row['blood_pressure_systolic'],
                diastolic=row['blood_pressure_diastolic']
            )
        
        return cls(
            id=row['id'],
            user_id=row['user_id'],
            heart_rate=row.get('heart_rate'),
            blood_pressure=bp,
            steps=row.get('steps'),
            sleep_hours=row.get('sleep_hours'),
            blood_glucose=row.get('blood_glucose'),
            recorded_at=row['recorded_at'],
            created_at=row['created_at']
        )

class HealthDataStats(BaseModel):
    """Statistics for health data over a period"""
    metric_type: HealthMetricType
    count: int
    average: Optional[float]
    min_value: Optional[float]
    max_value: Optional[float]
    latest_value: Optional[float]
    trend: Optional[str]  # "improving", "declining", "stable"