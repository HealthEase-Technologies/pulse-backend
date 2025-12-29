from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date
from enum import Enum


class GoalStatus(str, Enum):
    """Goal completion status"""
    PENDING = "pending"
    COMPLETED = "completed"
    MISSED = "missed"


class GoalFrequency(str, Enum):
    """Goal frequency options"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class GoalCompletionCreate(BaseModel):
    """Create goal completion record"""
    goal_text: str = Field(..., min_length=1, max_length=200, description="Goal description")
    goal_frequency: GoalFrequency = Field(..., description="Goal frequency")
    completion_date: date = Field(..., description="Date for this goal completion")

    class Config:
        json_schema_extra = {
            "example": {
                "goal_text": "Exercise 30 minutes",
                "goal_frequency": "daily",
                "completion_date": "2024-01-15"
            }
        }


class GoalCompletionResponse(BaseModel):
    """Goal completion response schema"""
    id: str
    user_id: str
    goal_text: str
    goal_frequency: str
    completion_date: date
    status: GoalStatus
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "123e4567-e89b-12d3-a456-426614174001",
                "goal_text": "Exercise 30 minutes",
                "goal_frequency": "daily",
                "completion_date": "2024-01-15",
                "status": "completed",
                "completed_at": "2024-01-15T14:30:00Z",
                "created_at": "2024-01-15T00:00:00Z",
                "updated_at": "2024-01-15T14:30:00Z"
            }
        }


class MarkGoalRequest(BaseModel):
    """Request to mark goal as complete"""
    goal_text: str = Field(..., min_length=1, max_length=200)
    goal_frequency: GoalFrequency
    completion_date: date

    class Config:
        json_schema_extra = {
            "example": {
                "goal_text": "Exercise 30 minutes",
                "goal_frequency": "daily",
                "completion_date": "2024-01-15"
            }
        }


class UnmarkGoalRequest(BaseModel):
    """Request to unmark goal completion"""
    goal_text: str = Field(..., min_length=1, max_length=200)
    completion_date: date

    class Config:
        json_schema_extra = {
            "example": {
                "goal_text": "Exercise 30 minutes",
                "completion_date": "2024-01-15"
            }
        }


class GoalStatsResponse(BaseModel):
    """Goal completion statistics"""
    total_tracked: int = Field(..., description="Total number of goal instances tracked")
    total_completed: int = Field(..., description="Number of goals completed")
    total_missed: int = Field(..., description="Number of goals missed")
    completion_rate: float = Field(..., ge=0, le=100, description="Completion rate percentage")
    current_streak: int = Field(..., ge=0, description="Current consecutive days streak")
    longest_streak: int = Field(..., ge=0, description="Longest consecutive days streak")

    class Config:
        json_schema_extra = {
            "example": {
                "total_tracked": 100,
                "total_completed": 85,
                "total_missed": 15,
                "completion_rate": 85.0,
                "current_streak": 7,
                "longest_streak": 14
            }
        }


class InitializeDailyGoalsResponse(BaseModel):
    """Response after initializing daily goals"""
    message: str
    goals_created: int
    goals: list[GoalCompletionResponse]

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Daily goals initialized successfully",
                "goals_created": 3,
                "goals": []
            }
        }


class MarkMissedGoalsResponse(BaseModel):
    """Response after marking missed goals"""
    message: str
    goals_marked_missed: int

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Missed goals marked successfully",
                "goals_marked_missed": 5
            }
        }
