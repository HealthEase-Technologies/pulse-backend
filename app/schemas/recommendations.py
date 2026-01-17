from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# =============================================================================
# ENUMS
# =============================================================================

class RecommendationCategory(str, Enum):
    """Categories for health recommendations"""
    NUTRITION = "nutrition"
    EXERCISE = "exercise"
    SLEEP = "sleep"
    LIFESTYLE = "lifestyle"
    MEDICAL = "medical"
    MENTAL_HEALTH = "mental_health"
    HYDRATION = "hydration"
    MEDICATION = "medication"


class RecommendationPriority(str, Enum):
    """Priority levels for recommendations"""
    URGENT = "urgent"      # Needs immediate attention (critical health values)
    HIGH = "high"          # Important, should address soon
    MEDIUM = "medium"      # Beneficial improvement
    LOW = "low"            # Nice to have, optimization


class RecommendationStatus(str, Enum):
    """Status of a recommendation"""
    ACTIVE = "active"
    IN_PROGRESS = "in_progress"   # User started following
    COMPLETED = "completed"       # User marked as done
    DISMISSED = "dismissed"       # User dismissed
    EXPIRED = "expired"           # Past valid_until date
    SNOOZED = "snoozed"          # User wants reminder later


class UserFeedback(str, Enum):
    """User feedback options for recommendations"""
    HELPFUL = "helpful"
    NOT_HELPFUL = "not_helpful"
    ALREADY_DOING = "already_doing"
    TOO_DIFFICULT = "too_difficult"
    NOT_APPLICABLE = "not_applicable"
    IMPLEMENTED = "implemented"


class DifficultyLevel(str, Enum):
    """How difficult is this recommendation to follow"""
    EASY = "easy"              # Simple habit change
    MODERATE = "moderate"      # Requires some effort
    CHALLENGING = "challenging"  # Significant lifestyle change


class ActionFrequency(str, Enum):
    """How often should user do this action"""
    ONCE = "once"              # One-time action
    DAILY = "daily"
    WEEKLY = "weekly"
    AS_NEEDED = "as_needed"
    ONGOING = "ongoing"        # Continuous habit


# =============================================================================
# UI DISPLAY HELPERS
# =============================================================================

class CategoryDisplay(BaseModel):
    """Category info for UI display"""
    key: str
    label: str
    icon: str
    color: str
    bg_color: str


# Category display mapping for frontend
CATEGORY_DISPLAY_MAP: Dict[str, CategoryDisplay] = {
    "nutrition": CategoryDisplay(
        key="nutrition", label="Nutrition", icon="utensils",
        color="#22c55e", bg_color="#f0fdf4"
    ),
    "exercise": CategoryDisplay(
        key="exercise", label="Exercise", icon="dumbbell",
        color="#3b82f6", bg_color="#eff6ff"
    ),
    "sleep": CategoryDisplay(
        key="sleep", label="Sleep", icon="moon",
        color="#8b5cf6", bg_color="#f5f3ff"
    ),
    "lifestyle": CategoryDisplay(
        key="lifestyle", label="Lifestyle", icon="heart",
        color="#ec4899", bg_color="#fdf2f8"
    ),
    "medical": CategoryDisplay(
        key="medical", label="Medical", icon="stethoscope",
        color="#ef4444", bg_color="#fef2f2"
    ),
    "mental_health": CategoryDisplay(
        key="mental_health", label="Mental Health", icon="brain",
        color="#14b8a6", bg_color="#f0fdfa"
    ),
    "hydration": CategoryDisplay(
        key="hydration", label="Hydration", icon="droplet",
        color="#06b6d4", bg_color="#ecfeff"
    ),
    "medication": CategoryDisplay(
        key="medication", label="Medication", icon="pill",
        color="#f97316", bg_color="#fff7ed"
    ),
}


PRIORITY_DISPLAY_MAP = {
    "urgent": {"label": "Urgent", "color": "#dc2626", "bg_color": "#fef2f2", "icon": "alert-triangle"},
    "high": {"label": "High Priority", "color": "#f97316", "bg_color": "#fff7ed", "icon": "arrow-up"},
    "medium": {"label": "Recommended", "color": "#eab308", "bg_color": "#fefce8", "icon": "minus"},
    "low": {"label": "Suggestion", "color": "#22c55e", "bg_color": "#f0fdf4", "icon": "arrow-down"},
}


# =============================================================================
# REQUEST SCHEMAS
# =============================================================================

class GenerateRecommendationsRequest(BaseModel):
    """Request schema for generating new recommendations"""
    categories: Optional[List[RecommendationCategory]] = Field(
        None,
        description="Specific categories to generate for. If not provided, generates for all."
    )
    force_regenerate: bool = Field(
        False,
        description="If true, generates new even if active ones exist."
    )
    max_recommendations: int = Field(
        5,
        ge=1, le=10,
        description="Maximum number of recommendations to generate"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "categories": ["nutrition", "exercise"],
                "force_regenerate": False,
                "max_recommendations": 5
            }
        }


