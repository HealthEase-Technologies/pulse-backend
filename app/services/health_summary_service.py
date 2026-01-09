from app.config.database import supabase_admin
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

            biomarkers_summary = {}
            insights = []
            has_critical = False
            has_concerning = False

            for biomarker, values in grouped.items():
                avg_val = sum(values) / len(values)

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

                biomarkers_summary[biomarker] = {
                    "average": round(avg_val, 2),
                    "min": min(values),
                    "max": max(values),
                    "count": len(values),
                    "status": status_label
                }

                if status_label == "optimal":
                    insights.append(f"{biomarker.replace('_', ' ').title()} is in optimal range.")
                elif status_label == "critical":
                    insights.append(f"Critical {biomarker.replace('_', ' ')} detected.")

            overall_status = (
                "critical" if has_critical else
                "needs_attention" if has_concerning else
                "good"
            )

            summary_data = {
                "date": target_date.isoformat(),
                "summary_type": summary_type,
                "overall_status": overall_status,
                "biomarkers": biomarkers_summary,
                "insights": insights
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

    # SEND MORNING BRIEFING EMAIL FLAGS
    @staticmethod
    async def send_morning_briefing_emails() -> int:
        try:
            summaries_resp = (
                supabase_admin
                .table("daily_health_summaries")
                .select("id")
                .eq("summary_type", "morning_briefing")
                .eq("email_sent", False)
                .execute()
            )

            sent_count = 0

            for row in summaries_resp.data or []:
                supabase_admin.table("daily_health_summaries").update({
                    "email_sent": True,
                    "email_sent_at": datetime.now(timezone.utc).isoformat()
                }).eq("id", row["id"]).execute()

                sent_count += 1

            return sent_count

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update email status: {str(e)}"
            )

    # GET USER SUMMARY
    @staticmethod
    async def get_user_summary(
        user_id: str,
        summary_date: date,
        summary_type: Optional[str] = None
    ) -> Optional[Dict]:
        try:
            query = (
                supabase_admin
                .table("daily_health_summaries")
                .select("summary_data")
                .eq("user_id", user_id)
                .eq("summary_date", summary_date.isoformat())
            )

            if summary_type:
                query = query.eq("summary_type", summary_type)

            resp = query.order("created_at", desc=True).limit(1).execute()
            return resp.data[0]["summary_data"] if resp.data else None

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
        try:
            query = (
                supabase_admin
                .table("daily_health_summaries")
                .select("summary_data")
                .eq("user_id", user_id)
                .gte("summary_date", start_date.isoformat())
                .lte("summary_date", end_date.isoformat())
            )

            if summary_type:
                query = query.eq("summary_type", summary_type)

            resp = query.order("summary_date", desc=True).execute()
            return [r["summary_data"] for r in resp.data or []]

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch summaries range: {str(e)}"
            )


# Singleton instance
health_summary_service = HealthSummaryService()

#for commit