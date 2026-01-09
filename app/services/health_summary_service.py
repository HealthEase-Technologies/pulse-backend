from app.config.database import supabase_admin
from app.services.email_service import email_service
from fastapi import HTTPException, status
from typing import Dict, Optional, List
from datetime import date, timedelta, datetime, timezone
import logging

logger = logging.getLogger(__name__)


class HealthSummaryService:
    """Service layer for daily health summary generation and management"""

    # MORNING BRIEFING (12:01 AM)
    @staticmethod
    async def generate_morning_briefing(
        target_date: Optional[date] = None
    ) -> Dict:
        try:
            if not target_date:
                target_date = date.today() - timedelta(days=1)

            start_ts = f"{target_date}T00:00:00"
            end_ts = f"{target_date}T23:59:59"

            users_resp = (
                supabase_admin
                .table("biomarkers")
                .select("user_id")
                .gte("recorded_at", start_ts)
                .lte("recorded_at", end_ts)
                .execute()
            )

            user_ids = {row["user_id"] for row in users_resp.data} if users_resp.data else set()

            summaries_created = 0
            users_with_alerts = 0

            for user_id in user_ids:
                result = await HealthSummaryService.calculate_daily_summary(
                    user_id=user_id,
                    target_date=target_date,
                    summary_type="morning_briefing"
                )

                supabase_admin.table("daily_health_summaries").insert({
                    "user_id": user_id,
                    "summary_date": target_date.isoformat(),
                    "summary_type": "morning_briefing",
                    "summary_data": result["summary_data"],
                    "overall_status": result["overall_status"],
                    "email_sent": False,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }).execute()

                summaries_created += 1
                if result["has_critical_values"]:
                    users_with_alerts += 1

            return {
                "total_users_processed": len(user_ids),
                "summaries_created": summaries_created,
                "users_with_alerts": users_with_alerts
            }

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate morning briefing: {str(e)}"
            )

    # EVENING SUMMARY (11:59 PM)
    @staticmethod
    async def generate_evening_summary(
        target_date: Optional[date] = None
    ) -> Dict:
        try:
            if not target_date:
                target_date = date.today()

            start_ts = f"{target_date}T00:00:00"
            end_ts = f"{target_date}T23:59:59"

            users_resp = (
                supabase_admin
                .table("biomarkers")
                .select("user_id")
                .gte("recorded_at", start_ts)
                .lte("recorded_at", end_ts)
                .execute()
            )

            user_ids = {row["user_id"] for row in users_resp.data} if users_resp.data else set()
            summaries_created = 0

            for user_id in user_ids:
                result = await HealthSummaryService.calculate_daily_summary(
                    user_id=user_id,
                    target_date=target_date,
                    summary_type="evening_summary"
                )

                supabase_admin.table("daily_health_summaries").insert({
                    "user_id": user_id,
                    "summary_date": target_date.isoformat(),
                    "summary_type": "evening_summary",
                    "summary_data": result["summary_data"],
                    "overall_status": result["overall_status"],
                    "email_sent": True,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }).execute()

                summaries_created += 1

            return {
                "total_users_processed": len(user_ids),
                "summaries_created": summaries_created
            }

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate evening summary: {str(e)}"
            )

    # CORE DAILY SUMMARY
    @staticmethod
    async def calculate_daily_summary(
        user_id: str,
        target_date: date,
        summary_type: str
    ) -> Dict:
        try:
            start_ts = f"{target_date}T00:00:00"
            end_ts = f"{target_date}T23:59:59"

            biomarker_resp = (
                supabase_admin
                .table("biomarkers")
                .select("biomarker_type,value")
                .eq("user_id", user_id)
                .gte("recorded_at", start_ts)
                .lte("recorded_at", end_ts)
                .execute()
            )

            if not biomarker_resp.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No biomarker data for this date"
                )

            grouped = {}
            for row in biomarker_resp.data:
                grouped.setdefault(row["biomarker_type"], []).append(row["value"])

            metrics = {}
            insights = []
            alerts = []
            has_critical = False
            has_concerning = False

            for biomarker, values in grouped.items():
                avg_val = sum(values) / len(values)
                min_val = min(values)
                max_val = max(values)

                range_resp = (
                    supabase_admin
                    .table("biomarker_ranges")
                    .select("*")
                    .eq("biomarker_type", biomarker)
                    .single()
                    .execute()
                )

                status_label = "normal"

                if range_resp.data:
                    r = range_resp.data
                    if avg_val < r["critical_low"] or avg_val > r["critical_high"]:
                        status_label = "critical"
                        has_critical = True
                    elif avg_val < r["min_normal"] or avg_val > r["max_normal"]:
                        status_label = "concerning"
                        has_concerning = True
                    elif r["min_optimal"] <= avg_val <= r["max_optimal"]:
                        status_label = "optimal"

                # Handle special biomarker types
                if biomarker == "blood_pressure_systolic":
                    # Blood pressure is handled separately - store for later
                    if "blood_pressure" not in metrics:
                        metrics["blood_pressure"] = {
                            "readings_count": len(values),
                            "status": status_label
                        }
                    metrics["blood_pressure"]["systolic_avg"] = round(avg_val, 2)
                elif biomarker == "blood_pressure_diastolic":
                    if "blood_pressure" not in metrics:
                        metrics["blood_pressure"] = {
                            "readings_count": len(values),
                            "status": status_label
                        }
                    metrics["blood_pressure"]["diastolic_avg"] = round(avg_val, 2)
                elif biomarker == "steps":
                    # Steps is a total, not an average
                    total_steps = int(sum(values))
                    metrics["steps"] = {
                        "total": total_steps,
                        "goal": 10000,
                        "percentage": round((total_steps / 10000) * 100, 2),
                        "status": status_label
                    }
                elif biomarker == "sleep_duration":
                    # Sleep duration in hours
                    metrics["sleep"] = {
                        "hours": round(avg_val, 2),
                        "goal": 8.0,
                        "status": status_label
                    }
                else:
                    # Standard biomarkers (heart_rate, glucose, etc.)
                    metrics[biomarker] = {
                        "avg": round(avg_val, 2),
                        "min": round(min_val, 2),
                        "max": round(max_val, 2),
                        "readings_count": len(values),
                        "status": status_label
                    }

                # Generate insights
                if status_label == "optimal":
                    insights.append(f"{biomarker.replace('_', ' ').title()} is in optimal range.")
                elif status_label == "critical":
                    alert_msg = f"⚠️ Critical {biomarker.replace('_', ' ')} detected: {round(avg_val, 2)}"
                    alerts.append(alert_msg)

            overall_status = (
                "critical" if has_critical else
                "needs_attention" if has_concerning else
                "good"
            )

            # Note: overall_status is NOT part of summary_data, it's a separate DB column
            summary_data = {
                "date": target_date.isoformat(),
                "summary_type": summary_type,
                "metrics": metrics,
                "insights": insights,
                "alerts": alerts,
                "recommendations": [],
                "daily_achievements": [],
                "areas_for_improvement": []
            }

            return {
                "summary_data": summary_data,
                "total_readings": sum(len(v) for v in grouped.values()),
                "biomarkers_tracked": list(grouped.keys()),
                "has_critical_values": has_critical,
                "has_concerning_values": has_concerning,
                "overall_status": overall_status
            }

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to calculate daily summary: {str(e)}"
            )

    # SEND MORNING BRIEFING EMAILS
    @staticmethod
    async def send_morning_briefing_emails() -> int:
        """
        Send morning briefing emails to users with pending summaries

        Returns:
            Number of emails successfully sent
        """
        try:
            # Get summaries that haven't been emailed yet
            summaries_resp = (
                supabase_admin
                .table("daily_health_summaries")
                .select("id, user_id, summary_data")
                .eq("summary_type", "morning_briefing")
                .eq("email_sent", False)
                .execute()
            )

            sent_count = 0

            for row in summaries_resp.data or []:
                try:
                    # Get user email and name from users table
                    user_resp = supabase_admin.table("users").select(
                        "email, username"
                    ).eq("id", row["user_id"]).single().execute()

                    if user_resp.data:
                        user_email = user_resp.data["email"]
                        user_name = user_resp.data.get("username", "User")

                        # Send the morning briefing email
                        email_sent = email_service.send_morning_briefing(
                            patient_email=user_email,
                            patient_name=user_name,
                            summary_data=row["summary_data"]
                        )

                        if email_sent:
                            # Update the email_sent flag
                            supabase_admin.table("daily_health_summaries").update({
                                "email_sent": True,
                                "email_sent_at": datetime.now(timezone.utc).isoformat()
                            }).eq("id", row["id"]).execute()

                            sent_count += 1
                            logger.info(f"Morning briefing email sent to {user_email}")
                        else:
                            logger.warning(f"Failed to send morning briefing to {user_email}")
                    else:
                        logger.warning(f"User not found for user_id: {row['user_id']}")

                except Exception as e:
                    logger.error(f"Error sending email for summary {row['id']}: {str(e)}")
                    continue

            return sent_count

        except Exception as e:
            logger.error(f"Error in send_morning_briefing_emails: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send morning briefing emails: {str(e)}"
            )

    # GET USER SUMMARY
    @staticmethod
    async def get_user_summary(
        user_id: str,
        summary_date: date,
        summary_type: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Get user's health summary for a specific date

        Args:
            user_id: The user's ID
            summary_date: The date to get summary for
            summary_type: Optional filter by summary type

        Returns:
            Complete summary record with metadata, or None if not found
        """
        try:
            query = (
                supabase_admin
                .table("daily_health_summaries")
                .select("*")
                .eq("user_id", user_id)
                .eq("summary_date", summary_date.isoformat())
            )

            if summary_type:
                query = query.eq("summary_type", summary_type)

            resp = query.order("created_at", desc=True).limit(1).execute()

            if resp.data:
                summary = resp.data[0]
                # Calculate metadata from summary_data
                summary_data = summary.get("summary_data", {})
                metrics = summary_data.get("metrics", {})

                # Calculate total readings and biomarkers tracked
                total_readings = 0
                biomarkers_tracked = []
                for key, metric in metrics.items():
                    if isinstance(metric, dict):
                        if "readings_count" in metric:
                            total_readings += metric["readings_count"]
                            biomarkers_tracked.append(key)
                        elif key == "steps":
                            total_readings += 1
                            biomarkers_tracked.append(key)
                        elif key == "sleep":
                            total_readings += 1
                            biomarkers_tracked.append(key)

                # Add calculated fields
                summary["total_readings"] = total_readings
                summary["biomarkers_tracked"] = biomarkers_tracked
                summary["has_critical_values"] = len([a for a in summary_data.get("alerts", []) if "Critical" in a]) > 0
                summary["has_concerning_values"] = False  # Can be enhanced based on metrics status
                # overall_status comes from the database column, not summary_data

                return summary

            return None

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch user summary: {str(e)}"
            )

    # GET USER SUMMARIES RANGE
    @staticmethod
    async def get_user_summaries_range(
        user_id: str,
        start_date: date,
        end_date: date,
        summary_type: Optional[str] = None
    ) -> List[Dict]:
        """
        Get user's health summaries for a date range

        Args:
            user_id: The user's ID
            start_date: Start date of range
            end_date: End date of range
            summary_type: Optional filter by summary type

        Returns:
            List of complete summary records with metadata
        """
        try:
            query = (
                supabase_admin
                .table("daily_health_summaries")
                .select("*")
                .eq("user_id", user_id)
                .gte("summary_date", start_date.isoformat())
                .lte("summary_date", end_date.isoformat())
            )

            if summary_type:
                query = query.eq("summary_type", summary_type)

            resp = query.order("summary_date", desc=True).execute()

            summaries = []
            for record in resp.data or []:
                summary_data = record.get("summary_data", {})
                metrics = summary_data.get("metrics", {})

                # Calculate metadata
                total_readings = 0
                biomarkers_tracked = []
                for key, metric in metrics.items():
                    if isinstance(metric, dict):
                        if "readings_count" in metric:
                            total_readings += metric["readings_count"]
                            biomarkers_tracked.append(key)
                        elif key in ["steps", "sleep"]:
                            total_readings += 1
                            biomarkers_tracked.append(key)

                # Add calculated fields
                record["total_readings"] = total_readings
                record["biomarkers_tracked"] = biomarkers_tracked
                record["has_critical_values"] = len([a for a in summary_data.get("alerts", []) if "Critical" in a]) > 0
                record["has_concerning_values"] = False
                # overall_status comes from the database column, not summary_data

                summaries.append(record)

            return summaries

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch summaries range: {str(e)}"
            )

    # REGENERATE SUMMARY
    @staticmethod
    async def regenerate_summary(
        user_id: str,
        target_date: date,
        summary_type: str
    ) -> Dict:
        """
        Regenerate a health summary for a specific date and type

        Args:
            user_id: The user's ID
            target_date: The date to regenerate summary for
            summary_type: Type of summary (morning_briefing or evening_summary)

        Returns:
            The regenerated summary data
        """
        try:
            # Calculate the new summary
            result = await HealthSummaryService.calculate_daily_summary(
                user_id=user_id,
                target_date=target_date,
                summary_type=summary_type
            )

            # Check if summary already exists
            existing = (
                supabase_admin
                .table("daily_health_summaries")
                .select("id")
                .eq("user_id", user_id)
                .eq("summary_date", target_date.isoformat())
                .eq("summary_type", summary_type)
                .execute()
            )

            summary_id = None
            if existing.data:
                # Update existing summary and reset email_sent to allow re-sending
                supabase_admin.table("daily_health_summaries").update({
                    "summary_data": result["summary_data"],
                    "overall_status": result["overall_status"],
                    "email_sent": False,
                    "email_sent_at": None,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }).eq("id", existing.data[0]["id"]).execute()
                summary_id = existing.data[0]["id"]
            else:
                # Insert new summary
                insert_resp = supabase_admin.table("daily_health_summaries").insert({
                    "user_id": user_id,
                    "summary_date": target_date.isoformat(),
                    "summary_type": summary_type,
                    "summary_data": result["summary_data"],
                    "overall_status": result["overall_status"],
                    "email_sent": False,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }).execute()
                summary_id = insert_resp.data[0]["id"] if insert_resp.data else None

            # Fetch and return the complete record
            if summary_id:
                complete_resp = supabase_admin.table("daily_health_summaries").select(
                    "*"
                ).eq("id", summary_id).single().execute()

                if complete_resp.data:
                    summary = complete_resp.data
                    # Add calculated fields
                    summary["total_readings"] = result["total_readings"]
                    summary["biomarkers_tracked"] = result["biomarkers_tracked"]
                    summary["has_critical_values"] = result["has_critical_values"]
                    summary["has_concerning_values"] = result["has_concerning_values"]
                    # overall_status is already in the database record
                    return summary

            return result["summary_data"]

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to regenerate summary: {str(e)}"
            )

    # VERIFY PROVIDER-PATIENT CONNECTION
    @staticmethod
    async def _verify_provider_patient_connection(
        provider_user_id: str,
        patient_user_id: str
    ) -> None:
        """
        Verify that a provider has an accepted connection with a patient

        Args:
            provider_user_id: The provider's user ID
            patient_user_id: The patient's user ID

        Raises:
            HTTPException: If connection is not found or not accepted
        """
        try:
            # Get provider's profile_id
            provider_profile = supabase_admin.table("providers").select("id").eq(
                "user_id", provider_user_id
            ).execute()

            if not provider_profile.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Provider profile not found"
                )

            provider_profile_id = provider_profile.data[0]["id"]

            # Get patient's profile_id
            patient_profile = supabase_admin.table("patients").select("id").eq(
                "user_id", patient_user_id
            ).execute()

            if not patient_profile.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Patient profile not found"
                )

            patient_profile_id = patient_profile.data[0]["id"]

            # Verify connection using profile IDs
            connection_check = supabase_admin.table("patient_provider_connections").select(
                "status"
            ).eq("provider_id", provider_profile_id).eq(
                "patient_id", patient_profile_id
            ).execute()

            if not connection_check.data or connection_check.data[0]["status"] != "accepted":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No accepted connection with this patient"
                )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to verify provider-patient connection: {str(e)}"
            )

    # GET PATIENT SUMMARY FOR PROVIDER
    @staticmethod
    async def get_patient_summary_for_provider(
        provider_user_id: str,
        patient_user_id: str,
        summary_date: date,
        summary_type: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Provider gets a patient's health summary for a specific date

        Business Rule: Provider must have an accepted connection with the patient

        Args:
            provider_user_id: The provider's user ID
            patient_user_id: The patient's user ID
            summary_date: The date to get summary for
            summary_type: Optional filter by summary type

        Returns:
            Patient's health summary or None if not found
        """
        try:
            # Verify provider has access to this patient
            await HealthSummaryService._verify_provider_patient_connection(
                provider_user_id, patient_user_id
            )

            # Get the summary
            return await HealthSummaryService.get_user_summary(
                user_id=patient_user_id,
                summary_date=summary_date,
                summary_type=summary_type
            )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch patient summary: {str(e)}"
            )

    # GET PATIENT SUMMARIES RANGE FOR PROVIDER
    @staticmethod
    async def get_patient_summaries_range_for_provider(
        provider_user_id: str,
        patient_user_id: str,
        start_date: date,
        end_date: date,
        summary_type: Optional[str] = None
    ) -> List[Dict]:
        """
        Provider gets a patient's health summaries for a date range

        Business Rule: Provider must have an accepted connection with the patient

        Args:
            provider_user_id: The provider's user ID
            patient_user_id: The patient's user ID
            start_date: Start date of range
            end_date: End date of range
            summary_type: Optional filter by summary type

        Returns:
            List of patient's health summaries
        """
        try:
            # Verify provider has access to this patient
            await HealthSummaryService._verify_provider_patient_connection(
                provider_user_id, patient_user_id
            )

            # Get the summaries
            return await HealthSummaryService.get_user_summaries_range(
                user_id=patient_user_id,
                start_date=start_date,
                end_date=end_date,
                summary_type=summary_type
            )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch patient summaries: {str(e)}"
            )


# Singleton instance
health_summary_service = HealthSummaryService()

#for commit