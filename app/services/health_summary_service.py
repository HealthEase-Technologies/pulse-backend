from app.config.database import supabase_admin
from sqlalchemy.orm import Session
from sqlalchemy import text, and_
from app.db.models.health_summary import DailyHealthSummary
from fastapi import HTTPException, status
from typing import Dict, Optional, List
from datetime import datetime, timezone, date, timedelta
import logging

logger = logging.getLogger(__name__)


class HealthSummaryService:
    """Service layer for daily health summary generation and management"""

    
    # MORNING BRIEFING (12:01 AM )
    @staticmethod
    async def generate_morning_briefing(target_date: Optional[date] = None) -> Dict:
        db: Session = supabase_admin.get_db()

        if not target_date:
            target_date = date.today() - timedelta(days=1)

        logger.info(f"Generating morning briefing for {target_date}")

        users = db.execute(
            text("""
                SELECT DISTINCT user_id
                FROM biomarkers
                WHERE DATE(recorded_at) = :target_date
            """),
            {"target_date": target_date}
        ).fetchall()

        summaries_created = 0
        users_with_alerts = 0

        for row in users:
            result = await HealthSummaryService.calculate_daily_summary(
                user_id=row.user_id,
                target_date=target_date,
                summary_type="morning_briefing"
            )

            summary = DailyHealthSummary(
                user_id=row.user_id,
                summary_date=target_date,
                summary_type="morning_briefing",
                summary_data=result["summary_data"],
                email_sent=False
            )

            db.add(summary)
            summaries_created += 1

            if result["has_critical_values"]:
                users_with_alerts += 1

        db.commit()
        db.close()

        return {
            "total_users_processed": len(users),
            "summaries_created": summaries_created,
            "users_with_alerts": users_with_alerts
        }

    # EVENING SUMMARY (11:59 PM)
    @staticmethod
    async def generate_evening_summary(target_date: Optional[date] = None) -> Dict:
        db: Session = supabase_admin.get_db()

        if not target_date:
            target_date = date.today()

        logger.info(f"Generating evening summary for {target_date}")

        users = db.execute(
            text("""
                SELECT DISTINCT user_id
                FROM biomarkers
                WHERE DATE(recorded_at) = :target_date
            """),
            {"target_date": target_date}
        ).fetchall()

        summaries_created = 0

        for row in users:
            result = await HealthSummaryService.calculate_daily_summary(
                user_id=row.user_id,
                target_date=target_date,
                summary_type="evening_summary"
            )

            summary = DailyHealthSummary(
                user_id=row.user_id,
                summary_date=target_date,
                summary_type="evening_summary",
                summary_data=result["summary_data"],
                email_sent=True  # no email for evening summary
            )

            db.add(summary)
            summaries_created += 1

        db.commit()
        db.close()

        return {
            "total_users_processed": len(users),
            "summaries_created": summaries_created
        }

    # CORE DAILY SUMMARY CALCULATION
    @staticmethod
    async def calculate_daily_summary(
        user_id: str,
        target_date: date,
        summary_type: str
    ) -> Dict:
        db: Session = supabase_admin.get_db()

        biomarker_rows = db.execute(
            text("""
                SELECT biomarker_type, value
                FROM biomarkers
                WHERE user_id = :user_id
                  AND DATE(recorded_at) = :target_date
            """),
            {"user_id": user_id, "target_date": target_date}
        ).fetchall()

        if not biomarker_rows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No biomarker data for this date"
            )

        grouped = {}
        for row in biomarker_rows:
            grouped.setdefault(row.biomarker_type, []).append(row.value)

        biomarkers_summary = {}
        has_critical = False
        has_concerning = False
        insights = []

        for biomarker, values in grouped.items():
            avg_val = sum(values) / len(values)

            range_row = db.execute(
                text("""
                    SELECT *
                    FROM biomarker_ranges
                    WHERE biomarker_type = :type
                """),
                {"type": biomarker}
            ).fetchone()

            status_label = "normal"

            if range_row:
                if avg_val < range_row.critical_low or avg_val > range_row.critical_high:
                    status_label = "critical"
                    has_critical = True
                elif avg_val < range_row.min_normal or avg_val > range_row.max_normal:
                    status_label = "concerning"
                    has_concerning = True
                elif range_row.min_optimal <= avg_val <= range_row.max_optimal:
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

        db.close()

        return {
            "summary_data": summary_data,
            "total_readings": len(biomarker_rows),
            "biomarkers_tracked": list(grouped.keys()),
            "has_critical_values": has_critical,
            "has_concerning_values": has_concerning,
            "overall_status": overall_status
        }

    # SEND MORNING BRIEFING EMAILS
    @staticmethod
    async def send_morning_briefing_emails() -> int:
        db: Session = supabase_admin.get_db()

        summaries = db.query(DailyHealthSummary).filter(
            and_(
                DailyHealthSummary.summary_type == "morning_briefing",
                DailyHealthSummary.email_sent == False
            )
        ).all()

        sent_count = 0

        for summary in summaries:
            # Email handled elsewhere
            summary.email_sent = True
            summary.email_sent_at = datetime.now(timezone.utc)
            sent_count += 1

        db.commit()
        db.close()

        return sent_count

    # GET USER SUMMARY (SINGLE)
    @staticmethod
    async def get_user_summary(
        user_id: str,
        summary_date: date,
        summary_type: Optional[str] = None
    ) -> Optional[Dict]:
        db: Session = supabase_admin.get_db()

        query = db.query(DailyHealthSummary).filter(
            DailyHealthSummary.user_id == user_id,
            DailyHealthSummary.summary_date == summary_date
        )

        if summary_type:
            query = query.filter(DailyHealthSummary.summary_type == summary_type)

        result = query.order_by(DailyHealthSummary.created_at.desc()).first()
        db.close()

        return result.summary_data if result else None

    # GET USER SUMMARIES (RANGE)
    @staticmethod
    async def get_user_summaries_range(
        user_id: str,
        start_date: date,
        end_date: date,
        summary_type: Optional[str] = None
    ) -> List[Dict]:
        db: Session = supabase_admin.get_db()

        query = db.query(DailyHealthSummary).filter(
            DailyHealthSummary.user_id == user_id,
            DailyHealthSummary.summary_date.between(start_date, end_date)
        )

        if summary_type:
            query = query.filter(DailyHealthSummary.summary_type == summary_type)

        results = query.order_by(DailyHealthSummary.summary_date.desc()).all()
        db.close()

        return [r.summary_data for r in results]

    # REGENERATE SUMMARY (MANUAL)
    @staticmethod
    async def regenerate_summary(
        user_id: str,
        target_date: date,
        summary_type: str
    ) -> Dict:
        db: Session = supabase_admin.get_db()

        db.query(DailyHealthSummary).filter(
            DailyHealthSummary.user_id == user_id,
            DailyHealthSummary.summary_date == target_date,
            DailyHealthSummary.summary_type == summary_type
        ).delete()

        db.commit()

        result = await HealthSummaryService.calculate_daily_summary(
            user_id=user_id,
            target_date=target_date,
            summary_type=summary_type
        )

        summary = DailyHealthSummary(
            user_id=user_id,
            summary_date=target_date,
            summary_type=summary_type,
            summary_data=result["summary_data"],
            email_sent=False
        )

        db.add(summary)
        db.commit()
        db.refresh(summary)
        db.close()

        return summary.summary_data


# Singleton
health_summary_service = HealthSummaryService()
