from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date


class EmergencyContact(BaseModel):
    """Emergency contact information"""
    name: str = Field(..., min_length=1, max_length=100)
    relationship: str = Field(..., min_length=1, max_length=50)
    phone: str = Field(..., min_length=10, max_length=20)


class HealthGoal(BaseModel):
    """Health goal with frequency"""
    goal: str = Field(..., min_length=1, max_length=200, description="Goal description")
    frequency: str = Field(..., pattern="^(daily|weekly|monthly)$", description="Goal frequency")


class PatientProfileResponse(BaseModel):
    """Patient profile response schema"""
    id: str
    user_id: str
    full_name: str
    date_of_birth: Optional[date] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    health_goals: Optional[List[HealthGoal]] = []
    health_restrictions: Optional[str] = None
    reminder_frequency: Optional[str] = "daily"
    emergency_contacts: Optional[List[EmergencyContact]] = []
    onboarding_completed: bool = False
    connected_provider_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "123e4567-e89b-12d3-a456-426614174001",
                "full_name": "John Doe",
                "date_of_birth": "1990-01-15",
                "height_cm": 175.5,
                "weight_kg": 70.0,
                "health_goals": [
                    {"goal": "Exercise 30 mins", "frequency": "daily"},
                    {"goal": "Drink 8 glasses of water", "frequency": "daily"}
                ],
                "health_restrictions": "Diabetes,Hypertension",
                "reminder_frequency": "daily",
                "emergency_contacts": [
                    {
                        "name": "Jane Doe",
                        "relationship": "Spouse",
                        "phone": "+1234567890"
                    }
                ],
                "onboarding_completed": True,
                "connected_provider_id": None,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }


class PatientOnboardingData(BaseModel):
    """Patient onboarding data schema"""
    date_of_birth: date = Field(..., description="Date of birth (YYYY-MM-DD)")
    height_cm: float = Field(..., ge=50, le=300, description="Height in centimeters")
    weight_kg: float = Field(..., ge=20, le=500, description="Weight in kilograms")
    health_goals: List[HealthGoal] = Field(..., min_length=1, max_length=10, description="List of health goals")
    health_restrictions: List[str] = Field(default=[], max_length=20, description="List of health restrictions")
    reminder_frequency: str = Field(default="daily", pattern="^(daily|weekly|monthly|none)$")
    emergency_contacts: List[EmergencyContact] = Field(default=[], max_length=3, description="Up to 3 emergency contacts")

    class Config:
        json_schema_extra = {
            "example": {
                "date_of_birth": "1990-01-15",
                "height_cm": 175.5,
                "weight_kg": 70.0,
                "health_goals": [
                    {"goal": "Exercise 30 mins daily", "frequency": "daily"},
                    {"goal": "Meditation", "frequency": "daily"}
                ],
                "health_restrictions": ["Diabetes", "Hypertension"],
                "reminder_frequency": "daily",
                "emergency_contacts": [
                    {
                        "name": "Jane Doe",
                        "relationship": "Spouse",
                        "phone": "+1234567890"
                    }
                ]
            }
        }


class PatientOnboardingResponse(BaseModel):
    """Response after completing onboarding"""
    message: str
    profile: PatientProfileResponse


class PatientProfileUpdate(BaseModel):
    """Patient profile update schema (all fields optional)"""
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    date_of_birth: Optional[date] = None
    height_cm: Optional[float] = Field(None, ge=50, le=300)
    weight_kg: Optional[float] = Field(None, ge=20, le=500)
    health_goals: Optional[List[HealthGoal]] = Field(None, max_length=10)
    health_restrictions: Optional[List[str]] = Field(None, max_length=20)
    reminder_frequency: Optional[str] = Field(None, pattern="^(daily|weekly|monthly|none)$")
    emergency_contacts: Optional[List[EmergencyContact]] = Field(None, max_length=3)

    class Config:
        json_schema_extra = {
            "example": {
                "full_name": "John Smith",
                "height_cm": 180.0,
                "weight_kg": 75.0,
                "health_goals": [
                    {"goal": "Walk 10000 steps", "frequency": "daily"}
                ],
                "reminder_frequency": "weekly"
            }
        }


class OnboardingStatusResponse(BaseModel):
    """Onboarding status check response"""
    completed: bool
    exists: bool
    profile: Optional[PatientProfileResponse] = None
