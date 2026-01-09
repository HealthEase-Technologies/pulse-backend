from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.auth.dependencies import get_current_provider, get_current_patient
from app.services.note_service import note_service
from app.schemas.note import (
    NoteCreate,
    NoteUpdate,
    NoteResponse,
    MarkNoteAsReadRequest
)
from typing import Dict, List

router = APIRouter(prefix="/notes", tags=["notes"])


# ==================== PATIENT ENDPOINTS ====================

@router.get("/my-notes", response_model=List[NoteResponse])
async def get_my_notes(
    limit: int = Query(50, ge=1, le=100, description="Maximum number of notes"),
    offset: int = Query(0, ge=0, description="Number of notes to skip"),
    current_user: Dict = Depends(get_current_patient)
):
    """
    Get all notes written about the current patient by their healthcare provider

    Business Rules:
    - Patient can only view notes about themselves
    - Shows notes from their connected provider
    - Notes are ordered by created_at DESC (most recent first)

    Requirements: Sprint 5.3 - Patient View Notes API

    TODO: Implement this endpoint
    - Get patient_user_id from current_user
    - Call note_service.get_my_notes()
    - Return list of notes
    """
    pass


@router.patch("/{note_id}/mark-read", response_model=NoteResponse)
async def mark_note_as_read(
    note_id: str,
    current_user: Dict = Depends(get_current_patient)
):
    """
    Mark a note as read by the patient

    Business Rules:
    - Patient can only mark their own notes as read
    - Sets is_read to True and records read_at timestamp
    - Can be toggled back to unread if needed

    Requirements: Sprint 5.3 - Mark Note As Read API

    TODO: Implement this endpoint
    - Get patient_user_id from current_user
    - Call note_service.mark_note_as_read()
    - Return updated note
    """
    pass


# ==================== HCP NOTES ENDPOINTS ====================

@router.get("/", response_model=List[NoteResponse])
async def get_all_my_notes(
    limit: int = Query(50, ge=1, le=100, description="Maximum number of notes"),
    offset: int = Query(0, ge=0, description="Number of notes to skip"),
    current_user: Dict = Depends(get_current_provider)
):
    """
    Get all notes created by the current provider (across all patients)

    Business Rules:
    - Provider can view all notes they created
    - Notes are ordered by created_at DESC (most recent first)
    - Supports pagination

    Requirements: Sprint 5.3 - Get All Provider Notes API

    TODO: Implement this endpoint
    - Get provider_user_id from current_user
    - Call note_service.get_all_provider_notes()
    - Return list of all notes by this provider
    """
    pass


@router.post("/", response_model=NoteResponse)
async def create_note(
    request: NoteCreate,
    current_user: Dict = Depends(get_current_provider)
):
    """
    Create a new note for a patient

    Business Rules:
    - Only providers can create notes
    - Provider must have an accepted connection with the patient
    - Content cannot be empty

    Requirements: Sprint 5.3 - Add Note API

    TODO: Implement this endpoint
    - Get provider_user_id from current_user
    - Validate patient_id exists
    - Call note_service.create_note()
    - Return created note
    """
    pass


@router.get("/patient/{patient_user_id}", response_model=List[NoteResponse])
async def get_patient_notes(
    patient_user_id: str,
    limit: int = Query(50, ge=1, le=100, description="Maximum number of notes"),
    offset: int = Query(0, ge=0, description="Number of notes to skip"),
    current_user: Dict = Depends(get_current_provider)
):
    """
    Get all notes for a specific patient

    Business Rules:
    - Only providers can view notes
    - Provider must have an accepted connection with the patient
    - Notes are ordered by created_at DESC (most recent first)

    Requirements: Sprint 5.3 - Get Patient Notes API

    TODO: Implement this endpoint
    - Get provider_user_id from current_user
    - Call note_service.get_patient_notes()
    - Return list of notes
    """
    pass


@router.get("/{note_id}", response_model=NoteResponse)
async def get_note(
    note_id: str,
    current_user: Dict = Depends(get_current_provider)
):
    """
    Get a specific note by ID

    Business Rules:
    - Provider can only view notes they created

    TODO: Implement this endpoint
    - Get provider_user_id from current_user
    - Call note_service.get_note_by_id()
    - Return note
    """
    pass


@router.put("/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: str,
    request: NoteUpdate,
    current_user: Dict = Depends(get_current_provider)
):
    """
    Update an existing note

    Business Rules:
    - Provider can only update notes they created
    - Content cannot be empty

    Requirements: Sprint 5.3 - Update Note API

    TODO: Implement this endpoint
    - Get provider_user_id from current_user
    - Call note_service.update_note()
    - Return updated note
    """
    pass


@router.delete("/{note_id}")
async def delete_note(
    note_id: str,
    current_user: Dict = Depends(get_current_provider)
):
    """
    Delete a note

    Business Rules:
    - Provider can only delete notes they created
    - Deletion is permanent

    Requirements: Sprint 5.3 - Delete Note API

    TODO: Implement this endpoint
    - Get provider_user_id from current_user
    - Call note_service.delete_note()
    - Return success message
    """
    pass
