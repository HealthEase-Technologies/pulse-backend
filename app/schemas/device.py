from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class DeviceType(str, Enum):
    """Supported device types"""
    APPLE_WATCH = "apple_watch"
    FITBIT = "fitbit"
    WHOOP = "whoop"
    OMRON_BP = "omron_bp"
    FREESTYLE_LIBRE = "freestyle_libre"


class DeviceStatus(str, Enum):
    """Device connection status"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"


class DeviceTypeInfo(BaseModel):
    """Device type information from reference table"""
    id: str
    device_type: str
    display_name: str
    manufacturer: str
    supported_biomarkers: List[str]
    description: Optional[str] = None
    icon_url: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "device_type": "apple_watch",
                "display_name": "Apple Watch",
                "manufacturer": "Apple",
                "supported_biomarkers": ["heart_rate", "steps", "sleep"],
                "description": "Comprehensive health and fitness tracking",
                "icon_url": "https://pulse-so-public-assets.s3.me-central-1.amazonaws.com/device-icons/apple_watch.jpg",
                "is_active": True,
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T10:00:00Z"
            }
        }


class ConnectDeviceRequest(BaseModel):
    """Request to connect a new device"""
    device_type: DeviceType = Field(..., description="Type of device to connect")
    device_name: Optional[str] = Field(None, description="Custom name for the device (e.g., 'My Apple Watch')")

    class Config:
        json_schema_extra = {
            "example": {
                "device_type": "apple_watch",
                "device_name": "My Apple Watch"
            }
        }


class DeviceResponse(BaseModel):
    """Device response schema"""
    id: str
    user_id: str
    device_type: str
    device_name: Optional[str] = None
    status: DeviceStatus
    connected_at: datetime
    disconnected_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "123e4567-e89b-12d3-a456-426614174001",
                "device_type": "apple_watch",
                "device_name": "My Apple Watch",
                "status": "connected",
                "connected_at": "2024-01-15T10:00:00Z",
                "disconnected_at": None,
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T10:00:00Z"
            }
        }


class DeviceWithTypeInfo(DeviceResponse):
    """Device response with type information"""
    display_name: str
    manufacturer: str
    supported_biomarkers: List[str]
    icon_url: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "123e4567-e89b-12d3-a456-426614174001",
                "device_type": "apple_watch",
                "device_name": "My Apple Watch",
                "status": "connected",
                "connected_at": "2024-01-15T10:00:00Z",
                "disconnected_at": None,
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T10:00:00Z",
                "display_name": "Apple Watch",
                "manufacturer": "Apple",
                "supported_biomarkers": ["heart_rate", "steps", "sleep"],
                "icon_url": "https://pulse-so-public-assets.s3.me-central-1.amazonaws.com/device-icons/apple_watch.jpg"
            }
        }


class DisconnectDeviceResponse(BaseModel):
    """Response after disconnecting a device"""
    message: str
    device_id: str
    disconnected_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Device disconnected successfully",
                "device_id": "123e4567-e89b-12d3-a456-426614174000",
                "disconnected_at": "2024-01-15T10:00:00Z"
            }
        }


class SimulateDeviceDataRequest(BaseModel):
    """Request to manually simulate biomarker data for a device"""
    days_of_history: int = Field(
        default=7,
        ge=1,
        le=90,
        description="Number of days of historical data to generate (1-90 days)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "days_of_history": 14
            }
        }


class SimulateDeviceDataResponse(BaseModel):
    """Response after simulating device data"""
    message: str
    device_id: str
    device_type: str
    total_readings: int
    biomarkers_generated: List[str]
    date_range: dict

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Device data simulated successfully",
                "device_id": "123e4567-e89b-12d3-a456-426614174000",
                "device_type": "apple_watch",
                "total_readings": 42,
                "biomarkers_generated": ["heart_rate", "steps", "sleep"],
                "date_range": {
                    "start": "2024-01-01T00:00:00Z",
                    "end": "2024-01-14T23:59:59Z"
                }
            }
        }