class FeedbackRequest(BaseModel):
    """Request schema for submitting feedback"""
    feedback: UserFeedback
    notes: Optional[str] = Field(None, max_length=500)
    difficulty_experienced: Optional[DifficultyLevel] = None

    class Config:
        json_schema_extra = {
            "example": {
                "feedback": "helpful",
                "notes": "Started walking after meals, feeling more energetic!",
                "difficulty_experienced": "easy"
            }
        }


class UpdateStatusRequest(BaseModel):
    """Request schema for updating recommendation status"""
    status: RecommendationStatus
    snooze_until: Optional[datetime] = Field(
        None,
        description="If status is 'snoozed', when to remind again"
    )


# =============================================================================
# RESPONSE SCHEMAS
# =============================================================================

class RelatedMetric(BaseModel):
    """Health metric this recommendation relates to"""
    biomarker_type: str
    current_value: Optional[float] = None
    target_value: Optional[float] = None
    unit: str
    status: str  # optimal, normal, concerning, critical
    trend: Optional[str] = None  # improving, stable, declining


class ActionStep(BaseModel):
    """Individual action step within a recommendation"""
    step_number: int
    instruction: str
    tip: Optional[str] = None


class RecommendationResponse(BaseModel):
    """Complete recommendation response for UI display"""
    # Core identifiers
    id: str
    user_id: str

    # Content
    category: RecommendationCategory
    title: str
    description: str
    detailed_explanation: Optional[str] = None

    # Why this recommendation
    reasoning: str  # Based on your data...
    expected_benefit: str  # What improvement to expect
    time_to_results: Optional[str] = None  # "1-2 weeks", "Immediate", etc.

    # Action details
    action_steps: Optional[List[ActionStep]] = None
    frequency: ActionFrequency
    duration: Optional[str] = None  # "2 weeks", "Ongoing", etc.
    best_time: Optional[str] = None  # "Morning", "After meals", etc.

    # Priority & difficulty
    priority: RecommendationPriority
    difficulty: DifficultyLevel
    effort_minutes_per_day: Optional[int] = None  # Estimated time commitment

    # Health context
    related_metrics: Optional[List[RelatedMetric]] = None
    related_goal: Optional[str] = None  # Which health goal this supports
    contraindications: Optional[List[str]] = None  # What to avoid if...

    # Safety & disclaimers
    requires_professional_consultation: bool = False
    safety_warning: Optional[str] = None
    disclaimer: Optional[str] = None

    # AI metadata
    ai_model: Optional[str] = None
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)

    # Status & interaction
    status: RecommendationStatus
    user_feedback: Optional[UserFeedback] = None
    feedback_notes: Optional[str] = None
    progress_percentage: Optional[int] = Field(None, ge=0, le=100)

    # Timestamps
    valid_from: datetime
    valid_until: Optional[datetime] = None
    snoozed_until: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    # UI display helpers (computed fields)
    category_display: Optional[CategoryDisplay] = None
    priority_display: Optional[Dict[str, str]] = None
    is_new: bool = False  # Created in last 24 hours
    is_expiring_soon: bool = False  # Expires in next 48 hours

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "123e4567-e89b-12d3-a456-426614174001",
                "category": "exercise",
                "title": "Add a 10-minute walk after dinner",
                "description": "A short post-meal walk can help regulate blood sugar levels and improve digestion.",
                "detailed_explanation": "Walking after meals helps your muscles use blood sugar, reducing post-meal glucose spikes. This is especially beneficial given your recent glucose readings.",
                "reasoning": "Your evening glucose readings have been averaging 145 mg/dL, which is above the optimal range. Post-meal walks are proven to reduce glucose spikes by 20-30%.",
                "expected_benefit": "Lower post-meal glucose levels, improved digestion, better sleep quality",
                "time_to_results": "1-2 weeks",
                "action_steps": [
                    {"step_number": 1, "instruction": "Wait 15-30 minutes after finishing dinner", "tip": "This allows initial digestion to begin"},
                    {"step_number": 2, "instruction": "Take a light 10-minute walk around your neighborhood", "tip": "Keep a comfortable pace where you can hold a conversation"},
                    {"step_number": 3, "instruction": "Track your post-walk glucose if possible", "tip": "Compare with days you don't walk"}
                ],
                "frequency": "daily",
                "duration": "Ongoing habit",
                "best_time": "15-30 minutes after dinner",
                "priority": "high",
                "difficulty": "easy",
                "effort_minutes_per_day": 10,
                "related_metrics": [
                    {"biomarker_type": "glucose", "current_value": 145, "target_value": 120, "unit": "mg/dL", "status": "concerning", "trend": "stable"}
                ],
                "related_goal": "Manage blood sugar levels",
                "requires_professional_consultation": False,
                "safety_warning": None,
                "disclaimer": "This is a general wellness suggestion. Consult your healthcare provider for personalized medical advice.",
                "ai_model": "gemini-2.0-flash",
                "confidence_score": 0.92,
                "status": "active",
                "user_feedback": None,
                "valid_from": "2024-01-15T00:00:00Z",
                "valid_until": "2024-01-22T00:00:00Z",
                "created_at": "2024-01-15T00:20:00Z",
                "updated_at": "2024-01-15T00:20:00Z",
                "category_display": {
                    "key": "exercise",
                    "label": "Exercise",
                    "icon": "dumbbell",
                    "color": "#3b82f6",
                    "bg_color": "#eff6ff"
                },
                "priority_display": {
                    "label": "High Priority",
                    "color": "#f97316",
                    "bg_color": "#fff7ed",
                    "icon": "arrow-up"
                },
                "is_new": True,
                "is_expiring_soon": False
            }
        }


