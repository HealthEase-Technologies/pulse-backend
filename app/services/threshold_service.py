from app.config.database import supabase_admin
from fastapi import HTTPException, status
from typing import Dict, Optional, List
from datetime import datetime, timezone
from app.schemas.biomarker import BiomarkerType
import logging

logger = logging.getLogger(__name__)


class ThresholdService:
    """Service for managing custom alert thresholds per patient"""

    BIOMARKER_TYPES = [b.value for b in BiomarkerType]

    @staticmethod
    async def get_effective_thresholds(patient_user_id: str) -> List[Dict]:
        """
        Resolve effective thresholds for all biomarker types using hierarchy:
        1. Provider-set custom threshold (highest priority)
        2. Patient-set custom threshold
        3. Global biomarker_ranges table (fallback)
        """
        try:
            # Fetch all custom thresholds for this patient
            custom_response = (
                supabase_admin
                .table("alert_thresholds")
                .select("*")
                .eq("patient_user_id", patient_user_id)
                .eq("is_active", True)
                .execute()
            )
            custom_thresholds = custom_response.data or []

            # Build lookup: {biomarker_type: {role: threshold}}
            custom_map = {}
            for t in custom_thresholds:
                bt = t["biomarker_type"]
                if bt not in custom_map:
                    custom_map[bt] = {}
                custom_map[bt][t["set_by_role"]] = t

            # Fetch global ranges
            global_response = supabase_admin.table("biomarker_ranges").select("*").execute()
            global_map = {r["biomarker_type"]: r for r in (global_response.data or [])}

            # Resolve for each biomarker type
            effective = []
            for bt in ThresholdService.BIOMARKER_TYPES:
                # Check provider-set first
                if bt in custom_map and "provider" in custom_map[bt]:
                    t = custom_map[bt]["provider"]
                    effective.append({
                        "biomarker_type": bt,
                        "warning_low": t.get("warning_low"),
                        "warning_high": t.get("warning_high"),
                        "critical_low": t.get("critical_low"),
                        "critical_high": t.get("critical_high"),
                        "source": "provider"
                    })
                # Then patient-set
                elif bt in custom_map and "patient" in custom_map[bt]:
                    t = custom_map[bt]["patient"]
                    effective.append({
                        "biomarker_type": bt,
                        "warning_low": t.get("warning_low"),
                        "warning_high": t.get("warning_high"),
                        "critical_low": t.get("critical_low"),
                        "critical_high": t.get("critical_high"),
                        "source": "patient"
                    })
                # Fallback to global
                elif bt in global_map:
                    g = global_map[bt]
                    effective.append({
                        "biomarker_type": bt,
                        "warning_low": g.get("min_normal"),
                        "warning_high": g.get("max_normal"),
                        "critical_low": g.get("critical_low"),
                        "critical_high": g.get("critical_high"),
                        "source": "global"
                    })
                else:
                    effective.append({
                        "biomarker_type": bt,
                        "warning_low": None,
                        "warning_high": None,
                        "critical_low": None,
                        "critical_high": None,
                        "source": "global"
                    })

            return effective
        except Exception as e:
            logger.error(f"Error getting effective thresholds for {patient_user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get effective thresholds"
            )

    @staticmethod
    async def get_effective_threshold_for_type(
        patient_user_id: str, biomarker_type: str
    ) -> Dict:
        """Resolve single biomarker type's effective threshold."""
        all_thresholds = await ThresholdService.get_effective_thresholds(patient_user_id)
        for t in all_thresholds:
            if t["biomarker_type"] == biomarker_type:
                return t
        return {
            "biomarker_type": biomarker_type,
            "warning_low": None,
            "warning_high": None,
            "critical_low": None,
            "critical_high": None,
            "source": "global"
        }

    @staticmethod
    async def upsert_patient_threshold(
        patient_user_id: str, data: dict
    ) -> Dict:
        """Patient sets their own custom threshold (upsert)."""
        try:
            biomarker_type = data["biomarker_type"]
            if isinstance(biomarker_type, BiomarkerType):
                biomarker_type = biomarker_type.value

            upsert_data = {
                "patient_user_id": patient_user_id,
                "set_by_user_id": patient_user_id,
                "set_by_role": "patient",
                "biomarker_type": biomarker_type,
                "warning_low": data.get("warning_low"),
                "warning_high": data.get("warning_high"),
                "critical_low": data.get("critical_low"),
                "critical_high": data.get("critical_high"),
                "is_active": True,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            response = (
                supabase_admin
                .table("alert_thresholds")
                .upsert(upsert_data, on_conflict="patient_user_id,biomarker_type,set_by_role")
                .execute()
            )

            return response.data[0] if response.data else upsert_data
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error upserting patient threshold: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to set threshold"
            )

    @staticmethod
    async def upsert_provider_threshold(
        provider_user_id: str, patient_user_id: str, data: dict
    ) -> Dict:
        """Provider sets threshold for a connected patient."""
        try:
            # Verify connection exists
            provider_profile = (
                supabase_admin.table("providers")
                .select("id")
                .eq("user_id", provider_user_id)
                .execute()
            )
            if not provider_profile.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Provider profile not found"
                )

            patient_profile = (
                supabase_admin.table("patients")
                .select("id")
                .eq("user_id", patient_user_id)
                .execute()
            )
            if not patient_profile.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Patient profile not found"
                )

            connection = (
                supabase_admin.table("patient_provider_connections")
                .select("status")
                .eq("provider_id", provider_profile.data[0]["id"])
                .eq("patient_id", patient_profile.data[0]["id"])
                .execute()
            )
            if not connection.data or connection.data[0]["status"] != "accepted":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No accepted connection with this patient"
                )

            biomarker_type = data["biomarker_type"]
            if isinstance(biomarker_type, BiomarkerType):
                biomarker_type = biomarker_type.value

            upsert_data = {
                "patient_user_id": patient_user_id,
                "set_by_user_id": provider_user_id,
                "set_by_role": "provider",
                "biomarker_type": biomarker_type,
                "warning_low": data.get("warning_low"),
                "warning_high": data.get("warning_high"),
                "critical_low": data.get("critical_low"),
                "critical_high": data.get("critical_high"),
                "is_active": True,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            response = (
                supabase_admin
                .table("alert_thresholds")
                .upsert(upsert_data, on_conflict="patient_user_id,biomarker_type,set_by_role")
                .execute()
            )

            return response.data[0] if response.data else upsert_data
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error upserting provider threshold: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to set threshold"
            )

    @staticmethod
    async def get_patient_thresholds(patient_user_id: str) -> List[Dict]:
        """Get all custom thresholds for a patient."""
        try:
            response = (
                supabase_admin
                .table("alert_thresholds")
                .select("*")
                .eq("patient_user_id", patient_user_id)
                .order("biomarker_type")
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error getting thresholds for {patient_user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get thresholds"
            )

    @staticmethod
    async def delete_threshold(threshold_id: str, requesting_user_id: str) -> bool:
        """Delete a threshold. User can only delete their own."""
        try:
            # Verify ownership
            existing = (
                supabase_admin
                .table("alert_thresholds")
                .select("*")
                .eq("id", threshold_id)
                .eq("set_by_user_id", requesting_user_id)
                .execute()
            )
            if not existing.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Threshold not found or you don't have permission to delete it"
                )

            supabase_admin.table("alert_thresholds").delete().eq("id", threshold_id).execute()
            return True
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting threshold {threshold_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete threshold"
            )


# Singleton instance
threshold_service = ThresholdService()
