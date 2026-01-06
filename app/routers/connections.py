from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.auth.dependencies import get_current_patient, get_current_provider
from app.services.connection_service import connection_service
from typing import Dict, List, Optional, Any

router = APIRouter(prefix="/connections", tags=["connections"])


# ==================== PATIENT ENDPOINTS ====================

@router.post("/request", response_model=Dict[str, Any])
async def request_connection(
    provider_user_id: str,
    current_user: Dict = Depends(get_current_patient)
):
    """
    Patient sends connection request to a provider

    Business Rule: Patient can only have ONE accepted connection at a time

    Requirements: Sprint 3 - Patient sends connection request to provider
    """
    try:
        patient_user_id = current_user["db_user"]["id"]

        connection = await connection_service.request_connection(
            patient_user_id=patient_user_id,
            provider_user_id=provider_user_id
        )

        return {
            "message": "Connection request sent successfully",
            "connection": connection
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to request connection: {str(e)}"
        )


@router.get("/my-connections", response_model=Dict[str, Any])
async def get_my_connections(
    connection_status: Optional[str] = Query(None, description="Filter by status (pending/accepted/rejected)"),
    current_user: Dict = Depends(get_current_patient)
):
    """
    Get all patient's connections with providers

    Query params:
    - connection_status: Filter by 'pending', 'accepted', or 'rejected'

    Requirements: Sprint 3 - Patient views their connections
    """
    try:
        patient_user_id = current_user["db_user"]["id"]

        connections = await connection_service.get_patient_connections(
            patient_user_id=patient_user_id,
            connection_status=connection_status
        )

        return {
            "total": len(connections),
            "connections": connections
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get connections: {str(e)}"
        )


@router.delete("/{connection_id}", response_model=Dict[str, Any])
async def disconnect_from_provider(
    connection_id: str,
    current_user: Dict = Depends(get_current_patient)
):
    """
    Patient disconnects from their current provider

    Requirements: Sprint 3 - Patient can disconnect from provider
    """
    try:
        patient_user_id = current_user["db_user"]["id"]

        connection = await connection_service.disconnect_from_provider(
            connection_id=connection_id,
            patient_user_id=patient_user_id
        )

        return {
            "message": "Successfully disconnected from provider",
            "connection": connection
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disconnect: {str(e)}"
        )


# ==================== PROVIDER ENDPOINTS ====================

@router.get("/requests", response_model=Dict[str, Any])
async def get_connection_requests(
    connection_status: Optional[str] = Query(None, description="Filter by status (pending/accepted/rejected)"),
    current_user: Dict = Depends(get_current_provider)
):
    """
    Get all connection requests for provider

    Query params:
    - connection_status: Filter by 'pending', 'accepted', or 'rejected'

    Requirements: Sprint 3 - Provider views connection requests
    """
    try:
        provider_user_id = current_user["db_user"]["id"]

        requests = await connection_service.get_provider_requests(
            provider_user_id=provider_user_id,
            connection_status=connection_status
        )

        return {
            "total": len(requests),
            "requests": requests
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get connection requests: {str(e)}"
        )


@router.patch("/{connection_id}/accept", response_model=Dict[str, Any])
async def accept_connection_request(
    connection_id: str,
    current_user: Dict = Depends(get_current_provider)
):
    """
    Provider accepts a connection request

    Business Rule: Double-checks patient doesn't have another accepted connection

    Requirements: Sprint 3 - Provider approves/rejects connection request
    """
    try:
        provider_user_id = current_user["db_user"]["id"]

        connection = await connection_service.accept_connection(
            connection_id=connection_id,
            provider_user_id=provider_user_id
        )

        return {
            "message": "Connection accepted successfully",
            "connection": connection
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to accept connection: {str(e)}"
        )


@router.patch("/{connection_id}/reject", response_model=Dict[str, Any])
async def reject_connection_request(
    connection_id: str,
    current_user: Dict = Depends(get_current_provider)
):
    """
    Provider rejects a connection request

    Requirements: Sprint 3 - Provider approves/rejects connection request
    """
    try:
        provider_user_id = current_user["db_user"]["id"]

        connection = await connection_service.reject_connection(
            connection_id=connection_id,
            provider_user_id=provider_user_id
        )

        return {
            "message": "Connection rejected successfully",
            "connection": connection
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reject connection: {str(e)}"
        )


@router.get("/connected-patients", response_model=Dict[str, Any])
async def get_connected_patients(
    current_user: Dict = Depends(get_current_provider)
):
    """
    Get all patients connected to this provider (accepted status only)

    Requirements: Sprint 3 - Provider views list of connected patients
    """
    try:
        provider_user_id = current_user["db_user"]["id"]

        patients = await connection_service.get_connected_patients(
            provider_user_id=provider_user_id
        )

        return {
            "total": len(patients),
            "patients": patients
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get connected patients: {str(e)}"
        )
