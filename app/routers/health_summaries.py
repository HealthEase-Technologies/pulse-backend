from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.auth.dependencies import get_current_patient, get_current_provider
from app.services.health_summary_service import health_summary_service
from app.schemas.health_summary import (
    DailyHealthSummaryResponse,
    SummaryType
)
from typing import Dict, List, Any, Optional
from datetime import date

router = APIRouter(prefix="/health-summaries", tags=["health-summaries"])


# ==================== PATIENT ENDPOINTS ====================

@router.get("/today", response_model=Optional[DailyHealthSummaryResponse])
async def get_todays_summary(
    summary_type: Optional[SummaryType] = Query(None, description="Filter by summary type"),
    current_user: Dict = Depends(get_current_patient)
):
    """
    Get today's health summary for current patient

    Returns most recent summary (morning briefing or evening summary)

    TODO: Implement this endpoint
    - Get user_id from current_user
    - Get today's date
    - Call health_summary_service.get_user_summary(user_id, today, summary_type)
    - Return summary or null if not generated yet
    """
    pass


@router.get("/{summary_date}", response_model=Optional[DailyHealthSummaryResponse])
async def get_summary_by_date(
    summary_date: date,
    summary_type: Optional[SummaryType] = Query(None, description="Filter by summary type"),
    current_user: Dict = Depends(get_current_patient)
):
    """
    Get health summary for a specific date

    Args:
        summary_date: Date in YYYY-MM-DD format
        summary_type: Optional filter (morning_briefing or evening_summary)

    TODO: Implement this endpoint
    - Get user_id from current_user
    - Call health_summary_service.get_user_summary(user_id, summary_date, summary_type)
    - Return summary or null if doesn't exist
    """
    pass


@router.get("/range", response_model=List[DailyHealthSummaryResponse])
async def get_summaries_in_range(
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    summary_type: Optional[SummaryType] = Query(None, description="Filter by summary type"),
    current_user: Dict = Depends(get_current_patient)
):
    """
    Get health summaries for a date range

    Useful for viewing summary history over weeks/months

    TODO: Implement this endpoint
    - Get user_id from current_user
    - Validate start_date <= end_date
    - Call health_summary_service.get_user_summaries_range()
    - Return list of summaries ordered by date DESC
    """
    pass


@router.post("/{summary_date}/regenerate", response_model=DailyHealthSummaryResponse)
async def regenerate_summary(
    summary_date: date,
    summary_type: SummaryType,
    current_user: Dict = Depends(get_current_patient)
):
    """
    Manually regenerate health summary for a specific date

    Useful when:
    - Biomarker data was corrected/updated
    - Summary generation failed
    - Testing/debugging

    TODO: Implement this endpoint
    - Get user_id from current_user
    - Call health_summary_service.regenerate_summary(user_id, summary_date, summary_type)
    - Return newly generated summary
    """
    pass


# ==================== PROVIDER ENDPOINTS ====================

@router.get("/patient/{patient_user_id}/today", response_model=Optional[DailyHealthSummaryResponse])
async def get_patient_todays_summary(
    patient_user_id: str,
    summary_type: Optional[SummaryType] = Query(None),
    current_user: Dict = Depends(get_current_provider)
):
    """
    Provider gets today's health summary for a connected patient

    Business Rule: Provider must have accepted connection with patient

    TODO: Implement this endpoint
    - Get provider_user_id from current_user
    - Verify provider has accepted connection with patient
    - Get today's date
    - Call health_summary_service.get_user_summary(patient_user_id, today, summary_type)
    - Return summary
    """
    pass


@router.get("/patient/{patient_user_id}/{summary_date}", response_model=Optional[DailyHealthSummaryResponse])
async def get_patient_summary_by_date(
    patient_user_id: str,
    summary_date: date,
    summary_type: Optional[SummaryType] = Query(None),
    current_user: Dict = Depends(get_current_provider)
):
    """
    Provider gets health summary for a connected patient on specific date

    Business Rule: Provider must have accepted connection with patient

    TODO: Implement this endpoint
    - Get provider_user_id from current_user
    - Verify provider has accepted connection with patient
    - Call health_summary_service.get_user_summary(patient_user_id, summary_date, summary_type)
    - Return summary
    """
    pass


@router.get("/patient/{patient_user_id}/range", response_model=List[DailyHealthSummaryResponse])
async def get_patient_summaries_in_range(
    patient_user_id: str,
    start_date: date = Query(...),
    end_date: date = Query(...),
    summary_type: Optional[SummaryType] = Query(None),
    current_user: Dict = Depends(get_current_provider)
):
    """
    Provider gets health summaries for a connected patient over a date range

    Business Rule: Provider must have accepted connection with patient

    TODO: Implement this endpoint
    - Get provider_user_id from current_user
    - Verify provider has accepted connection with patient
    - Validate date range
    - Call health_summary_service.get_user_summaries_range(patient_user_id, start_date, end_date, summary_type)
    - Return list of summaries
    """
    pass
