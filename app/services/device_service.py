from app.config.database import supabase_admin
from fastapi import HTTPException, status
from typing import Dict, Optional, List
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class DeviceService:
    """Service layer for device management"""

    @staticmethod
    async def get_available_device_types() -> List[Dict]:
        """
        Get all available device types that users can connect

        Returns:
            List of device types with metadata (display_name, manufacturer, supported_biomarkers, icon_url)

        TODO: Implement this function
        - Query device_types table
        - Filter by is_active = true
        - Return list of available devices
        """
        pass

    @staticmethod
    async def connect_device(user_id: str, device_type: str, device_name: Optional[str] = None) -> Dict:
        """
        Connect a new device for a user

        Business Rules:
        - User can only have ONE device of each type
        - Device type must exist in device_types table
        - If device was previously connected and disconnected, reactivate it
        - Auto-generates 7 days (1 week) of initial biomarker data for demo purposes

        Data Flow:
        1. Validate and connect device → stored in 'devices' table
        2. Auto-generate initial biomarker data → stored in 'biomarkers' table via simulate_device_data()

        Args:
            user_id: The user's ID
            device_type: Type of device (apple_watch, fitbit, etc.)
            device_name: Optional custom name for the device

        Returns:
            Device record with simulation summary

        TODO: Implement this function
        - Validate device_type exists in device_types table
        - Check if user already has this device type
        - If exists and disconnected, reactivate it
        - If exists and connected, raise error
        - If doesn't exist, create new device record
        - IMPORTANT: Call biomarker_service.simulate_device_data(user_id, device_id, device_type, days_of_history=7)
        - Return device with type information + simulation summary
        """
        pass

    @staticmethod
    async def disconnect_device(device_id: str, user_id: str) -> Dict:
        """
        Disconnect a device

        Args:
            device_id: The device ID to disconnect
            user_id: The user's ID (for authorization)

        Returns:
            Updated device record

        TODO: Implement this function
        - Verify device belongs to user
        - Verify device is currently connected
        - Update status to 'disconnected'
        - Set disconnected_at timestamp
        - Return updated device record
        """
        pass

    @staticmethod
    async def get_user_devices(user_id: str, status: Optional[str] = None) -> List[Dict]:
        """
        Get all devices for a user

        Args:
            user_id: The user's ID
            status: Optional filter by status (connected/disconnected)

        Returns:
            List of user's devices with type information

        TODO: Implement this function
        - Query devices table for user
        - Filter by status if provided
        - Join with device_types to get display info
        - Return enriched device list
        """
        pass

    @staticmethod
    async def get_device_by_id(device_id: str, user_id: str) -> Dict:
        """
        Get a specific device by ID

        Args:
            device_id: The device ID
            user_id: The user's ID (for authorization)

        Returns:
            Device record with type information

        TODO: Implement this function
        - Verify device belongs to user
        - Get device details
        - Join with device_types for display info
        - Return enriched device record
        """
        pass


# Create singleton instance
device_service = DeviceService()
