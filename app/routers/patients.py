from fastapi import APIRouter, Depends, HTTPException, status
from app.auth.dependencies import get_current_patient
from app.services.patient_service import patient_service
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import date


router = APIRouter(prefix="/patients", tags=["patients"])


class EmergencyContact(BaseModel):
    name: str = Field(..., description="Emergency contact name")
    phone: str = Field(..., description="Emergency contact phone")
    relationship: str = Field(..., description="Relationship to patient")


class HealthGoal(BaseModel):
    goal: str = Field(..., description="Health goal description")
    frequency: str = Field(..., description="Goal frequency: daily, weekly, monthly")


class OnboardingData(BaseModel):
    date_of_birth: date = Field(..., description="Patient's date of birth")
    height_cm: float = Field(..., gt=0, description="Height in centimeters")
    weight_kg: float = Field(..., gt=0, description="Weight in kilograms")
    health_goals: List[HealthGoal] = Field(..., description="List of health goals with frequency")
    health_restrictions: List[str] = Field(default=[], description="List of health restrictions")
    reminder_frequency: str = Field(default="daily", description="Reminder frequency: daily, weekly, monthly, none")
    emergency_contacts: List[EmergencyContact] = Field(default=[], max_length=3, description="Up to 3 emergency contacts")


class ProfileUpdateData(BaseModel):
    date_of_birth: Optional[date] = None
    height_cm: Optional[float] = Field(None, gt=0)
    weight_kg: Optional[float] = Field(None, gt=0)
    health_goals: Optional[List[HealthGoal]] = None
    health_restrictions: Optional[List[str]] = None
    reminder_frequency: Optional[str] = Field(None, description="Reminder frequency: daily, weekly, monthly, none")
    emergency_contacts: Optional[List[EmergencyContact]] = Field(None, max_length=3)


@router.get("/profile")
async def get_patient_profile(
    current_user: Dict = Depends(get_current_patient)
):
    """
    Get current patient's profile

    Requirements: Patient authentication
    """
    try:
        user_id = current_user["db_user"]["id"]
        profile = await patient_service.get_patient_profile(user_id)

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient profile not found"
            )

        # health_goals is already JSONB array, no conversion needed
        # Ensure health_goals has default value if null
        if not profile.get("health_goals"):
            profile["health_goals"] = []

        # Convert comma-separated health_restrictions to array for frontend
        if profile.get("health_restrictions"):
            profile["health_restrictions"] = profile["health_restrictions"].split(",")
        else:
            profile["health_restrictions"] = []

        return profile

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch profile: {str(e)}"
        )


@router.get("/onboarding/status")
async def check_onboarding_status(
    current_user: Dict = Depends(get_current_patient)
):
    """
    Check if patient has completed onboarding

    Requirements: Patient authentication
    """
    try:
        user_id = current_user["db_user"]["id"]
        status_result = await patient_service.check_onboarding_status(user_id)

        # Convert health_restrictions to arrays if profile exists
        # health_goals is already JSONB array, no conversion needed
        if status_result.get("profile"):
            profile = status_result["profile"]

            # Ensure health_goals has default value if null
            if not profile.get("health_goals"):
                profile["health_goals"] = []

            # Convert comma-separated health_restrictions to array
            if profile.get("health_restrictions"):
                profile["health_restrictions"] = profile["health_restrictions"].split(",")
            else:
                profile["health_restrictions"] = []

        return status_result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check onboarding status: {str(e)}"
        )


@router.post("/onboarding/complete")
async def complete_onboarding(
    onboarding_data: OnboardingData,
    current_user: Dict = Depends(get_current_patient)
):
    """
    Complete patient onboarding with health information

    Requirements: Patient authentication
    """
    try:
        user_id = current_user["db_user"]["id"]

        # Convert Pydantic model to dict
        data_dict = onboarding_data.model_dump()

        # Convert date to string
        data_dict["date_of_birth"] = data_dict["date_of_birth"].isoformat()

        # Convert health_goals HealthGoal objects to dict format
        if data_dict.get("health_goals"):
            data_dict["health_goals"] = [
                goal if isinstance(goal, dict) else goal.dict()
                for goal in data_dict["health_goals"]
            ]

        # Convert emergency contacts to dict format
        if data_dict.get("emergency_contacts"):
            data_dict["emergency_contacts"] = [
                contact if isinstance(contact, dict) else contact.dict()
                for contact in data_dict["emergency_contacts"]
            ]

        updated_profile = await patient_service.complete_onboarding(
            user_id=user_id,
            onboarding_data=data_dict
        )

        # health_goals is already JSONB array, no conversion needed
        # Ensure health_goals has default value if null
        if not updated_profile.get("health_goals"):
            updated_profile["health_goals"] = []

        # Convert comma-separated health_restrictions to array for response
        if updated_profile.get("health_restrictions"):
            updated_profile["health_restrictions"] = updated_profile["health_restrictions"].split(",")
        else:
            updated_profile["health_restrictions"] = []

        return {
            "message": "Onboarding completed successfully",
            "profile": updated_profile
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete onboarding: {str(e)}"
        )


