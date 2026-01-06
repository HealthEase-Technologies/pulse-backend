from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.auth.dependencies import get_current_patient, get_current_provider
from app.services.biomarker_service import biomarker_service
from app.schemas.biomarker import (
    BiomarkerRangeResponse,
    InsertBiomarkerRequest,
    BiomarkerResponse,
    LatestBiomarkerReading,
    BiomarkerDashboardSummary
)
from typing import Dict, List, Any, Optional

router = APIRouter(prefix="/biomarkers", tags=["biomarkers"])


# ==================== REFERENCE DATA ENDPOINTS ====================

@router.get("/ranges", response_model=List[BiomarkerRangeResponse])
async def get_biomarker_ranges():
    """
    Get reference ranges for all biomarker types

    Returns normal/optimal/critical ranges for:
    - Heart Rate
    - Blood Pressure (systolic/diastolic)
    - Glucose
    - Steps
    - Sleep

    Public endpoint - no authentication required

    TODO: Implement this endpoint
    - Call biomarker_service.get_biomarker_ranges()
    - Return reference ranges
    """
    pass


# ==================== PATIENT BIOMARKER ENDPOINTS ====================

@router.post("/", response_model=Dict[str, Any])
async def insert_biomarker_data(
    request: InsertBiomarkerRequest,
    current_user: Dict = Depends(get_current_patient)
):
    """
    Insert new biomarker data (manual entry or device sync)

    Business Rules:
    - If source is 'device', device_id must be provided and belong to user
    - If source is 'manual', device_id should be None
    - recorded_at defaults to current time if not provided

    Requirements: Sprint 4 - Insert Biomarker Data API

    TODO: Implement this endpoint
    - Get user_id from current_user
    - Validate request data
    - Call biomarker_service.insert_biomarker_data()
    - Return success message with created biomarker record
    """
    pass


@router.get("/dashboard", response_model=BiomarkerDashboardSummary)
async def get_dashboard_summary(
    current_user: Dict = Depends(get_current_patient)
):
    """
    Get latest readings for all biomarker types (dashboard summary)

    Returns most recent value for each biomarker with health status

    Requirements: Sprint 4 - Get Latest Biomarker Readings API

    TODO: Implement this endpoint
    - Get user_id from current_user
    - Call biomarker_service.get_latest_biomarker_readings()
    - Return dashboard summary with latest readings and status
    """
    pass


@router.get("/history/{biomarker_type}", response_model=List[BiomarkerResponse])
async def get_biomarker_history(
    biomarker_type: str,
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    current_user: Dict = Depends(get_current_patient)
):
    """
    Get historical data for a specific biomarker type

    Supports pagination for large datasets

    TODO: Implement this endpoint
    - Get user_id from current_user
    - Validate biomarker_type
    - Call biomarker_service.get_biomarker_history()
    - Return paginated historical data
    """
    pass


@router.get("/all", response_model=List[BiomarkerResponse])
async def get_all_biomarkers(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    current_user: Dict = Depends(get_current_patient)
):
    """
    Get all biomarker data for current user (all types)

    Returns all biomarkers ordered by recorded_at DESC
    Supports pagination

    TODO: Implement this endpoint
    - Get user_id from current_user
    - Call biomarker_service.get_all_biomarkers()
    - Return paginated biomarker data
    """
    pass


# ==================== PROVIDER ENDPOINTS ====================

@router.get("/patient/{patient_user_id}/dashboard", response_model=BiomarkerDashboardSummary)
async def get_patient_dashboard_for_provider(
    patient_user_id: str,
    current_user: Dict = Depends(get_current_provider)
):
    """
    Provider gets latest biomarker readings for a connected patient

    Business Rule: Provider must have an accepted connection with the patient

    TODO: Implement this endpoint
    - Get provider_user_id from current_user
    - Call biomarker_service.get_patient_biomarkers_for_provider()
    - Return patient's latest biomarker readings
    """
    pass


@router.get("/patient/{patient_user_id}/history/{biomarker_type}", response_model=List[BiomarkerResponse])
async def get_patient_biomarker_history_for_provider(
    patient_user_id: str,
    biomarker_type: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: Dict = Depends(get_current_provider)
):
    """
    Provider gets historical biomarker data for a connected patient

    Business Rule: Provider must have an accepted connection with the patient

    TODO: Implement this endpoint
    - Verify provider has accepted connection with patient
    - Call biomarker_service.get_biomarker_history() with patient_user_id
    - Return patient's historical biomarker data
    """
    pass
