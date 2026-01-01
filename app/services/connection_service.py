from app.config.database import supabase_admin
from app.services.email_service import email_service
from fastapi import HTTPException, status
from typing import Dict, Optional, List
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class ConnectionService:
    """Service layer for patient-provider connection management"""

    @staticmethod
    async def request_connection(patient_user_id: str, provider_user_id: str) -> Dict:
        """
        Patient sends connection request to provider

        Business Rule: Patient can only have ONE accepted connection at a time

        Args:
            patient_user_id: The patient's user ID
            provider_user_id: The provider's user ID

        Returns:
            Connection record
        """
        try:
            # Get patient's database ID
            patient_result = supabase_admin.table("patients").select("id").eq(
                "user_id", patient_user_id
            ).execute()

            if not patient_result.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Patient profile not found"
                )

            patient_id = patient_result.data[0]["id"]

            # Get provider's database ID and verify they're approved
            provider_result = supabase_admin.table("providers").select(
                "id, license_status"
            ).eq("user_id", provider_user_id).execute()

            if not provider_result.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Provider not found"
                )

            provider_data = provider_result.data[0]

            # Only allow connections to approved providers
            if provider_data.get("license_status") != "approved":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot connect to provider with unapproved license"
                )

            provider_id = provider_data["id"]

            # Check if patient already has an accepted connection
            existing_connection = supabase_admin.table("patient_provider_connections").select(
                "*"
            ).eq("patient_id", patient_id).eq("status", "accepted").execute()

            if existing_connection.data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You already have an active connection with a provider. Please disconnect first."
                )

            # Check if there's already a pending request to this provider
            pending_request = supabase_admin.table("patient_provider_connections").select(
                "*"
            ).eq("patient_id", patient_id).eq(
                "provider_id", provider_id
            ).eq("status", "pending").execute()

            if pending_request.data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You already have a pending request to this provider"
                )

            # Create connection request
            connection_data = {
                "patient_id": patient_id,
                "provider_id": provider_id,
                "status": "pending",
                "requested_at": datetime.now(timezone.utc).isoformat()
            }

            result = supabase_admin.table("patient_provider_connections").insert(
                connection_data
            ).execute()

            if not result.data:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create connection request"
                )

            # Send email notification to provider
            try:
                # Get patient and provider details for email
                patient_details = supabase_admin.table("patients").select("full_name").eq(
                    "user_id", patient_user_id
                ).execute()

                provider_details = supabase_admin.table("providers").select("full_name").eq(
                    "user_id", provider_user_id
                ).execute()

                provider_email_result = supabase_admin.table("users").select("email").eq(
                    "id", provider_user_id
                ).execute()

                if patient_details.data and provider_details.data and provider_email_result.data:
                    email_service.send_connection_request_notification(
                        provider_email=provider_email_result.data[0]["email"],
                        provider_name=provider_details.data[0]["full_name"],
                        patient_name=patient_details.data[0]["full_name"]
                    )
                else:
                    logger.warning("Could not send email notification - missing user details")
            except Exception as e:
                # Don't fail the request if email fails
                logger.error(f"Failed to send connection request email: {str(e)}")

            return result.data[0]

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to request connection: {str(e)}"
            )

    @staticmethod
    async def get_patient_connections(
        patient_user_id: str,
        connection_status: Optional[str] = None
    ) -> List[Dict]:
        """
        Get all connections for a patient with provider details

        Args:
            patient_user_id: The patient's user ID
            connection_status: Optional filter by status (pending/accepted/rejected)

        Returns:
            List of connections with provider details
        """
        try:
            # Get patient's database ID
            patient_result = supabase_admin.table("patients").select("id").eq(
                "user_id", patient_user_id
            ).execute()

            if not patient_result.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Patient profile not found"
                )

            patient_id = patient_result.data[0]["id"]

            # Get connections
            query = supabase_admin.table("patient_provider_connections").select(
                "*"
            ).eq("patient_id", patient_id)

            if connection_status:
                query = query.eq("status", connection_status)

            result = query.order("created_at", desc=True).execute()

            if not result.data:
                return []

            # Enrich with provider details
            enriched_connections = []
            for connection in result.data:
                provider_id = connection["provider_id"]

                # Get provider details
                provider_result = supabase_admin.table("providers").select(
                    "user_id, full_name, specialisation, years_of_experience, license_status"
                ).eq("id", provider_id).execute()

                if provider_result.data:
                    provider = provider_result.data[0]

                    # Get provider email
                    user_result = supabase_admin.table("users").select("email").eq(
                        "id", provider["user_id"]
                    ).execute()

                    connection["provider_name"] = provider["full_name"]
                    connection["provider_email"] = user_result.data[0]["email"] if user_result.data else None
                    connection["provider_specialisation"] = provider.get("specialisation")
                    connection["provider_experience"] = provider.get("years_of_experience")
                    connection["provider_license_status"] = provider.get("license_status")

                enriched_connections.append(connection)

            return enriched_connections

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get patient connections: {str(e)}"
            )

    @staticmethod
    async def get_provider_requests(
        provider_user_id: str,
        connection_status: Optional[str] = None
    ) -> List[Dict]:
        """
        Get all connection requests for a provider with patient details

        Args:
            provider_user_id: The provider's user ID
            connection_status: Optional filter by status (pending/accepted/rejected)

        Returns:
            List of connection requests with patient details
        """
        try:
            # Get provider's database ID
            provider_result = supabase_admin.table("providers").select("id").eq(
                "user_id", provider_user_id
            ).execute()

            if not provider_result.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Provider profile not found"
                )

            provider_id = provider_result.data[0]["id"]

            # Get connection requests
            query = supabase_admin.table("patient_provider_connections").select(
                "*"
            ).eq("provider_id", provider_id)

            if connection_status:
                query = query.eq("status", connection_status)

            result = query.order("created_at", desc=True).execute()

            if not result.data:
                return []

            # Enrich with patient details
            enriched_requests = []
            for connection in result.data:
                patient_id = connection["patient_id"]

                # Get patient details
                patient_result = supabase_admin.table("patients").select(
                    "user_id, full_name, date_of_birth, health_goals"
                ).eq("id", patient_id).execute()

                if patient_result.data:
                    patient = patient_result.data[0]

                    # Get patient email
                    user_result = supabase_admin.table("users").select("email").eq(
                        "id", patient["user_id"]
                    ).execute()

                    # Calculate age from date_of_birth
                    age = None
                    if patient.get("date_of_birth"):
                        from datetime import date
                        dob = patient["date_of_birth"]
                        if isinstance(dob, str):
                            dob = date.fromisoformat(dob)
                        today = date.today()
                        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

                    connection["patient_name"] = patient["full_name"]
                    connection["patient_email"] = user_result.data[0]["email"] if user_result.data else None
                    connection["patient_age"] = age
                    connection["patient_health_goals"] = patient.get("health_goals", [])

                enriched_requests.append(connection)

            return enriched_requests

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get provider requests: {str(e)}"
            )

    @staticmethod
    async def accept_connection(connection_id: str, provider_user_id: str) -> Dict:
        """
        Provider accepts a connection request

        Business Rule: Double-check patient doesn't have another accepted connection

        Args:
            connection_id: The connection ID
            provider_user_id: The provider's user ID (for authorization)

        Returns:
            Updated connection record
        """
        try:
            # Get provider's database ID
            provider_result = supabase_admin.table("providers").select("id").eq(
                "user_id", provider_user_id
            ).execute()

            if not provider_result.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Provider profile not found"
                )

            provider_id = provider_result.data[0]["id"]

            # Get the connection and verify it belongs to this provider
            connection_result = supabase_admin.table("patient_provider_connections").select(
                "*"
            ).eq("id", connection_id).execute()

            if not connection_result.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Connection request not found"
                )

            connection = connection_result.data[0]

            if connection["provider_id"] != provider_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not authorized to accept this connection"
                )

            if connection["status"] != "pending":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Connection is already {connection['status']}"
                )

            # Double-check patient doesn't have another accepted connection
            patient_id = connection["patient_id"]
            existing_accepted = supabase_admin.table("patient_provider_connections").select(
                "*"
            ).eq("patient_id", patient_id).eq("status", "accepted").execute()

            if existing_accepted.data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Patient already has an active connection with another provider"
                )

            # Accept the connection
            update_data = {
                "status": "accepted",
                "accepted_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            result = supabase_admin.table("patient_provider_connections").update(
                update_data
            ).eq("id", connection_id).execute()

            if not result.data:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to accept connection"
                )

            # Send email notification to patient
            try:
                # Get patient user_id from patient_id
                patient_profile = supabase_admin.table("patients").select("user_id, full_name").eq(
                    "id", patient_id
                ).execute()

                provider_profile = supabase_admin.table("providers").select("full_name").eq(
                    "user_id", provider_user_id
                ).execute()

                if patient_profile.data and provider_profile.data:
                    patient_user_id = patient_profile.data[0]["user_id"]

                    patient_email_result = supabase_admin.table("users").select("email").eq(
                        "id", patient_user_id
                    ).execute()

                    if patient_email_result.data:
                        email_service.send_connection_accepted_notification(
                            patient_email=patient_email_result.data[0]["email"],
                            patient_name=patient_profile.data[0]["full_name"],
                            provider_name=provider_profile.data[0]["full_name"]
                        )
                else:
                    logger.warning("Could not send email notification - missing user details")
            except Exception as e:
                # Don't fail the request if email fails
                logger.error(f"Failed to send connection accepted email: {str(e)}")

            return result.data[0]

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to accept connection: {str(e)}"
            )

    @staticmethod
    async def reject_connection(connection_id: str, provider_user_id: str) -> Dict:
        """
        Provider rejects a connection request

        Args:
            connection_id: The connection ID
            provider_user_id: The provider's user ID (for authorization)

        Returns:
            Updated connection record
        """
        try:
            # Get provider's database ID
            provider_result = supabase_admin.table("providers").select("id").eq(
                "user_id", provider_user_id
            ).execute()

            if not provider_result.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Provider profile not found"
                )

            provider_id = provider_result.data[0]["id"]

            # Get the connection and verify it belongs to this provider
            connection_result = supabase_admin.table("patient_provider_connections").select(
                "*"
            ).eq("id", connection_id).execute()

            if not connection_result.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Connection request not found"
                )

            connection = connection_result.data[0]

            if connection["provider_id"] != provider_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not authorized to reject this connection"
                )

            if connection["status"] != "pending":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Connection is already {connection['status']}"
                )

            # Reject the connection
            update_data = {
                "status": "rejected",
                "rejected_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            result = supabase_admin.table("patient_provider_connections").update(
                update_data
            ).eq("id", connection_id).execute()

            if not result.data:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to reject connection"
                )

            # Send email notification to patient
            try:
                # Get patient user_id from patient_id
                patient_id = connection["patient_id"]
                patient_profile = supabase_admin.table("patients").select("user_id, full_name").eq(
                    "id", patient_id
                ).execute()

                provider_profile = supabase_admin.table("providers").select("full_name").eq(
                    "user_id", provider_user_id
                ).execute()

                if patient_profile.data and provider_profile.data:
                    patient_user_id_for_email = patient_profile.data[0]["user_id"]

                    patient_email_result = supabase_admin.table("users").select("email").eq(
                        "id", patient_user_id_for_email
                    ).execute()

                    if patient_email_result.data:
                        email_service.send_connection_rejected_notification(
                            patient_email=patient_email_result.data[0]["email"],
                            patient_name=patient_profile.data[0]["full_name"],
                            provider_name=provider_profile.data[0]["full_name"]
                        )
                else:
                    logger.warning("Could not send email notification - missing user details")
            except Exception as e:
                # Don't fail the request if email fails
                logger.error(f"Failed to send connection rejected email: {str(e)}")

            return result.data[0]

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to reject connection: {str(e)}"
            )

    @staticmethod
    async def disconnect_from_provider(connection_id: str, patient_user_id: str) -> Dict:
        """
        Patient disconnects from their current provider

        Args:
            connection_id: The connection ID
            patient_user_id: The patient's user ID (for authorization)

        Returns:
            Updated connection record with disconnected status
        """
        try:
            # Get patient's database ID
            patient_result = supabase_admin.table("patients").select("id").eq(
                "user_id", patient_user_id
            ).execute()

            if not patient_result.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Patient profile not found"
                )

            patient_id = patient_result.data[0]["id"]

            # Get the connection and verify it belongs to this patient
            connection_result = supabase_admin.table("patient_provider_connections").select(
                "*"
            ).eq("id", connection_id).execute()

            if not connection_result.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Connection not found"
                )

            connection = connection_result.data[0]

            if connection["patient_id"] != patient_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not authorized to disconnect this connection"
                )

            if connection["status"] != "accepted":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Can only disconnect from accepted connections"
                )

            # Disconnect
            update_data = {
                "status": "disconnected",
                "disconnected_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            result = supabase_admin.table("patient_provider_connections").update(
                update_data
            ).eq("id", connection_id).execute()

            if not result.data:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to disconnect"
                )

            # Send email notification to provider
            try:
                # Get provider user_id from provider_id
                provider_id = connection["provider_id"]
                provider_profile = supabase_admin.table("providers").select("user_id, full_name").eq(
                    "id", provider_id
                ).execute()

                patient_profile = supabase_admin.table("patients").select("full_name").eq(
                    "user_id", patient_user_id
                ).execute()

                if provider_profile.data and patient_profile.data:
                    provider_user_id_for_email = provider_profile.data[0]["user_id"]

                    provider_email_result = supabase_admin.table("users").select("email").eq(
                        "id", provider_user_id_for_email
                    ).execute()

                    if provider_email_result.data:
                        email_service.send_disconnection_notification(
                            provider_email=provider_email_result.data[0]["email"],
                            provider_name=provider_profile.data[0]["full_name"],
                            patient_name=patient_profile.data[0]["full_name"]
                        )
                else:
                    logger.warning("Could not send email notification - missing user details")
            except Exception as e:
                # Don't fail the request if email fails
                logger.error(f"Failed to send disconnection email: {str(e)}")

            return result.data[0]

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to disconnect from provider: {str(e)}"
            )

    @staticmethod
    async def get_connected_patients(provider_user_id: str) -> List[Dict]:
        """
        Get all patients connected to this provider (accepted status only)

        Args:
            provider_user_id: The provider's user ID

        Returns:
            List of connected patients with their details
        """
        try:
            # Get provider's database ID
            provider_result = supabase_admin.table("providers").select("id").eq(
                "user_id", provider_user_id
            ).execute()

            if not provider_result.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Provider profile not found"
                )

            provider_id = provider_result.data[0]["id"]

            # Get accepted connections only
            connections = supabase_admin.table("patient_provider_connections").select(
                "*"
            ).eq("provider_id", provider_id).eq("status", "accepted").order(
                "accepted_at", desc=True
            ).execute()

            if not connections.data:
                return []

            # Enrich with patient details
            connected_patients = []
            for connection in connections.data:
                patient_id = connection["patient_id"]

                # Get patient details
                patient_result = supabase_admin.table("patients").select(
                    "user_id, full_name, date_of_birth, health_goals, health_restrictions"
                ).eq("id", patient_id).execute()

                if patient_result.data:
                    patient = patient_result.data[0]

                    # Get patient email
                    user_result = supabase_admin.table("users").select("email").eq(
                        "id", patient["user_id"]
                    ).execute()

                    # Calculate age
                    age = None
                    if patient.get("date_of_birth"):
                        from datetime import date
                        dob = patient["date_of_birth"]
                        if isinstance(dob, str):
                            dob = date.fromisoformat(dob)
                        today = date.today()
                        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

                    connected_patients.append({
                        "connection_id": connection["id"],
                        "patient_id": patient["user_id"],
                        "patient_name": patient["full_name"],
                        "patient_email": user_result.data[0]["email"] if user_result.data else None,
                        "patient_age": age,
                        "health_goals": patient.get("health_goals", []),
                        "health_restrictions": patient.get("health_restrictions", "").split(",") if patient.get("health_restrictions") else [],
                        "connected_since": connection.get("accepted_at")
                    })

            return connected_patients

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get connected patients: {str(e)}"
            )


# Create singleton instance
connection_service = ConnectionService()
