from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from enum import Enum


class SummaryType(str, Enum):
    """Type of health summary"""
    MORNING_BRIEFING = "morning_briefing"
    EVENING_SUMMARY = "evening_summary"


class OverallHealthStatus(str, Enum):
    """Overall health status categories"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    NEEDS_ATTENTION = "needs_attention"
    CRITICAL = "critical"


class BiomarkerMetricSummary(BaseModel):
    """Summary statistics for a single biomarker"""
    avg: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    readings_count: int = 0
    status: str  # optimal, normal, elevated, critical
    trend: Optional[str] = None  # improving, stable, declining

    class Config:
        json_schema_extra = {
            "example": {
                "avg": 72,
                "min": 58,
                "max": 95,
                "readings_count": 12,
                "status": "good",
                "trend": "stable"
            }
        }


class StepsSummary(BaseModel):
    """Steps summary for the day"""
    total: int
    goal: Optional[int] = 10000
    percentage: Optional[float] = None
    status: str

    class Config:
        json_schema_extra = {
            "example": {
                "total": 8547,
                "goal": 10000,
                "percentage": 85.47,
                "status": "good"
            }
        }


class SleepSummary(BaseModel):
    """Sleep summary for the day"""
    hours: float
    goal: Optional[float] = 8.0
    status: str

    class Config:
        json_schema_extra = {
            "example": {
                "hours": 7.5,
                "goal": 8.0,
                "status": "good"
            }
        }


class BloodPressureSummary(BaseModel):
    """Blood pressure summary"""
    systolic_avg: Optional[float] = None
    diastolic_avg: Optional[float] = None
    readings_count: int = 0
    status: str
    trend: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "systolic_avg": 118,
                "diastolic_avg": 76,
                "readings_count": 3,
                "status": "optimal",
                "trend": "improving"
            }
        }


class DailyMetricsSummary(BaseModel):
    """All daily metrics aggregated"""
    heart_rate: Optional[BiomarkerMetricSummary] = None
    blood_pressure: Optional[BloodPressureSummary] = None
    glucose: Optional[BiomarkerMetricSummary] = None
    steps: Optional[StepsSummary] = None
    sleep: Optional[SleepSummary] = None

    class Config:
        json_schema_extra = {
            "example": {
                "heart_rate": {
                    "avg": 72,
                    "min": 58,
                    "max": 95,
                    "readings_count": 12,
                    "status": "good",
                    "trend": "stable"
                },
                "steps": {
                    "total": 8547,
                    "goal": 10000,
                    "percentage": 85.47,
                    "status": "good"
                }
            }
        }


class HealthSummaryData(BaseModel):
    """Complete health summary data structure (stored in JSONB)"""
    date: date
    summary_type: str
    metrics: DailyMetricsSummary
    insights: List[str] = []
    alerts: List[str] = []
    recommendations: List[str] = []  # Future implementation
    daily_achievements: Optional[List[str]] = []
    areas_for_improvement: Optional[List[str]] = []

    class Config:
        json_schema_extra = {
            "example": {
                "date": "2024-01-15",
                "summary_type": "morning_briefing",
                "metrics": {
                    "heart_rate": {
                        "avg": 72,
                        "readings_count": 12,
                        "status": "good",
                        "trend": "stable"
                    },
                    "steps": {
                        "total": 8547,
                        "goal": 10000,
                        "percentage": 85.47,
                        "status": "good"
                    }
                },
                "insights": [
                    "Your average heart rate was within optimal range",
                    "You achieved 85% of your daily step goal"
                ],
                "alerts": [],
                "recommendations": []
            }
        }


class DailyHealthSummaryResponse(BaseModel):
    """Daily health summary response"""
    id: str
    user_id: str
    summary_date: date
    summary_type: SummaryType
    summary_data: Dict[str, Any]  # JSONB data
    total_readings: int
    biomarkers_tracked: List[str]
    has_critical_values: bool
    has_concerning_values: bool
    overall_status: Optional[OverallHealthStatus] = None
    email_sent: bool
    email_sent_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "123e4567-e89b-12d3-a456-426614174001",
                "summary_date": "2024-01-15",
                "summary_type": "morning_briefing",
                "summary_data": {
                    "date": "2024-01-15",
                    "metrics": {},
                    "insights": [],
                    "alerts": []
                },
                "total_readings": 45,
                "biomarkers_tracked": ["heart_rate", "steps", "sleep"],
                "has_critical_values": False,
                "has_concerning_values": False,
                "overall_status": "good",
                "email_sent": True,
                "email_sent_at": "2024-01-16T00:05:00Z",
                "created_at": "2024-01-16T00:01:00Z",
                "updated_at": "2024-01-16T00:01:00Z"
            }
        }


class MorningBriefingEmailData(BaseModel):
    """Data structure for morning briefing email template"""
    user_name: str
    summary_date: date
    overall_status: str
    metrics_summary: DailyMetricsSummary
    insights: List[str]
    alerts: List[str]
    has_critical_alerts: bool

    class Config:
        json_schema_extra = {
            "example": {
                "user_name": "John Doe",
                "summary_date": "2024-01-15",
                "overall_status": "good",
                "metrics_summary": {},
                "insights": ["Your heart rate was optimal yesterday"],
                "alerts": [],
                "has_critical_alerts": False
            }
        }
