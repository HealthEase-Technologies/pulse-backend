from fastapi import APIRouter, Depends, HTTPException, status
from app.auth.dependencies import get_current_user_patient_or_provider
from app.services.device_service import device_service
from app.schemas.device import (
    DeviceTypeInfo,
    ConnectDeviceRequest,
    DeviceResponse,
    DeviceWithTypeInfo,
    DisconnectDeviceResponse,
    SimulateDeviceDataRequest,
    SimulateDeviceDataResponse
)
from typing import Dict, List, Any

router = APIRouter(prefix="/devices", tags=["devices"])


# ==================== DEVICE TYPE ENDPOINTS ====================

@router.get("/types", response_model=List[DeviceTypeInfo])
async def get_available_device_types(
    current_user: Dict = Depends(get_current_user_patient_or_provider)
):
    """
    Get all available device types that can be connected

    Returns list of supported devices with:
    - Display name and manufacturer
    - Supported biomarkers
    - Icon URL

    Requirements: Sprint 4 - Show available devices for connection

    TODO: Implement this endpoint
    - Call device_service.get_available_device_types()
    - Return list of device types
    """
    pass


# ==================== DEVICE CONNECTION ENDPOINTS ====================

@router.post("/connect", response_model=Dict[str, Any])
async def connect_device(
    request: ConnectDeviceRequest,
    current_user: Dict = Depends(get_current_user_patient_or_provider)
):
    """
    Connect a new device to user's account

    Business Rules:
    - User can only have ONE device of each type
    - If previously disconnected, will be reactivated

    Requirements: Sprint 4 - Connect Device API

    TODO: Implement this endpoint
    - Get user_id from current_user
    - Call device_service.connect_device()
    - Return success message with device details
    """
    pass


@router.delete("/{device_id}/disconnect", response_model=DisconnectDeviceResponse)
async def disconnect_device(
    device_id: str,
    current_user: Dict = Depends(get_current_user_patient_or_provider)
):
    """
    Disconnect a device from user's account

    Requirements: Sprint 4 - Disconnect Device API

    TODO: Implement this endpoint
    - Get user_id from current_user
    - Call device_service.disconnect_device()
    - Return success message with disconnection timestamp
    """
    pass


@router.get("/my-devices", response_model=List[DeviceWithTypeInfo])
async def get_my_devices(
    current_user: Dict = Depends(get_current_user_patient_or_provider)
):
    """
    Get all devices connected to current user's account

    Returns devices with full type information (manufacturer, icon, etc.)

    Requirements: Sprint 4 - Get Connected Devices API

    TODO: Implement this endpoint
    - Get user_id from current_user
    - Call device_service.get_user_devices() with status='connected'
    - Return list of connected devices
    """
    pass


@router.get("/{device_id}", response_model=DeviceWithTypeInfo)
async def get_device_details(
    device_id: str,
    current_user: Dict = Depends(get_current_user_patient_or_provider)
):
    """
    Get details of a specific device

    TODO: Implement this endpoint
    - Get user_id from current_user
    - Call device_service.get_device_by_id()
    - Return device details with type information
    """
    pass


# ==================== SIMULATION ENDPOINTS ====================

@router.post("/{device_id}/simulate-data", response_model=SimulateDeviceDataResponse)
async def simulate_device_data(
    device_id: str,
    request: SimulateDeviceDataRequest,
    current_user: Dict = Depends(get_current_user_patient_or_provider)
):
    """
    Manually trigger biomarker data simulation for a connected device

    This endpoint allows generating additional historical biomarker data
    for testing and demo purposes. Useful for:
    - Generating more historical data after initial connection
    - Testing dashboard charts with different time ranges
    - Populating data for demos

    Business Rules:
    - Device must be connected (status='connected')
    - Device must belong to current user
    - Generates realistic values within healthy ranges
    - Data is stored in 'biomarkers' table with source='device'

    Requirements: Sprint 4 - Device Data Simulation (Manual Trigger)

    TODO: Implement this endpoint
    - Get user_id from current_user
    - Verify device belongs to user and is connected
    - Get device_type from device record
    - Call biomarker_service.simulate_device_data(user_id, device_id, device_type, days_of_history)
    - Return simulation summary (total readings, biomarkers generated, date range)
    """
    pass
