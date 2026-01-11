from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class NoteCreate(BaseModel):
    """Schema for creating a new HCP note"""
    patient_id: str
    content: str


class NoteUpdate(BaseModel):
    """Schema for updating an existing HCP note (provider only)"""
    content: str


class MarkNoteAsReadRequest(BaseModel):
    """Schema for patient marking a note as read"""
    is_read: bool = True


class ProviderInfo(BaseModel):
    """Schema for provider information in note responses"""
    id: str
    full_name: str


class PatientInfo(BaseModel):
    """Schema for patient information in note responses"""
    id: str
    full_name: str


class NoteResponse(BaseModel):
    """Schema for HCP note response"""
    id: str
    patient_id: str
    content: str
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    provider: Optional[ProviderInfo] = None
    patient: Optional[PatientInfo] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "patient_id": "123e4567-e89b-12d3-a456-426614174001",
                "content": "Patient showing good progress with medication adherence. Blood pressure readings have stabilized.",
                "is_read": False,
                "read_at": None,
                "created_at": "2026-01-09T10:30:00Z",
                "updated_at": "2026-01-09T10:30:00Z",
                "provider": {
                    "id": "123e4567-e89b-12d3-a456-426614174002",
                    "full_name": "Dr. Sarah Johnson"
                },
                "patient": {
                    "id": "123e4567-e89b-12d3-a456-426614174001",
                    "full_name": "John Doe"
                }
            }
        }
