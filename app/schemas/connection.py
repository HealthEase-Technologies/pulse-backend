from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class ConnectionStatus(str, Enum):
    """Patient-Provider connection status"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    DISCONNECTED = "disconnected"


class PatientProviderConnectionCreate(BaseModel):
    """Create patient-provider connection request"""
    provider_id: str = Field(..., description="Provider's user ID")

    class Config:
        json_schema_extra = {
            "example": {
                "provider_id": "123e4567-e89b-12d3-a456-426614174001"
            }
        }


class PatientProviderConnectionResponse(BaseModel):
    """Patient-Provider connection response schema"""
    id: str
    patient_id: str
    provider_id: str
    status: ConnectionStatus
    requested_at: datetime
    accepted_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    disconnected_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "patient_id": "123e4567-e89b-12d3-a456-426614174001",
                "provider_id": "123e4567-e89b-12d3-a456-426614174002",
                "status": "pending",
                "requested_at": "2024-01-15T10:00:00Z",
                "accepted_at": None,
                "rejected_at": None,
                "disconnected_at": None,
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T10:00:00Z"
            }
        }


class PatientProviderConnectionWithDetails(BaseModel):
    """Connection response with patient and provider details"""
    id: str
    patient_id: str
    patient_name: str
    patient_email: str
    provider_id: str
    provider_name: str
    provider_email: str
    status: ConnectionStatus
    requested_at: datetime
    accepted_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    disconnected_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "patient_id": "123e4567-e89b-12d3-a456-426614174001",
                "patient_name": "John Doe",
                "patient_email": "john@example.com",
                "provider_id": "123e4567-e89b-12d3-a456-426614174002",
                "provider_name": "Dr. Jane Smith",
                "provider_email": "dr.smith@example.com",
                "status": "accepted",
                "requested_at": "2024-01-15T10:00:00Z",
                "accepted_at": "2024-01-15T14:30:00Z",
                "rejected_at": None,
                "disconnected_at": None,
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T14:30:00Z"
            }
        }


class UpdateConnectionStatusRequest(BaseModel):
    """Request to update connection status (accept/reject)"""
    status: ConnectionStatus = Field(
        ...,
        description="New status (accepted/rejected)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "status": "accepted"
            }
        }


class ConnectionStatusResponse(BaseModel):
    """Response after updating connection status"""
    message: str
    connection: PatientProviderConnectionResponse

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Connection accepted successfully",
                "connection": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "patient_id": "123e4567-e89b-12d3-a456-426614174001",
                    "provider_id": "123e4567-e89b-12d3-a456-426614174002",
                    "status": "accepted",
                    "requested_at": "2024-01-15T10:00:00Z",
                    "accepted_at": "2024-01-15T14:30:00Z",
                    "rejected_at": None,
                    "disconnected_at": None,
                    "created_at": "2024-01-15T10:00:00Z",
                    "updated_at": "2024-01-15T14:30:00Z"
                }
            }
        }


class DisconnectProviderResponse(BaseModel):
    """Response after disconnecting from provider"""
    message: str
    disconnected_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Successfully disconnected from provider",
                "disconnected_at": "2024-01-20T10:00:00Z"
            }
        }
