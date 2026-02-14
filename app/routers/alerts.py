from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.auth.dependencies import get_current_patient, get_current_provider
from app.services.alert_service import alert_service
from app.schemas.alert import (
    AlertHistoryResponse,
    AlertHistoryListResponse,
    UnacknowledgedCountResponse,
)
from typing import Dict, Optional

router = APIRouter(prefix="/alerts", tags=["alerts"])


# =============================================================================
# PATIENT ENDPOINTS
# =============================================================================

@router.get("/history", response_model=AlertHistoryListResponse)
async def get_alert_history(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    alert_type: Optional[str] = Query(None, description="Filter by alert type: warning or critical"),
    alert_status: Optional[str] = Query(None, alias="status", description="Filter by status"),
    current_user: Dict = Depends(get_current_patient),
):
    """Get patient's alert history with optional filters."""
    try:
        patient_user_id = current_user["db_user"]["id"]
        return await alert_service.get_alert_history(
            patient_user_id=patient_user_id,
            limit=limit,
            offset=offset,
            alert_type=alert_type,
            alert_status=alert_status,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch alert history: {str(e)}",
        )


@router.get("/unacknowledged-count", response_model=UnacknowledgedCountResponse)
async def get_unacknowledged_count(
    current_user: Dict = Depends(get_current_patient),
):
    """Get count of unacknowledged alerts (for badge/notification indicator)."""
    try:
        patient_user_id = current_user["db_user"]["id"]
        count = await alert_service.get_unacknowledged_count(patient_user_id)
        return {"count": count}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get unacknowledged count: {str(e)}",
        )


@router.patch("/{alert_id}/acknowledge", response_model=AlertHistoryResponse)
async def acknowledge_alert(
    alert_id: str,
    current_user: Dict = Depends(get_current_patient),
):
    """Patient acknowledges an alert."""
    try:
        patient_user_id = current_user["db_user"]["id"]
        return await alert_service.acknowledge_alert(alert_id, patient_user_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to acknowledge alert: {str(e)}",
        )


# =============================================================================
# PROVIDER ENDPOINTS
# =============================================================================

@router.get("/patient/{patient_user_id}/history", response_model=AlertHistoryListResponse)
async def get_patient_alert_history(
    patient_user_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: Dict = Depends(get_current_provider),
):
    """Provider gets patient's alert history."""
    try:
        provider_user_id = current_user["db_user"]["id"]
        return await alert_service.get_alert_history_for_provider(
            provider_user_id=provider_user_id,
            patient_user_id=patient_user_id,
            limit=limit,
            offset=offset,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch patient alert history: {str(e)}",
        )


@router.patch("/provider/{alert_id}/acknowledge", response_model=AlertHistoryResponse)
async def provider_acknowledge_alert(
    alert_id: str,
    current_user: Dict = Depends(get_current_provider),
):
    """Provider acknowledges a patient's alert."""
    try:
        provider_user_id = current_user["db_user"]["id"]
        return await alert_service.acknowledge_alert(alert_id, provider_user_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to acknowledge alert: {str(e)}",
        )
