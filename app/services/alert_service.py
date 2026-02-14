from app.config.database import supabase_admin
from app.config.settings import settings
from app.services.threshold_service import threshold_service
from app.services.notification_service import notification_service
from fastapi import HTTPException, status
from typing import Dict, Optional, List
from datetime import datetime, timedelta, timezone
import logging

logger = logging.getLogger(__name__)


class AlertService:
    """Service for real-time anomaly detection and alert management"""

    @staticmethod
    async def check_and_alert(
        patient_user_id: str,
        biomarker_id: str,
        biomarker_type: str,
        value: float,
        unit: str,
    ) -> Dict:
        """
        Main entry point: called after every biomarker insert.
        Checks value against effective thresholds, creates alert if needed,
        sends notifications respecting cooldown.
        """
        try:
            # 1. Get effective threshold for this biomarker type
            threshold = await threshold_service.get_effective_threshold_for_type(
                patient_user_id, biomarker_type
            )

            # 2. Evaluate value against thresholds
            alert_type = None
            alert_direction = None
            threshold_value = None

            # Check critical first (higher priority)
            if threshold.get("critical_high") is not None and value > threshold["critical_high"]:
                alert_type = "critical"
                alert_direction = "high"
                threshold_value = threshold["critical_high"]
            elif threshold.get("critical_low") is not None and value < threshold["critical_low"]:
                alert_type = "critical"
                alert_direction = "low"
                threshold_value = threshold["critical_low"]
            # Then check warning
            elif threshold.get("warning_high") is not None and value > threshold["warning_high"]:
                alert_type = "warning"
                alert_direction = "high"
                threshold_value = threshold["warning_high"]
            elif threshold.get("warning_low") is not None and value < threshold["warning_low"]:
                alert_type = "warning"
                alert_direction = "low"
                threshold_value = threshold["warning_low"]

            if not alert_type:
                return {"alert_triggered": False, "cooldown_active": False}

            # 3. Check cooldown
            in_cooldown = await AlertService._is_in_cooldown(
                patient_user_id, biomarker_type, alert_type
            )

            if in_cooldown:
                return {
                    "alert_triggered": True,
                    "alert_type": alert_type,
                    "alert_direction": alert_direction,
                    "threshold_source": threshold.get("source", "global"),
                    "threshold_value": threshold_value,
                    "cooldown_active": True,
                }

            # 4. Find threshold_id if custom
            threshold_id = None
            if threshold.get("source") != "global":
                t_response = (
                    supabase_admin.table("alert_thresholds")
                    .select("id")
                    .eq("patient_user_id", patient_user_id)
                    .eq("biomarker_type", biomarker_type)
                    .eq("set_by_role", threshold["source"])
                    .eq("is_active", True)
                    .execute()
                )
                if t_response.data:
                    threshold_id = t_response.data[0]["id"]

            # 5. Create alert history record
            alert_record = {
                "patient_user_id": patient_user_id,
                "biomarker_id": biomarker_id,
                "biomarker_type": biomarker_type,
                "value": value,
                "unit": unit,
                "alert_type": alert_type,
                "alert_direction": alert_direction,
                "threshold_id": threshold_id,
                "threshold_source": threshold.get("source", "global"),
                "threshold_value": threshold_value,
                "status": "triggered",
            }

            alert_response = (
                supabase_admin.table("alert_history")
                .insert(alert_record)
                .execute()
            )
            alert_id = alert_response.data[0]["id"] if alert_response.data else None

            # 6. Send notifications
            notification_results = []
            channels = []

            if alert_type == "warning":
                notification_results = await notification_service.send_warning_notification(
                    patient_user_id=patient_user_id,
                    biomarker_type=biomarker_type,
                    value=value,
                    unit=unit,
                    threshold_value=threshold_value,
                    direction=alert_direction,
                    alert_id=alert_id,
                )
                channels = ["email"]
            elif alert_type == "critical":
                notification_results = await notification_service.send_critical_alert(
                    patient_user_id=patient_user_id,
                    biomarker_type=biomarker_type,
                    value=value,
                    unit=unit,
                    threshold_value=threshold_value,
                    direction=alert_direction,
                    alert_id=alert_id,
                )
                channels = list(set(r.get("channel", "email") for r in notification_results))

            # 7. Update alert record with notification results
            total_attempts = sum(r.get("attempts", 0) for r in notification_results)
            any_success = any(r.get("success", False) for r in notification_results)
            new_status = "notified" if any_success else ("triggered" if not notification_results else "triggered")
            if alert_id:
                supabase_admin.table("alert_history").update({
                    "status": new_status,
                    "notification_channels": channels,
                    "notification_attempts": total_attempts,
                    "notification_results": notification_results,
                }).eq("id", alert_id).execute()

            # 8. Update cooldown
            await AlertService._update_cooldown(patient_user_id, biomarker_type, alert_type)

            return {
                "alert_triggered": True,
                "alert_type": alert_type,
                "alert_direction": alert_direction,
                "threshold_source": threshold.get("source", "global"),
                "threshold_value": threshold_value,
                "alert_id": alert_id,
                "cooldown_active": False,
            }

        except Exception as e:
            logger.error(f"Error in check_and_alert for {patient_user_id}: {str(e)}")
            return {"alert_triggered": False, "error": str(e)}

    # =========================================================================
    # COOLDOWN MANAGEMENT
    # =========================================================================

    @staticmethod
    async def _is_in_cooldown(
        patient_user_id: str, biomarker_type: str, alert_type: str
    ) -> bool:
        """Check if alert was recently sent within cooldown period."""
        try:
            cooldown_minutes = (
                settings.alert_cooldown_critical_minutes
                if alert_type == "critical"
                else settings.alert_cooldown_warning_minutes
            )
            cutoff = (datetime.now(timezone.utc) - timedelta(minutes=cooldown_minutes)).isoformat()

            response = (
                supabase_admin.table("alert_cooldowns")
                .select("last_alerted_at")
                .eq("patient_user_id", patient_user_id)
                .eq("biomarker_type", biomarker_type)
                .eq("alert_type", alert_type)
                .gte("last_alerted_at", cutoff)
                .execute()
            )
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error checking cooldown: {e}")
            return False  # If cooldown check fails, allow the alert

    @staticmethod
    async def _update_cooldown(
        patient_user_id: str, biomarker_type: str, alert_type: str
    ) -> None:
        """Upsert cooldown record with current timestamp."""
        try:
            supabase_admin.table("alert_cooldowns").upsert(
                {
                    "patient_user_id": patient_user_id,
                    "biomarker_type": biomarker_type,
                    "alert_type": alert_type,
                    "last_alerted_at": datetime.now(timezone.utc).isoformat(),
                },
                on_conflict="patient_user_id,biomarker_type,alert_type",
            ).execute()
        except Exception as e:
            logger.error(f"Error updating cooldown: {e}")

    # =========================================================================
    # ALERT HISTORY QUERIES
    # =========================================================================

    @staticmethod
    async def get_alert_history(
        patient_user_id: str,
        limit: int = 50,
        offset: int = 0,
        alert_type: Optional[str] = None,
        alert_status: Optional[str] = None,
    ) -> Dict:
        """Get paginated alert history for a patient."""
        try:
            query = (
                supabase_admin.table("alert_history")
                .select("*", count="exact")
                .eq("patient_user_id", patient_user_id)
            )

            if alert_type:
                query = query.eq("alert_type", alert_type)
            if alert_status:
                query = query.eq("status", alert_status)

            response = (
                query
                .order("created_at", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )

            return {
                "total_count": response.count or len(response.data or []),
                "alerts": response.data or [],
            }
        except Exception as e:
            logger.error(f"Error fetching alert history: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch alert history"
            )

    @staticmethod
    async def get_alert_history_for_provider(
        provider_user_id: str,
        patient_user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict:
        """Provider gets patient's alert history (verifies connection first)."""
        try:
            # Verify connection
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

            return await AlertService.get_alert_history(
                patient_user_id, limit, offset
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching patient alert history for provider: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch patient alert history"
            )

    @staticmethod
    async def acknowledge_alert(alert_id: str, user_id: str) -> Dict:
        """Mark an alert as acknowledged."""
        try:
            # Verify alert exists and belongs to user (or user is connected provider)
            existing = (
                supabase_admin.table("alert_history")
                .select("*")
                .eq("id", alert_id)
                .execute()
            )
            if not existing.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Alert not found"
                )

            response = (
                supabase_admin.table("alert_history")
                .update({
                    "status": "acknowledged",
                    "acknowledged_at": datetime.now(timezone.utc).isoformat(),
                    "acknowledged_by": user_id,
                })
                .eq("id", alert_id)
                .execute()
            )

            return response.data[0] if response.data else existing.data[0]
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error acknowledging alert {alert_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to acknowledge alert"
            )

    @staticmethod
    async def get_unacknowledged_count(patient_user_id: str) -> int:
        """Get count of unacknowledged alerts for badge display."""
        try:
            response = (
                supabase_admin.table("alert_history")
                .select("id", count="exact")
                .eq("patient_user_id", patient_user_id)
                .in_("status", ["triggered", "notified"])
                .execute()
            )
            return response.count or 0
        except Exception as e:
            logger.error(f"Error getting unacknowledged count: {str(e)}")
            return 0


# Singleton instance
alert_service = AlertService()
