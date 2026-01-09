from app.config.database import supabase_admin
from fastapi import HTTPException, status
from typing import Tuple


async def verify_provider_patient_connection(
    provider_user_id: str,
    patient_user_id: str
) -> Tuple[str, str]:
    """
    Verify provider-patient connection and get profile IDs

    Args:
        provider_user_id: The provider's user ID
        patient_user_id: The patient's user ID

    Returns:
        Tuple of (provider_profile_id, patient_profile_id)

    Raises:
        HTTPException: If connection is not found or not accepted
    """
    # Get provider's profile_id
    provider_profile = supabase_admin.table("providers")\
        .select("id")\
        .eq("user_id", provider_user_id)\
        .execute()
    if not provider_profile.data or len(provider_profile.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider profile not found"
        )
    provider_profile_id = provider_profile.data[0]["id"]

    # Get patient's profile_id
    patient_profile = supabase_admin.table("patients")\
        .select("id")\
        .eq("user_id", patient_user_id)\
        .execute()
    if not patient_profile.data or len(patient_profile.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient profile not found"
        )
    patient_profile_id = patient_profile.data[0]["id"]

    # Verify connection using profile IDs
    connection_check = supabase_admin.table("patient_provider_connections")\
        .select("status")\
        .eq("provider_id", provider_profile_id)\
        .eq("patient_id", patient_profile_id)\
        .execute()
    if not connection_check.data or len(connection_check.data) == 0 or connection_check.data[0]["status"] != "accepted":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No accepted connection with the patient"
        )

    return (provider_profile_id, patient_profile_id)
