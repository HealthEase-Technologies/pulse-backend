from fastapi import APIRouter, Depends, HTTPException, status
from app.auth.dependencies import get_current_patient, get_current_provider
from app.services.threshold_service import threshold_service
from app.schemas.threshold import (
    ThresholdCreate,
    ThresholdResponse,
    EffectiveThreshold,
)
from typing import Dict, List

router = APIRouter(prefix="/thresholds", tags=["thresholds"])


# =============================================================================
# PATIENT ENDPOINTS
# =============================================================================

@router.get("/my-thresholds", response_model=List[ThresholdResponse])
async def get_my_thresholds(
    current_user: Dict = Depends(get_current_patient),
):
    """Get all custom thresholds set for the current patient (by self or provider)."""
    try:
        patient_user_id = current_user["db_user"]["id"]
        return await threshold_service.get_patient_thresholds(patient_user_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch thresholds: {str(e)}",
        )


@router.get("/effective", response_model=List[EffectiveThreshold])
async def get_effective_thresholds(
    current_user: Dict = Depends(get_current_patient),
):
    """Get resolved effective thresholds (after hierarchy resolution) for all biomarker types."""
    try:
        patient_user_id = current_user["db_user"]["id"]
        return await threshold_service.get_effective_thresholds(patient_user_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch effective thresholds: {str(e)}",
        )


@router.post("/", response_model=ThresholdResponse)
async def set_patient_threshold(
    request: ThresholdCreate,
    current_user: Dict = Depends(get_current_patient),
):
    """Patient sets/updates their own custom threshold for a biomarker type."""
    try:
        patient_user_id = current_user["db_user"]["id"]
        return await threshold_service.upsert_patient_threshold(
            patient_user_id=patient_user_id,
            data=request.model_dump(),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set threshold: {str(e)}",
        )


@router.delete("/{threshold_id}")
async def delete_threshold(
    threshold_id: str,
    current_user: Dict = Depends(get_current_patient),
):
    """Patient deletes their own custom threshold."""
    try:
        patient_user_id = current_user["db_user"]["id"]
        await threshold_service.delete_threshold(threshold_id, patient_user_id)
        return {"message": "Threshold deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete threshold: {str(e)}",
        )


# =============================================================================
# PROVIDER ENDPOINTS
# =============================================================================

@router.post("/patient/{patient_user_id}", response_model=ThresholdResponse)
async def set_provider_threshold(
    patient_user_id: str,
    request: ThresholdCreate,
    current_user: Dict = Depends(get_current_provider),
):
    """Provider sets/updates custom threshold for a connected patient."""
    try:
        provider_user_id = current_user["db_user"]["id"]
        return await threshold_service.upsert_provider_threshold(
            provider_user_id=provider_user_id,
            patient_user_id=patient_user_id,
            data=request.model_dump(),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set threshold: {str(e)}",
        )


@router.get("/patient/{patient_user_id}", response_model=List[ThresholdResponse])
async def get_patient_thresholds_for_provider(
    patient_user_id: str,
    current_user: Dict = Depends(get_current_provider),
):
    """Provider gets all custom thresholds for a connected patient."""
    try:
        return await threshold_service.get_patient_thresholds(patient_user_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch patient thresholds: {str(e)}",
        )


@router.get("/patient/{patient_user_id}/effective", response_model=List[EffectiveThreshold])
async def get_patient_effective_thresholds(
    patient_user_id: str,
    current_user: Dict = Depends(get_current_provider),
):
    """Provider gets resolved effective thresholds for a connected patient."""
    try:
        return await threshold_service.get_effective_thresholds(patient_user_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch effective thresholds: {str(e)}",
        )


@router.delete("/provider/{threshold_id}")
async def delete_provider_threshold(
    threshold_id: str,
    current_user: Dict = Depends(get_current_provider),
):
    """Provider deletes their own threshold for a patient."""
    try:
        provider_user_id = current_user["db_user"]["id"]
        await threshold_service.delete_threshold(threshold_id, provider_user_id)
        return {"message": "Threshold deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete threshold: {str(e)}",
        )
