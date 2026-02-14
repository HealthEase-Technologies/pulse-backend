from app.config.database import supabase_admin
from fastapi import HTTPException, status
from typing import Dict, Optional, List
from datetime import datetime, timezone
from app.services.biomarker_service import biomarker_service
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
        try:
            response = supabase_admin.table("device_types").select("*").eq("is_active", True).execute()
            return response.data

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch device types: {str(e)}"
            )

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
        try:
            type_response = supabase_admin.table("device_types").select("*").eq("device_type", device_type).eq("is_active",True).execute()
            if not type_response.data or len(type_response.data) == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid device type"
                )
            device_type_info = type_response.data[0]
            device_response = supabase_admin.table("devices").select("*").eq("user_id", user_id).eq("device_type", device_type).execute()
            now = datetime.now(timezone.utc)
            # if device exists
            if device_response.data and len(device_response.data) > 0:
                device = device_response.data[0]
                if device["status"] == "connected":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Device of this type is already connected"
                    )
                else:
                    # reactivate device
                    update_data = {
                        "status": "connected",
                        "connected_at": now.isoformat(),
                        "disconnected_at": None,
                        "updated_at": now.isoformat()
                    }
                    if device_name:
                        update_data["device_name"] = device_name
                    update_response = supabase_admin.table("devices").update(update_data).eq("id", device["id"]).execute()
                    device= update_response.data[0]
            # create new device
            else :
                insert_response = (
                supabase_admin
                .table("devices")
                .insert({
                    "user_id": user_id,
                    "device_type": device_type,
                    "device_name": device_name if device_name else device_type_info["display_name"],
                    "status": "connected",
                    "connected_at": now.isoformat(),
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat()
                })
                .execute()
                )
                device = insert_response.data[0]

            simulation_summary = await biomarker_service.simulate_device_data(
            user_id=user_id,
            device_id=device["id"],
            device_type=device_type,
            days_of_history=7
        )
            return {
                "device": {
                    **device,
                    "display_name": device_type_info["display_name"],
                    "manufacturer": device_type_info["manufacturer"],
                    "supported_biomarkers": device_type_info["supported_biomarkers"],
                    "icon_url": device_type_info.get("icon_url")
                },
                "simulation": simulation_summary
                    
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error connecting device: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to connect device"
            )


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
        try:
            device_response = supabase_admin.table("devices").select("*").eq("id", device_id).eq("user_id", user_id).execute()
            if not device_response.data or len(device_response.data) == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Device not found"
                )
            device = device_response.data[0]
            if device["status"] != "connected":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Device is not currently connected"
                )
            now = datetime.now(timezone.utc)
            update_response = supabase_admin.table("devices").update({
                "status": "disconnected",
                "disconnected_at": now.isoformat(),
                "updated_at": now.isoformat()
            }).eq("id", device_id).execute()

            # returns formatted response
            updated = update_response.data[0]
            return {
                "message": "Device disconnected successfully",
                "device_id": updated["id"],
                "disconnected_at": updated.get("disconnected_at", now.isoformat())
            }
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error disconnecting device: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to disconnect device"
            )

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
        try:
            query = supabase_admin.table("devices").select("*").eq("user_id", user_id)
            if status:
                query = query.eq("status", status)
            response = query.execute()
            devices = response.data
            # Enrich with device type info
            for device in devices:
                type_response = supabase_admin.table("device_types").select("*").eq("device_type", device["device_type"]).execute()
                if type_response.data and len(type_response.data) > 0:
                    device_type_info = type_response.data[0]
                    device.update({
                        "display_name": device_type_info["display_name"],
                        "manufacturer": device_type_info["manufacturer"],
                        "supported_biomarkers": device_type_info["supported_biomarkers"],
                        "icon_url": device_type_info.get("icon_url")
                    })
            return devices
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching user devices: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch user devices"
            )

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
        try:
            device_response = supabase_admin.table("devices").select("*").eq("id", device_id).eq("user_id", user_id).execute()
            if not device_response.data or len(device_response.data) == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Device not found"
                )
            device = device_response.data[0]
            type_response = supabase_admin.table("device_types").select("*").eq("device_type", device["device_type"]).execute()
            if type_response.data and len(type_response.data) > 0:
                device_type_info = type_response.data[0]
                device.update({
                    "display_name": device_type_info["display_name"],
                    "manufacturer": device_type_info["manufacturer"],
                    "supported_biomarkers": device_type_info["supported_biomarkers"],
                    "icon_url": device_type_info.get("icon_url")
                })
            return device
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching device details: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch device details"
            )


# Create singleton instance
device_service = DeviceService()
