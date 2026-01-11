from app.config.database import supabase_admin
from fastapi import HTTPException, status
from typing import Dict, List, Optional
from datetime import datetime, timezone
from app.utils.connection_helpers import verify_provider_patient_connection
import logging

logger = logging.getLogger(__name__)


class NoteService:
    """Service layer for HCP notes management"""

    @staticmethod
    async def get_my_notes(
        patient_user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """
        Get all notes for a patient (patient view - shows notes about them)

        Business Rules:
        - Patient can view all notes written about them by any provider
        - Notes are ordered by created_at DESC (most recent first)
        - Supports pagination

        Args:
            patient_user_id: The patient's user ID
            limit: Maximum number of notes to return
            offset: Number of notes to skip

        Returns:
            List of note records

        TODO: Implement this function
        - Get patient's profile_id from patients table using patient_user_id
        - Query hcp_notes table for notes where patient_id matches
        - Order by created_at DESC
        - Apply limit and offset for pagination
        - Return list of notes
        """
        patient_data = supabase_admin.table("patients") \
            .select("id") \
            .eq("user_id", patient_user_id) \
            .single() \
            .execute()

        if not patient_data.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Patient profile not found"
            )
        
        patient_profile_id = patient_data.data["id"]

        # 2. Search the notes table for all notes matching this patient
        # We also ask to see the Provider's name so the patient knows who wrote it
        notes_query = supabase_admin.table("hcp_notes") \
            .select("*, provider:providers(id, full_name)") \
            .eq("patient_id", patient_profile_id) \
            .order("created_at", desc=True) \
            .range(offset, offset + limit - 1) \
            .execute()

        return notes_query.data

    @staticmethod
    async def mark_note_as_read(
        patient_user_id: str,
        note_id: str
    ) -> Dict:
        """
        Mark a note as read by the patient

        Business Rules:
        - Patient can only mark notes about themselves
        - Sets is_read to True and records read_at timestamp

        Args:
            patient_user_id: The patient's user ID
            note_id: The note's ID

        Returns:
            Updated note record

        TODO: Implement this function
        - Get patient's profile_id from patients table
        - Verify note exists and belongs to this patient (patient_id matches)
        - Update note with is_read=True and read_at=current timestamp
        - Return updated note record
        """
        # 1. Get patient's internal profile_id (The "ID Badge")
        patient_data = supabase_admin.table("patients") \
            .select("id") \
            .eq("user_id", patient_user_id) \
            .single() \
            .execute()

        if not patient_data.data:
            raise HTTPException(status_code=404, detail="Patient profile not found")
        
        patient_profile_id = patient_data.data["id"]

        # 2. Update the note, but ONLY if it belongs to this patient
        # We use .eq("id", note_id) AND .eq("patient_id", patient_profile_id) for safety
        update_data = {
            "is_read": True,
            "read_at": datetime.now(timezone.utc).isoformat()
        }

        result = supabase_admin.table("hcp_notes") \
            .update(update_data) \
            .eq("id", note_id) \
            .eq("patient_id", patient_profile_id) \
            .execute()

        # 3. Fetch the updated note with provider info
        if result.data:
            note = supabase_admin.table("hcp_notes") \
                .select("*, provider:providers(id, full_name)") \
                .eq("id", note_id) \
                .single() \
                .execute()
            result.data = [note.data] if note.data else []

        # 4. If nothing happened (data is empty), it means the note wasn't theirs
        if not result.data:
            raise HTTPException(
                status_code=404,
                detail="Note not found or access denied"
            )

        return result.data[0]

    @staticmethod
    async def get_all_provider_notes(
        provider_user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """
        Get all notes created by a provider (across all their patients)

        Business Rules:
        - Provider can view all notes they created
        - Notes are ordered by created_at DESC (most recent first)
        - Supports pagination

        Args:
            provider_user_id: The provider's user ID
            limit: Maximum number of notes to return
            offset: Number of notes to skip

        Returns:
            List of note records

        TODO: Implement this function
        - Get provider's profile_id from providers table using provider_user_id
        - Query hcp_notes table for notes where provider_id matches
        - Order by created_at DESC
        - Apply limit and offset for pagination
        - Return list of notes
        """
        # 1. Find the Provider's internal ID (Their "Doctor Badge")
        provider_data = supabase_admin.table("providers") \
            .select("id") \
            .eq("user_id", provider_user_id) \
            .single() \
            .execute()

        if not provider_data.data:
            raise HTTPException(status_code=404, detail="Provider profile not found")
        
        provider_profile_id = provider_data.data["id"]

        # 2. Get all notes where the 'provider_id' matches this doctor
        # We also grab the patient's name so the doctor knows who the note is for!
        notes_query = supabase_admin.table("hcp_notes") \
            .select("*, patient:patients(id, full_name)") \
            .eq("provider_id", provider_profile_id) \
            .order("created_at", desc=True) \
            .range(offset, offset + limit - 1) \
            .execute()

        return notes_query.data

    @staticmethod
    async def create_note(
        provider_user_id: str,
        patient_user_id: str,
        content: str
    ) -> Dict:
        """
        Create a new note for a patient by a healthcare provider

        Business Rules:
        - Provider must have an accepted connection with the patient
        - Content cannot be empty
        - Automatically records provider_id and patient_id from their profile IDs

        Args:
            provider_user_id: The provider's user ID
            patient_user_id: The patient's user ID
            content: The note content

        Returns:
            Created note record

        TODO: Implement this function
        - Get provider's profile_id from providers table using provider_user_id
        - Get patient's profile_id from patients table using patient_user_id
        - Verify provider has accepted connection with patient
        - Insert note into hcp_notes table with provider_id, patient_id, content
        - Return created note record
        """
        # 1. Validation: Make sure the note isn't empty
        if not content or not content.strip():
            raise HTTPException(
                status_code=400, 
                detail="Note content cannot be empty"
            )

        # 2. Use the Helper to get both Profile IDs and check their connection
        # This one line does the "Gatekeeping" for you!
        provider_profile_id, patient_profile_id = await NoteService._verify_provider_patient_connection(
            provider_user_id, patient_user_id
        )

        # 3. Create the note record
        note_data = {
            "provider_id": provider_profile_id,
            "patient_id": patient_profile_id,
            "content": content,
            "is_read": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        # 4. Save it to the database
        result = supabase_admin.table("hcp_notes") \
            .insert(note_data) \
            .select("*, provider:providers(id, full_name), patient:patients(id, full_name)") \
            .execute()

        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create note")

        return result.data[0]

    @staticmethod
    async def get_patient_notes(
        provider_user_id: str,
        patient_user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """
        Get all notes for a specific patient (for provider view)

        Business Rules:
        - Provider must have an accepted connection with the patient
        - Notes are ordered by created_at DESC (most recent first)
        - Supports pagination

        Args:
            provider_user_id: The provider's user ID
            patient_user_id: The patient's user ID
            limit: Maximum number of notes to return
            offset: Number of notes to skip

        Returns:
            List of note records

        TODO: Implement this function
        - Get provider's profile_id from providers table
        - Get patient's profile_id from patients table
        - Verify provider has accepted connection with patient
        - Query hcp_notes table for notes where patient_id matches
        - Order by created_at DESC
        - Apply limit and offset for pagination
        - Return list of notes
        """
        # 1. Verification: Use the helper to check the connection and get IDs
        # This ensures the doctor and patient are "linked"
        provider_profile_id, patient_profile_id = await NoteService._verify_provider_patient_connection(
            provider_user_id, patient_user_id
        )

        # 2. Search for notes that match BOTH the doctor and the patient
        notes_query = supabase_admin.table("hcp_notes") \
            .select("*, patient:patients(id, full_name)") \
            .eq("patient_id", patient_profile_id) \
            .eq("provider_id", provider_profile_id) \
            .order("created_at", desc=True) \
            .range(offset, offset + limit - 1) \
            .execute()

        # 3. Hand back the list of notes
        return notes_query.data

    @staticmethod
    async def get_note_by_id(
        provider_user_id: str,
        note_id: str
    ) -> Dict:
        """
        Get a specific note by ID

        Business Rules:
        - Provider can only view notes they created
        - Note must exist

        Args:
            provider_user_id: The provider's user ID
            note_id: The note's ID

        Returns:
            Note record

        TODO: Implement this function
        - Get provider's profile_id from providers table
        - Query hcp_notes table for note with note_id
        - Verify the note belongs to this provider (provider_id matches)
        - Return note record or raise 404 if not found
        """
        # 1. Get the Doctor's internal ID
        provider_data = supabase_admin.table("providers") \
            .select("id") \
            .eq("user_id", provider_user_id) \
            .single() \
            .execute()

        if not provider_data.data:
            raise HTTPException(status_code=404, detail="Provider profile not found")
        
        provider_profile_id = provider_data.data["id"]

        # 2. Look for the specific note, but ONLY if the provider_id matches
        # This prevents Doctor A from snooping on Doctor B's notes
        result = supabase_admin.table("hcp_notes") \
            .select("*, patient:patients(id, full_name)") \
            .eq("id", note_id) \
            .eq("provider_id", provider_profile_id) \
            .single() \
            .execute()

        # 3. Check if we actually found it
        if not result.data:
            raise HTTPException(
                status_code=404, 
                detail="Note not found or you do not have permission to view it"
            )

        return result.data

    @staticmethod
    async def update_note(
        provider_user_id: str,
        note_id: str,
        content: str
    ) -> Dict:
        """
        Update an existing note

        Business Rules:
        - Provider can only update notes they created
        - Content cannot be empty
        - Updates the updated_at timestamp

        Args:
            provider_user_id: The provider's user ID
            note_id: The note's ID
            content: New note content

        Returns:
            Updated note record

        TODO: Implement this function
        - Get provider's profile_id from providers table
        - Verify note exists and belongs to this provider
        - Update note content and updated_at timestamp
        - Return updated note record
        """
        # 1. Validation: Make sure they didn't send an empty note
        if not content or not content.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Note content cannot be empty"
            )

        # 2. Get the Provider's internal ID
        provider_data = supabase_admin.table("providers") \
            .select("id") \
            .eq("user_id", provider_user_id) \
            .single() \
            .execute()

        if not provider_data.data:
            raise HTTPException(status_code=404, detail="Provider profile not found")
        
        provider_profile_id = provider_data.data["id"]

        # 3. Prepare the update data with a new "Last Updated" timestamp
        update_data = {
            "content": content,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        # 4. Perform the update
        # We search by BOTH the note ID and the Provider ID to ensure ownership
        result = supabase_admin.table("hcp_notes") \
            .update(update_data) \
            .eq("id", note_id) \
            .eq("provider_id", provider_profile_id) \
            .execute()

        # 5. Fetch the updated note with patient info
        if result.data:
            note = supabase_admin.table("hcp_notes") \
                .select("*, patient:patients(id, full_name)") \
                .eq("id", note_id) \
                .single() \
                .execute()
            result.data = [note.data] if note.data else []

        # 6. If nothing was updated, either the ID is wrong or they don't own it
        if not result.data:
            raise HTTPException(
                status_code=404,
                detail="Note not found or you do not have permission to edit it"
            )

        return result.data[0]

    @staticmethod
    async def delete_note(
        provider_user_id: str,
        note_id: str
    ) -> Dict:
        """
        Delete a note

        Business Rules:
        - Provider can only delete notes they created
        - Deletion is permanent

        Args:
            provider_user_id: The provider's user ID
            note_id: The note's ID

        Returns:
            Success message

        TODO: Implement this function
        - Get provider's profile_id from providers table
        - Verify note exists and belongs to this provider
        - Delete note from hcp_notes table
        - Return success message
        """
        # 1. Get the Provider's internal ID
        provider_data = supabase_admin.table("providers") \
            .select("id") \
            .eq("user_id", provider_user_id) \
            .single() \
            .execute()

        if not provider_data.data:
            raise HTTPException(status_code=404, detail="Provider profile not found")
        
        provider_profile_id = provider_data.data["id"]

        # 2. Try to delete the note
        # We add .eq("provider_id", provider_profile_id) so they can't delete other people's notes!
        result = supabase_admin.table("hcp_notes") \
            .delete() \
            .eq("id", note_id) \
            .eq("provider_id", provider_profile_id) \
            .execute()

        # 3. If the database didn't find a note that matched both IDs, nothing gets deleted
        if not result.data:
            raise HTTPException(
                status_code=404, 
                detail="Note not found or you do not have permission to delete it"
            )

        # 4. Return a success message
        return {"message": "Note deleted successfully", "note_id": note_id}

    @staticmethod
    async def _verify_provider_patient_connection(
        provider_user_id: str,
        patient_user_id: str
    ) -> tuple:
        """
        Helper function to verify provider-patient connection and get profile IDs

        Args:
            provider_user_id: The provider's user ID
            patient_user_id: The patient's user ID

        Returns:
            Tuple of (provider_profile_id, patient_profile_id)

        Raises:
            HTTPException: If connection is not found or not accepted
        """
        return await verify_provider_patient_connection(provider_user_id, patient_user_id)


# Singleton instance
note_service = NoteService()
