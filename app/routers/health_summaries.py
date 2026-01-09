from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.auth.dependencies import get_current_patient, get_current_provider
from app.services.health_summary_service import health_summary_service
from app.schemas.health_summary import (
    DailyHealthSummaryResponse,
    SummaryType
)
from typing import Dict, List, Optional
from datetime import date

router = APIRouter(prefix="/health-summaries", tags=["health-summaries"])


#PATIENT ENDPOINTS

@router.get("/today", response_model=Optional[DailyHealthSummaryResponse])
async def get_todays_summary(
    summary_type: Optional[SummaryType] = Query(None, description="Filter by summary type"),
    current_user: Dict = Depends(get_current_patient)
):
    user_id = current_user["db_user"]["id"]
    today = date.today()

    summary = await health_summary_service.get_user_summary(
        user_id=user_id,
        summary_date=today,
        summary_type=summary_type
    )

    return summary


@router.get("/range", response_model=List[DailyHealthSummaryResponse])
async def get_summaries_in_range(
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    summary_type: Optional[SummaryType] = Query(None, description="Filter by summary type"),
    current_user: Dict = Depends(get_current_patient)
):
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before or equal to end_date"
        )

    user_id = current_user["db_user"]["id"]

    summaries = await health_summary_service.get_user_summaries_range(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        summary_type=summary_type
    )

    return summaries


@router.get("/{summary_date}", response_model=Optional[DailyHealthSummaryResponse])
async def get_summary_by_date(
    summary_date: date,
    summary_type: Optional[SummaryType] = Query(None, description="Filter by summary type"),
    current_user: Dict = Depends(get_current_patient)
):
    user_id = current_user["db_user"]["id"]

    summary = await health_summary_service.get_user_summary(
        user_id=user_id,
        summary_date=summary_date,
        summary_type=summary_type
    )

    return summary


@router.post("/{summary_date}/regenerate", response_model=DailyHealthSummaryResponse)
async def regenerate_summary(
    summary_date: date,
    summary_type: SummaryType,
    current_user: Dict = Depends(get_current_patient)
):
    user_id = current_user["db_user"]["id"]

    summary = await health_summary_service.regenerate_summary(
        user_id=user_id,
        target_date=summary_date,
        summary_type=summary_type
    )

    return summary


# PROVIDER ENDPOINTS

@router.get("/patient/{patient_user_id}/today", response_model=Optional[DailyHealthSummaryResponse])
async def get_patient_todays_summary(
    patient_user_id: str,
    summary_type: Optional[SummaryType] = Query(None),
    current_user: Dict = Depends(get_current_provider)
):
    provider_user_id = current_user["db_user"]["id"]
    today = date.today()

    summary = await health_summary_service.get_patient_summary_for_provider(
        provider_user_id=provider_user_id,
        patient_user_id=patient_user_id,
        summary_date=today,
        summary_type=summary_type
    )

    return summary


@router.get("/patient/{patient_user_id}/{summary_date}", response_model=Optional[DailyHealthSummaryResponse])
async def get_patient_summary_by_date(
    patient_user_id: str,
    summary_date: date,
    summary_type: Optional[SummaryType] = Query(None),
    current_user: Dict = Depends(get_current_provider)
):
    provider_user_id = current_user["db_user"]["id"]

    summary = await health_summary_service.get_patient_summary_for_provider(
        provider_user_id=provider_user_id,
        patient_user_id=patient_user_id,
        summary_date=summary_date,
        summary_type=summary_type
    )

    return summary


@router.get("/patient/{patient_user_id}/range", response_model=List[DailyHealthSummaryResponse])
async def get_patient_summaries_in_range(
    patient_user_id: str,
    start_date: date = Query(...),
    end_date: date = Query(...),
    summary_type: Optional[SummaryType] = Query(None),
    current_user: Dict = Depends(get_current_provider)
):
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before or equal to end_date"
        )

    provider_user_id = current_user["db_user"]["id"]

    summaries = await health_summary_service.get_patient_summaries_range_for_provider(
        provider_user_id=provider_user_id,
        patient_user_id=patient_user_id,
        start_date=start_date,
        end_date=end_date,
        summary_type=summary_type
    )

    return summaries
#for commiting