class RecommendationSummary(BaseModel):
    """Compact recommendation for list views"""
    id: str
    category: RecommendationCategory
    title: str
    priority: RecommendationPriority
    difficulty: DifficultyLevel
    status: RecommendationStatus
    frequency: ActionFrequency
    effort_minutes_per_day: Optional[int] = None
    confidence_score: Optional[float] = None
    user_feedback: Optional[UserFeedback] = None
    is_new: bool = False
    created_at: datetime

    # UI helpers
    category_display: Optional[CategoryDisplay] = None
    priority_display: Optional[Dict[str, str]] = None


class RecommendationListResponse(BaseModel):
    """Response for list of recommendations"""
    recommendations: List[RecommendationResponse]
    total_count: int

    # Summary stats for UI dashboard
    by_category: Dict[str, int] = {}  # Count per category
    by_priority: Dict[str, int] = {}  # Count per priority
    by_status: Dict[str, int] = {}    # Count per status

    urgent_count: int = 0
    new_count: int = 0  # Created in last 24 hours
    in_progress_count: int = 0
    completion_rate: Optional[float] = None  # % of completed vs total historical

    class Config:
        json_schema_extra = {
            "example": {
                "recommendations": [],
                "total_count": 5,
                "by_category": {"exercise": 2, "nutrition": 2, "sleep": 1},
                "by_priority": {"high": 2, "medium": 2, "low": 1},
                "by_status": {"active": 4, "in_progress": 1},
                "urgent_count": 0,
                "new_count": 3,
                "in_progress_count": 1,
                "completion_rate": 0.75
            }
        }


class GenerateRecommendationsResponse(BaseModel):
    """Response for generate recommendations endpoint"""
    generated_count: int
    recommendations: List[RecommendationResponse]
    message: str
    skipped_categories: Optional[List[str]] = None  # Categories that already had active recs

    class Config:
        json_schema_extra = {
            "example": {
                "generated_count": 4,
                "recommendations": [],
                "message": "Generated 4 new personalized recommendations",
                "skipped_categories": ["sleep"]
            }
        }


# =============================================================================
# HEALTH CONTEXT FOR AI
# =============================================================================

class BiomarkerContext(BaseModel):
    """Biomarker data for AI context"""
    biomarker_type: str
    current_avg: float
    min_value: float
    max_value: float
    readings_count: int
    unit: str
    status: str  # optimal, normal, concerning, critical
    trend: str   # improving, stable, declining
    days_of_data: int
    optimal_range: Optional[Dict[str, float]] = None  # min_optimal, max_optimal


class PatientProfileContext(BaseModel):
    """Patient profile for AI context"""
    age: int
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    bmi: Optional[float] = None
    health_goals: List[Dict[str, str]]  # [{"goal": "...", "frequency": "..."}]
    health_restrictions: List[str]
    goal_completion_rate_7d: Optional[float] = None  # Last 7 days


class HealthContext(BaseModel):
    """Complete health context passed to AI for recommendation generation"""
    patient_profile: PatientProfileContext
    biomarkers: List[BiomarkerContext]
    latest_summary: Optional[Dict[str, Any]] = None  # From daily_health_summaries
    active_alerts: List[str] = []
    recent_insights: List[str] = []
    overall_health_status: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "patient_profile": {
                    "age": 45,
                    "height_cm": 175,
                    "weight_kg": 82,
                    "bmi": 26.8,
                    "health_goals": [
                        {"goal": "Lower blood pressure", "frequency": "ongoing"},
                        {"goal": "Walk 10000 steps", "frequency": "daily"}
                    ],
                    "health_restrictions": ["Hypertension", "Pre-diabetes"],
                    "goal_completion_rate_7d": 0.65
                },
                "biomarkers": [
                    {
                        "biomarker_type": "blood_pressure_systolic",
                        "current_avg": 138,
                        "min_value": 125,
                        "max_value": 152,
                        "readings_count": 14,
                        "unit": "mmHg",
                        "status": "concerning",
                        "trend": "stable",
                        "days_of_data": 7,
                        "optimal_range": {"min_optimal": 90, "max_optimal": 120}
                    }
                ],
                "active_alerts": ["Elevated blood pressure detected"],
                "recent_insights": ["Heart rate within normal range"],
                "overall_health_status": "needs_attention"
            }
        }


# =============================================================================
# EMAIL DATA
# =============================================================================

class RecommendationEmailData(BaseModel):
    """Recommendation data formatted for email templates"""
    title: str
    description: str
    category: str
    category_icon: str
    priority: str
    priority_color: str
    action_summary: Optional[str] = None  # Brief "Do this: X"
    time_commitment: Optional[str] = None  # "10 min/day"