@router.patch("/profile")
async def update_patient_profile(
    update_data: ProfileUpdateData,
    current_user: Dict = Depends(get_current_patient)
):
    """
    Update patient profile information

    Requirements: Patient authentication
    """
    try:
        user_id = current_user["db_user"]["id"]

        # Convert Pydantic model to dict and remove None values
        data_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}

        # Convert date to string if present
        if "date_of_birth" in data_dict:
            data_dict["date_of_birth"] = data_dict["date_of_birth"].isoformat()

        # Convert health_goals HealthGoal objects to dict format if present
        if "health_goals" in data_dict and data_dict["health_goals"]:
            data_dict["health_goals"] = [
                goal if isinstance(goal, dict) else goal.dict()
                for goal in data_dict["health_goals"]
            ]

        updated_profile = await patient_service.update_patient_profile(
            user_id=user_id,
            update_data=data_dict
        )

        # health_goals is already JSONB array, no conversion needed
        # Ensure health_goals has default value if null
        if not updated_profile.get("health_goals"):
            updated_profile["health_goals"] = []

        # Convert comma-separated health_restrictions to array for response
        if updated_profile.get("health_restrictions"):
            updated_profile["health_restrictions"] = updated_profile["health_restrictions"].split(",")
        else:
            updated_profile["health_restrictions"] = []

        return {
            "message": "Profile updated successfully",
            "profile": updated_profile
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile: {str(e)}"
        )


@router.post("/goals/complete")
async def mark_goal_complete(
    goal_text: str,
    goal_frequency: str,
    completion_date: Optional[str] = None,
    current_user: Dict = Depends(get_current_patient)
):
    """
    Mark a goal as completed for a specific date

    Requirements: Patient authentication
    """
    try:
        user_id = current_user["db_user"]["id"]

        # Use today if no date provided
        if not completion_date:
            from datetime import date
            completion_date = date.today().isoformat()

        result = await patient_service.mark_goal_complete(
            user_id=user_id,
            goal_text=goal_text,
            goal_frequency=goal_frequency,
            completion_date=completion_date
        )

        return {
            "message": "Goal marked as completed",
            "completion": result
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark goal complete: {str(e)}"
        )


@router.post("/goals/uncomplete")
async def unmark_goal_complete(
    goal_text: str,
    completion_date: Optional[str] = None,
    current_user: Dict = Depends(get_current_patient)
):
    """
    Unmark a goal completion

    Requirements: Patient authentication
    """
    try:
        user_id = current_user["db_user"]["id"]

        # Use today if no date provided
        if not completion_date:
            from datetime import date
            completion_date = date.today().isoformat()

        result = await patient_service.unmark_goal_complete(
            user_id=user_id,
            goal_text=goal_text,
            completion_date=completion_date
        )

        return {
            "message": "Goal unmarked",
            "completion": result
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unmark goal: {str(e)}"
        )


@router.get("/goals/completions")
async def get_goal_completions(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: Dict = Depends(get_current_patient)
):
    """
    Get goal completion history for date range

    Requirements: Patient authentication
    """
    try:
        user_id = current_user["db_user"]["id"]

        completions = await patient_service.get_goal_completions(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date
        )

        return {
            "completions": completions,
            "total": len(completions)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get goal completions: {str(e)}"
        )


@router.get("/goals/stats")
async def get_goal_stats(
    current_user: Dict = Depends(get_current_patient)
):
    """
    Get goal completion statistics

    Requirements: Patient authentication
    """
    try:
        user_id = current_user["db_user"]["id"]

        stats = await patient_service.get_goal_stats(user_id=user_id)

        return stats

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get goal stats: {str(e)}"
        )


@router.post("/goals/initialize")
async def initialize_daily_goals(
    current_user: Dict = Depends(get_current_patient)
):
    """
    Initialize today's goal tracking based on user's health goals

    Requirements: Patient authentication
    """
    try:
        user_id = current_user["db_user"]["id"]

        created = await patient_service.initialize_daily_goals(user_id=user_id)

        return {
            "message": "Daily goals initialized",
            "goals": created
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize daily goals: {str(e)}"
        )
