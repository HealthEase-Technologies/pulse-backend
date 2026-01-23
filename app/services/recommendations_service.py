from app.config.database import supabase_admin
from app.services.gemini_service import gemini_service, GeminiService
from app.schemas.recommendations import CATEGORY_DISPLAY_MAP, PRIORITY_DISPLAY_MAP
from fastapi import HTTPException, status
from typing import Dict, Optional, List
from datetime import date, datetime, timezone, timedelta
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# HELPER FUNCTIONS FOR COMPUTED FIELDS
# =============================================================================

def _parse_datetime(dt_str: str) -> Optional[datetime]:
    """Parse datetime string with various formats."""
    if not dt_str:
        return None
    try:
        # Replace Z with +00:00 for timezone
        dt_str = dt_str.replace("Z", "+00:00")
        return datetime.fromisoformat(dt_str)
    except ValueError:
        # Try parsing with dateutil for non-standard formats
        try:
            from dateutil import parser
            return parser.isoparse(dt_str)
        except Exception:
            pass
        # Fallback: try stripping microseconds variations
        try:
            # Handle cases like 2026-01-23T12:56:52.04703+00:00
            if "." in dt_str and "+" in dt_str:
                base, tz = dt_str.rsplit("+", 1)
                if "." in base:
                    date_part, micro = base.rsplit(".", 1)
                    # Pad or truncate microseconds to 6 digits
                    micro = micro[:6].ljust(6, "0")
                    dt_str = f"{date_part}.{micro}+{tz}"
            return datetime.fromisoformat(dt_str)
        except Exception:
            return None


def enrich_recommendation(rec: Dict) -> Dict:
    """
    Enrich a recommendation with computed display fields.

    Adds:
        - category_display: Display info for the category (icon, color, etc.)
        - priority_display: Display info for the priority
        - is_new: True if created in last 24 hours
        - is_expiring_soon: True if expiring in next 48 hours
    """
    # Category display
    category = rec.get("category")
    if category and category in CATEGORY_DISPLAY_MAP:
        rec["category_display"] = CATEGORY_DISPLAY_MAP[category].model_dump()

    # Priority display
    priority = rec.get("priority")
    if priority and priority in PRIORITY_DISPLAY_MAP:
        rec["priority_display"] = PRIORITY_DISPLAY_MAP[priority]

    # Is new (created in last 24 hours)
    created_at = rec.get("created_at")
    if created_at:
        if isinstance(created_at, str):
            created_dt = _parse_datetime(created_at)
        else:
            created_dt = created_at
        if created_dt:
            rec["is_new"] = (datetime.now(timezone.utc) - created_dt) < timedelta(hours=24)

    # Is expiring soon (within next 48 hours)
    valid_until = rec.get("valid_until")
    if valid_until:
        if isinstance(valid_until, str):
            valid_until_dt = _parse_datetime(valid_until)
        else:
            valid_until_dt = valid_until
        if valid_until_dt:
            time_remaining = valid_until_dt - datetime.now(timezone.utc)
            rec["is_expiring_soon"] = timedelta(0) < time_remaining < timedelta(hours=48)

    return rec


def calculate_list_stats(recommendations: List[Dict]) -> Dict:
    """
    Calculate summary statistics for a list of recommendations.

    Returns:
        Dict with by_category, by_priority, by_status counts,
        urgent_count, new_count, in_progress_count
    """
    by_category = {}
    by_priority = {}
    by_status = {}
    urgent_count = 0
    new_count = 0
    in_progress_count = 0

    for rec in recommendations:
        # Count by category
        cat = rec.get("category")
        if cat:
            by_category[cat] = by_category.get(cat, 0) + 1

        # Count by priority
        pri = rec.get("priority")
        if pri:
            by_priority[pri] = by_priority.get(pri, 0) + 1
            if pri == "urgent":
                urgent_count += 1

        # Count by status
        stat = rec.get("status")
        if stat:
            by_status[stat] = by_status.get(stat, 0) + 1
            if stat == "in_progress":
                in_progress_count += 1

        # Count new
        if rec.get("is_new"):
            new_count += 1

    return {
        "by_category": by_category,
        "by_priority": by_priority,
        "by_status": by_status,
        "urgent_count": urgent_count,
        "new_count": new_count,
        "in_progress_count": in_progress_count
    }

# =============================================================================
# DATABASE TABLE: ai_recommendations
# =============================================================================
# Columns:
#   - id: UUID (PK)
#   - user_id: UUID (FK -> users.id)
#
#   -- Core content
#   - category: VARCHAR(50) - 'nutrition', 'exercise', 'sleep', 'lifestyle', 'medical', 'mental_health', 'hydration', 'medication'
#   - title: VARCHAR(255)
#   - description: TEXT
#   - detailed_explanation: TEXT
#
#   -- Why this recommendation
#   - reasoning: TEXT
#   - expected_benefit: TEXT
#   - time_to_results: VARCHAR(50)
#
#   -- Action details
#   - action_steps: JSONB - [{step_number, instruction, tip}]
#   - frequency: VARCHAR(20) - 'once', 'daily', 'weekly', 'as_needed', 'ongoing'
#   - duration: VARCHAR(50)
#   - best_time: VARCHAR(50)
#   - effort_minutes_per_day: INTEGER
#
#   -- Priority & difficulty
#   - priority: VARCHAR(20) - 'urgent', 'high', 'medium', 'low'
#   - difficulty: VARCHAR(20) - 'easy', 'moderate', 'challenging'
#
#   -- Health context
#   - related_metrics: JSONB - [{biomarker_type, target_improvement}]
#   - related_goal: TEXT
#   - contraindications: JSONB - [string]
#   - health_context: JSONB - snapshot of health data used for generation
#
#   -- Safety
#   - requires_professional_consultation: BOOLEAN - default FALSE
#   - safety_warning: TEXT
#   - disclaimer: TEXT
#
#   -- AI metadata
#   - ai_model: VARCHAR(100) - default 'gemini-2.0-flash'
#   - confidence_score: DECIMAL(3,2) - 0.00 to 1.00
#
#   -- Status & interaction
#   - status: VARCHAR(20) - 'active', 'in_progress', 'completed', 'dismissed', 'expired', 'snoozed'
#   - user_feedback: VARCHAR(30) - 'helpful', 'not_helpful', 'already_doing', 'too_difficult', 'not_applicable', 'implemented'
#   - feedback_notes: TEXT
#   - difficulty_experienced: VARCHAR(20) - 'easy', 'moderate', 'challenging'
#   - progress_percentage: INTEGER - 0 to 100
#
#   -- Validity & timestamps
#   - valid_from: TIMESTAMP WITH TIME ZONE
#   - valid_until: TIMESTAMP WITH TIME ZONE
#   - snoozed_until: TIMESTAMP WITH TIME ZONE
#   - created_at: TIMESTAMP WITH TIME ZONE
#   - updated_at: TIMESTAMP WITH TIME ZONE
# =============================================================================


class RecommendationsService:
    """Service layer for AI-powered health recommendations"""

    # =========================================================================
    # GENERATE RECOMMENDATIONS
    # =========================================================================
    @staticmethod
    async def generate_recommendations_for_user(
        user_id: str,
        categories: Optional[List[str]] = None,
        force_regenerate: bool = False
    ) -> Dict:
        """
        Generate AI-powered health recommendations for a user.

        Args:
            user_id: The user's ID
            categories: Optional list of categories to generate for
            force_regenerate: If True, generate even if active recommendations exist

        Returns:
            Dict with generated_count, recommendations list, and message

        DB Operations:
            - SELECT from ai_recommendations WHERE user_id = ? AND status = 'active'
            - INSERT into ai_recommendations (user_id, category, title, description,
              priority, ai_model, confidence_score, reasoning, health_context,
              status, valid_from, valid_until, created_at, updated_at)
        """
        # TODO: Implement recommendation generation
        # Steps:
        # 1. Check if user has active recommendations (skip if force_regenerate=False)
        #    - Query: SELECT * FROM ai_recommendations WHERE user_id = ? AND status = 'active'
        # 2. Build health context using _build_health_context()
        # 3. Call gemini_service.generate_health_recommendations(health_context)
        # 4. Store recommendations in database using _store_recommendations()
        # 5. Return the generated recommendations
        try:
            # 1️⃣ Check for existing active recommendations (if not forcing regeneration)
            if not force_regenerate:
                existing_response = (
                    supabase_admin
                    .table("ai_recommendations")
                    .select("*")
                    .eq("user_id", user_id)
                    .eq("status", "active")
                    .execute()
                )

                if existing_response.data and len(existing_response.data) > 0:
                    return {
                        "generated_count": 0,
                        "recommendations": existing_response.data,
                        "message": "Active recommendations already exist"
                    }

            # 2️⃣ Build health context
            health_context = await RecommendationsService._build_health_context(user_id)

            # 3️⃣ Generate recommendations via Gemini
            recommendations = await gemini_service.generate_health_recommendations(
                health_context
            )

            # 4️⃣ Filter by categories if specified
            if categories:
                recommendations = [
                    rec for rec in recommendations
                    if rec.get("category") in categories
                ]

            # 5️⃣ Store recommendations
            stored_recommendations = await RecommendationsService._store_recommendations(
                user_id,
                recommendations,
                health_context
            )

            # 6️⃣ Return response
            return {
                "generated_count": len(stored_recommendations),
                "recommendations": stored_recommendations,
                "message": f"Generated {len(stored_recommendations)} new recommendations"
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error generating recommendations for user {user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate recommendations"
            )

                        
    @staticmethod
    async def generate_daily_recommendations() -> Dict:
        """
        Cron job: Generate daily recommendations for all users with recent health data.

        Returns:
            Dict with total_users_processed and recommendations_generated counts

        DB Operations:
            - SELECT DISTINCT user_id FROM daily_health_summaries
              WHERE summary_date = yesterday
        """
        # TODO: Implement daily recommendation generation
        # Steps:
        # 1. Get all users who have health summaries from yesterday
        #    - Query: SELECT DISTINCT user_id FROM daily_health_summaries
        #             WHERE summary_date = (CURRENT_DATE - 1)
        # 2. For each user, call generate_recommendations_for_user()
        # 3. Log results and return summary
        try:
            # 1️⃣ Fetch users with health summaries from yesterday
            yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date()
            users_response = (
                supabase_admin
                .table("daily_health_summaries")
                .select("user_id")
                .eq("summary_date", yesterday.isoformat())
                .execute()
            )

            # Get unique user_ids
            user_ids = list(set(record["user_id"] for record in users_response.data))

            total_users_processed = 0
            recommendations_generated = 0

            # 2️⃣ Generate recommendations for each user
            for user_id in user_ids:
                try:
                    result = await RecommendationsService.generate_recommendations_for_user(
                        user_id,
                        force_regenerate=False
                    )
                    if result and result.get("recommendations"):
                        recommendations_generated += len(result["recommendations"])
                    total_users_processed += 1
                except Exception as user_error:
                    logger.warning(f"Failed to generate recommendations for user {user_id}: {str(user_error)}")
                    continue

            # 3️⃣ Return summary
            return {
                "total_users_processed": total_users_processed,
                "recommendations_generated": recommendations_generated
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error generating daily recommendations: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate daily recommendations"
            )

    # =========================================================================
    # GET RECOMMENDATIONS
    # =========================================================================
    @staticmethod
    async def get_active_recommendations(
        user_id: str,
        category: Optional[str] = None
    ) -> List[Dict]:
        """
        Get active recommendations for a user.

        Args:
            user_id: The user's ID
            category: Optional category filter

        Returns:
            List of active recommendation records

        DB Query:
            SELECT * FROM ai_recommendations
            WHERE user_id = ?
              AND status IN ('active', 'in_progress')
              AND (valid_until IS NULL OR valid_until > NOW())
            ORDER BY
              CASE priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
              created_at DESC
        """
        # TODO: Implement fetching active recommendations
        # Steps:
        # 1. Query ai_recommendations table for user_id
        # 2. Filter by status IN ('active', 'in_progress') and valid_until > now (or null)
        # 3. Optionally filter by category column
        # 4. Order by priority (urgent first, then high, medium, low) and created_at desc
        # 5. Return list of recommendations
        try:
            query = (
                supabase_admin
                .table("ai_recommendations")
                .select("*")
                .eq("user_id", user_id)
                .in_("status", ["active", "in_progress"])
                .or_("valid_until.gt." + datetime.now(timezone.utc).isoformat() + ",valid_until.is.null")
            )

            if category:
                query = query.eq("category", category)

            response = query.execute()

            priority_order = {
                "urgent": 0,
                "high": 1,
                "medium": 2,
                "low": 3
            }

            sorted_data = sorted(
                response.data,
                key=lambda x: (
                    priority_order.get(x.get("priority"), 3),  # priority ASC
                    -datetime.fromisoformat(x["created_at"]).timestamp()  # created_at DESC
                )
            )

            return sorted_data
        except Exception as e:  
            logger.error(f"Error fetching active recommendations for user {user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch active recommendations"
            )
            

        

    @staticmethod
    async def get_recommendation_history(
        user_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict:
        """
        Get recommendation history for a user.

        Args:
            user_id: The user's ID
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Max records to return
            offset: Pagination offset

        Returns:
            Dict with recommendations list and total_count

        DB Query:
            SELECT * FROM ai_recommendations
            WHERE user_id = ?
              AND created_at >= start_date
              AND created_at <= end_date
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        # TODO: Implement recommendation history
        # Steps:
        # 1. Query ai_recommendations table for user_id
        # 2. Apply date filters on created_at column if provided
        # 3. Order by created_at desc
        # 4. Apply pagination (limit, offset)
        # 5. Get total count for pagination
        # 6. Return recommendations and total_count
        try:
            query = (
                supabase_admin
                .table("ai_recommendations")
                .select("*", count="exact")
                .eq("user_id", user_id)
            )

            if start_date:
                query = query.gte("created_at", start_date.isoformat())
            if end_date:
                query = query.lte("created_at", end_date.isoformat())

            query = query.order("created_at", desc=True).range(offset, offset + limit - 1)

            response = query.execute()

            return {
                "recommendations": response.data,
                "total_count": response.count or len(response.data)
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching recommendation history for user {user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch recommendation history"
            )

    @staticmethod
    async def get_recommendation_by_id(
        recommendation_id: str,
        user_id: str
    ) -> Optional[Dict]:
        """
        Get a specific recommendation by ID.

        Args:
            recommendation_id: The recommendation's ID
            user_id: The user's ID (for authorization)

        Returns:
            Recommendation record or None if not found

        DB Query:
            SELECT * FROM ai_recommendations
            WHERE id = ? AND user_id = ?
        """
        # TODO: Implement get by ID
        # Steps:
        # 1. Query ai_recommendations table by id column
        # 2. Verify user_id matches
        # 3. Return recommendation or None
        try:
            response = (
                supabase_admin
                .table("ai_recommendations")
                .select("*")
                .eq("id", recommendation_id)
                .eq("user_id", user_id)
                .execute()
            )

            if not response.data or len(response.data) == 0:
                return None

            return response.data[0]
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching recommendation {recommendation_id} for user {user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch recommendation"
            )

    # =========================================================================
    # UPDATE RECOMMENDATIONS
    # =========================================================================
    @staticmethod
    async def submit_feedback(
        recommendation_id: str,
        user_id: str,
        feedback: str,
        notes: Optional[str] = None,
        difficulty_experienced: Optional[str] = None
    ) -> Dict:
        """
        Submit user feedback for a recommendation.

        Args:
            recommendation_id: The recommendation's ID
            user_id: The user's ID
            feedback: Feedback value ('helpful', 'not_helpful', 'already_doing', 'too_difficult', 'not_applicable', 'implemented')
            notes: Optional feedback notes
            difficulty_experienced: Optional difficulty ('easy', 'moderate', 'challenging')

        Returns:
            Updated recommendation record

        DB Update:
            UPDATE ai_recommendations
            SET user_feedback = ?,
                feedback_notes = ?,
                difficulty_experienced = ?,
                status = CASE WHEN ? = 'implemented' THEN 'completed' ELSE status END,
                updated_at = NOW()
            WHERE id = ? AND user_id = ?
        """
        # TODO: Implement feedback submission
        # Steps:
        # 1. Verify recommendation exists and belongs to user
        # 2. Update user_feedback, feedback_notes, and difficulty_experienced columns
        # 3. If feedback is 'implemented', update status column to 'completed'
        # 4. Update updated_at timestamp
        # 5. Return updated recommendation
        try:
            # Verify recommendation exists and belongs to user
            existing_response = (
                supabase_admin
                .table("ai_recommendations")
                .select("*")
                .eq("id", recommendation_id)
                .eq("user_id", user_id)
                .execute()
            )

            if not existing_response.data or len(existing_response.data) == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Recommendation not found"
                )

            update_data = {
                "user_feedback": feedback,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            if notes:
                update_data["feedback_notes"] = notes
            if difficulty_experienced:
                update_data["difficulty_experienced"] = difficulty_experienced
            if feedback == "implemented":
                update_data["status"] = "completed"

            response = (
                supabase_admin
                .table("ai_recommendations")
                .update(update_data)
                .eq("id", recommendation_id)
                .eq("user_id", user_id)
                .execute()
            )

            return response.data[0] if response.data else existing_response.data[0]
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error submitting feedback for recommendation {recommendation_id} by user {user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to submit feedback"
            )

    @staticmethod
    async def dismiss_recommendation(
        recommendation_id: str,
        user_id: str
    ) -> Dict:
        """
        Dismiss a recommendation.

        Args:
            recommendation_id: The recommendation's ID
            user_id: The user's ID

        Returns:
            Updated recommendation record

        DB Update:
            UPDATE ai_recommendations
            SET status = 'dismissed', updated_at = NOW()
            WHERE id = ? AND user_id = ?
        """
        # TODO: Implement dismissal
        # Steps:
        # 1. Verify recommendation exists and belongs to user
        # 2. Update status column to 'dismissed'
        # 3. Update updated_at timestamp
        # 4. Return updated recommendation
        try:
            # Verify recommendation exists and belongs to user
            existing_response = (
                supabase_admin
                .table("ai_recommendations")
                .select("*")
                .eq("id", recommendation_id)
                .eq("user_id", user_id)
                .execute()
            )

            if not existing_response.data or len(existing_response.data) == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Recommendation not found"
                )

            response = (
                supabase_admin
                .table("ai_recommendations")
                .update({
                    "status": "dismissed",
                    "updated_at": datetime.now(timezone.utc).isoformat()
                })
                .eq("id", recommendation_id)
                .eq("user_id", user_id)
                .execute()
            )

            return response.data[0] if response.data else existing_response.data[0]
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error dismissing recommendation {recommendation_id} by user {user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to dismiss recommendation"
            )

    # =========================================================================
    # PROVIDER ACCESS
    # =========================================================================
    @staticmethod
    async def get_patient_recommendations_for_provider(
        provider_user_id: str,
        patient_user_id: str,
        status_filter: Optional[str] = None
    ) -> List[Dict]:
        """
        Provider gets a patient's recommendations.

        Business Rule: Provider must have an accepted connection with the patient.

        Args:
            provider_user_id: The provider's user ID
            patient_user_id: The patient's user ID
            status_filter: Optional status filter

        Returns:
            List of patient's recommendations

        DB Query:
            SELECT * FROM ai_recommendations
            WHERE user_id = patient_user_id
              AND status = ? (optional)
            ORDER BY created_at DESC
        """
        # TODO: Implement provider access to patient recommendations
        # Steps:
        # 1. Verify provider-patient connection using _verify_provider_patient_connection()
        # 2. Query ai_recommendations for patient_user_id
        # 3. Apply status filter if provided
        # 4. Return recommendations list
        try:
            # 1️⃣ Verify connection
            await RecommendationsService._verify_provider_patient_connection(
                provider_user_id,
                patient_user_id
            )

            # 2️⃣ Query recommendations
            query = (
                supabase_admin
                .table("ai_recommendations")
                .select("*")
                .eq("user_id", patient_user_id)
            )

            if status_filter:
                query = query.eq("status", status_filter)

            query = query.order("created_at", desc=True)

            response = query.execute()

            return response.data
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching recommendations for patient {patient_user_id} by provider {provider_user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch patient recommendations"
            )

    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    @staticmethod
    async def _build_health_context(user_id: str) -> Dict:
        """
        Build health context for AI recommendation generation.

        Args:
            user_id: The user's ID

        Returns:
            Dict containing patient profile, biomarkers, summaries, and trends

        Tables accessed:
            - patients: health_goals, health_restrictions, date_of_birth, height_cm, weight_kg
            - biomarkers: biomarker_type, value, recorded_at (last 7 days)
            - daily_health_summaries: summary_data, overall_status
            - goal_completions: status (for completion rate calculation)
        """
        # TODO: Implement health context building
        # Steps:
        # 1. Fetch patient profile from patients table:
        #    - SELECT health_goals, health_restrictions, date_of_birth, height_cm, weight_kg
        #      FROM patients WHERE user_id = ?
        # 2. Fetch recent biomarkers (last 7 days) from biomarkers table:
        #    - SELECT biomarker_type, value, recorded_at FROM biomarkers
        #      WHERE user_id = ? AND recorded_at >= (NOW() - 7 days)
        # 3. Fetch latest health summary from daily_health_summaries:
        #    - SELECT summary_data, overall_status FROM daily_health_summaries
        #      WHERE user_id = ? ORDER BY summary_date DESC LIMIT 1
        # 4. Calculate goal completion rate from goal_completions:
        #    - SELECT COUNT(*) FILTER (WHERE status = 'completed') / COUNT(*)
        #      FROM goal_completions WHERE user_id = ? AND completion_date >= (NOW() - 7 days)
        # 5. Calculate trends for each biomarker (improving, stable, declining)
        # 6. Return structured health context dict
        try:
            health_context = {}

            # 1️⃣ Fetch patient profile
            profile_response = (
                supabase_admin
                .table("patients")
                .select("health_goals, health_restrictions, date_of_birth, height_cm, weight_kg")
                .eq("user_id", user_id)
                .execute()
            )

            if not profile_response.data or len(profile_response.data) == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Patient profile not found"
                )

            patient_data = profile_response.data[0]

            # Calculate age from date_of_birth
            age = None
            if patient_data.get("date_of_birth"):
                dob_str = patient_data["date_of_birth"]
                try:
                    # Handle date-only strings (YYYY-MM-DD)
                    if "T" not in dob_str and len(dob_str) == 10:
                        dob_date = date.fromisoformat(dob_str)
                    else:
                        # Handle ISO datetime strings
                        dob_dt = datetime.fromisoformat(dob_str.replace("Z", "+00:00"))
                        dob_date = dob_dt.date()

                    today = date.today()
                    age = today.year - dob_date.year - ((today.month, today.day) < (dob_date.month, dob_date.day))
                except (ValueError, AttributeError) as e:
                    logger.warning(f"Could not parse date_of_birth '{dob_str}': {e}")
                    age = None

            # Calculate BMI if height and weight available
            bmi = None
            height_cm = patient_data.get("height_cm")
            weight_kg = patient_data.get("weight_kg")
            if height_cm and weight_kg:
                height_m = height_cm / 100
                bmi = round(weight_kg / (height_m ** 2), 1)

            health_context["patient_profile"] = {
                "age": age,
                "height_cm": height_cm,
                "weight_kg": weight_kg,
                "bmi": bmi,
                "health_goals": patient_data.get("health_goals") or [],
                "health_restrictions": patient_data.get("health_restrictions") or []
            }

            # 2️⃣ Fetch recent biomarkers (last 7 days)
            seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            biomarkers_response = (
                supabase_admin
                .table("biomarkers")
                .select("biomarker_type, value, unit, recorded_at")
                .eq("user_id", user_id)
                .gte("recorded_at", seven_days_ago)
                .order("recorded_at", desc=True)
                .execute()
            )

            # Process biomarkers into summary format
            biomarkers_by_type = {}
            for b in biomarkers_response.data:
                b_type = b["biomarker_type"]
                if b_type not in biomarkers_by_type:
                    biomarkers_by_type[b_type] = []
                biomarkers_by_type[b_type].append(b)

            biomarkers_summary = []
            for b_type, readings in biomarkers_by_type.items():
                values = [r["value"] for r in readings]
                unit = readings[0].get("unit", "")
                biomarkers_summary.append({
                    "biomarker_type": b_type,
                    "current_avg": round(sum(values) / len(values), 1),
                    "min_value": min(values),
                    "max_value": max(values),
                    "unit": unit,
                    "status": "normal",  # Would be determined by comparing with ranges
                    "trend": "stable",   # Would be calculated from historical data
                    "optimal_range": "N/A"
                })

            health_context["biomarkers"] = biomarkers_summary

            # 3️⃣ Fetch latest health summary
            summary_response = (
                supabase_admin
                .table("daily_health_summaries")
                .select("summary_data, overall_status")
                .eq("user_id", user_id)
                .order("summary_date", desc=True)
                .limit(1)
                .execute()
            )

            if summary_response.data and len(summary_response.data) > 0:
                health_context["latest_summary"] = summary_response.data[0].get("summary_data")
                health_context["overall_health_status"] = summary_response.data[0].get("overall_status", "unknown")
            else:
                health_context["latest_summary"] = None
                health_context["overall_health_status"] = "unknown"

            # 4️⃣ Calculate goal completion rate
            completion_response = (
                supabase_admin
                .table("goal_completions")
                .select("status")
                .eq("user_id", user_id)
                .gte("completion_date", seven_days_ago)
                .execute()
            )

            total_goals = len(completion_response.data) if completion_response.data else 0
            completed_goals = sum(1 for record in completion_response.data if record.get("status") == "completed")
            completion_rate = (completed_goals / total_goals) if total_goals > 0 else 0.0

            health_context["patient_profile"]["goal_completion_rate_7d"] = completion_rate

            # 5️⃣ Fetch active alerts (placeholder - adjust based on your alerts table)
            health_context["active_alerts"] = []
            health_context["recent_insights"] = []

            return health_context
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error building health context for user {user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to build health context"
            )

    @staticmethod
    async def _store_recommendations(
        user_id: str,
        recommendations: List[Dict],
        health_context: Dict
    ) -> List[Dict]:
        """
        Store generated recommendations in the database.

        Args:
            user_id: The user's ID
            recommendations: List of recommendation dicts from AI
            health_context: Health context used for generation

        Returns:
            List of stored recommendation records

        DB Insert:
            INSERT INTO ai_recommendations (
                user_id, category, title, description, detailed_explanation,
                reasoning, expected_benefit, time_to_results,
                action_steps, frequency, duration, best_time, effort_minutes_per_day,
                priority, difficulty,
                related_metrics, related_goal, contraindications, health_context,
                requires_professional_consultation, safety_warning, disclaimer,
                ai_model, confidence_score,
                status, valid_from, valid_until, created_at, updated_at
            ) VALUES (...)
        """
        try:
            now = datetime.now(timezone.utc)
            valid_until = now + timedelta(days=7)

            standard_disclaimer = (
                "This is a general wellness suggestion based on AI analysis. "
                "It is not a substitute for professional medical advice. "
                "Consult your healthcare provider for personalized medical guidance."
            )

            records_to_insert = []
            for rec in recommendations:
                # Convert action_steps from Pydantic model format if needed
                action_steps = rec.get("action_steps", [])
                if action_steps and hasattr(action_steps[0], "model_dump"):
                    action_steps = [step.model_dump() for step in action_steps]

                # Convert related_metrics from Pydantic model format if needed
                related_metrics = rec.get("related_metrics", [])
                if related_metrics and hasattr(related_metrics[0], "model_dump"):
                    related_metrics = [metric.model_dump() for metric in related_metrics]

                record = {
                    "user_id": user_id,
                    # Core content
                    "category": rec.get("category"),
                    "title": rec.get("title"),
                    "description": rec.get("description"),
                    "detailed_explanation": rec.get("detailed_explanation"),
                    # Why this recommendation
                    "reasoning": rec.get("reasoning"),
                    "expected_benefit": rec.get("expected_benefit"),
                    "time_to_results": rec.get("time_to_results"),
                    # Action details
                    "action_steps": action_steps,
                    "frequency": rec.get("frequency"),
                    "duration": rec.get("duration"),
                    "best_time": rec.get("best_time"),
                    "effort_minutes_per_day": rec.get("effort_minutes_per_day"),
                    # Priority & difficulty
                    "priority": rec.get("priority"),
                    "difficulty": rec.get("difficulty"),
                    # Health context
                    "related_metrics": related_metrics,
                    "related_goal": rec.get("related_goal"),
                    "contraindications": rec.get("contraindications"),
                    "health_context": health_context,
                    # Safety
                    "requires_professional_consultation": rec.get("requires_professional_consultation", False),
                    "safety_warning": rec.get("safety_warning"),
                    "disclaimer": standard_disclaimer,
                    # AI metadata
                    "ai_model": GeminiService.MODEL_NAME,
                    "confidence_score": rec.get("confidence_score"),
                    # Status & timestamps
                    "status": "active",
                    "valid_from": now.isoformat(),
                    "valid_until": valid_until.isoformat(),
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat()
                }
                records_to_insert.append(record)

            # Batch insert all recommendations
            if records_to_insert:
                response = (
                    supabase_admin
                    .table("ai_recommendations")
                    .insert(records_to_insert)
                    .execute()
                )
                return response.data

            return []

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error storing recommendations for user {user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to store recommendations"
            )

    @staticmethod
    async def _verify_provider_patient_connection(
        provider_user_id: str,
        patient_user_id: str
    ) -> None:
        """
        Verify that a provider has an accepted connection with a patient.

        Args:
            provider_user_id: The provider's user ID
            patient_user_id: The patient's user ID

        Raises:
            HTTPException: If connection is not found or not accepted

        Tables accessed:
            - providers: id (provider profile id)
            - patients: id (patient profile id)
            - patient_provider_connections: provider_id, patient_id, status
        """
        # TODO: Implement connection verification
        # Steps:
        # 1. Get provider's profile_id from providers table:
        #    - SELECT id FROM providers WHERE user_id = ?
        # 2. Get patient's profile_id from patients table:
        #    - SELECT id FROM patients WHERE user_id = ?
        # 3. Check patient_provider_connections for accepted connection:
        #    - SELECT status FROM patient_provider_connections
        #      WHERE provider_id = ? AND patient_id = ? AND status = 'accepted'
        # 4. Raise 403 if no accepted connection found
        try:
            # Get provider profile ID
            provider_response = (
                supabase_admin
                .table("providers")
                .select("id")
                .eq("user_id", provider_user_id)
                .execute()
            )

            if not provider_response.data or len(provider_response.data) == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Provider profile not found"
                )

            provider_id = provider_response.data[0]["id"]

            # Get patient profile ID
            patient_response = (
                supabase_admin
                .table("patients")
                .select("id")
                .eq("user_id", patient_user_id)
                .execute()
            )

            if not patient_response.data or len(patient_response.data) == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Patient profile not found"
                )

            patient_id = patient_response.data[0]["id"]

            # Check connection status
            connection_response = (
                supabase_admin
                .table("patient_provider_connections")
                .select("status")
                .eq("provider_id", provider_id)
                .eq("patient_id", patient_id)
                .eq("status", "accepted")
                .execute()
            )

            if not connection_response.data or len(connection_response.data) == 0:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No accepted connection between provider and patient"
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error verifying connection between provider {provider_user_id} and patient {patient_user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to verify provider-patient connection"
            )

    @staticmethod
    async def _expire_old_recommendations(user_id: str) -> int:
        """
        Mark expired recommendations as expired.

        Args:
            user_id: The user's ID

        Returns:
            Number of recommendations marked as expired

        DB Update:
            UPDATE ai_recommendations
            SET status = 'expired', updated_at = NOW()
            WHERE user_id = ?
              AND status IN ('active', 'in_progress')
              AND valid_until < NOW()
        """
        # TODO: Implement expiration logic
        # Steps:
        # 1. Query active/in_progress recommendations where valid_until < NOW()
        # 2. Update status column to 'expired'
        # 3. Update updated_at column
        # 4. Return count of updated records
        try:
            now = datetime.now(timezone.utc).isoformat()
            response = (
                supabase_admin
                .table("ai_recommendations")
                .update({
                    "status": "expired",
                    "updated_at": now
                })
                .eq("user_id", user_id)
                .in_("status", ["active", "in_progress"])
                .lt("valid_until", now)
                .execute()
            )

            return len(response.data) if response.data else 0
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error expiring recommendations for user {user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to expire old recommendations"
            )
        

    @staticmethod
    async def get_recommendations_for_email(user_id: str, limit: int = 3) -> List[Dict]:
        """
        Get top recommendations to include in morning briefing email.

        Args:
            user_id: The user's ID
            limit: Max recommendations to return (default 3)

        Returns:
            List of recommendation dicts for email template:
                - title: str
                - description: str
                - category: str
                - priority: str

        DB Query:
            SELECT title, description, category, priority
            FROM ai_recommendations
            WHERE user_id = ?
              AND status IN ('active', 'in_progress')
              AND (valid_until IS NULL OR valid_until > NOW())
            ORDER BY
              CASE priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
              created_at DESC
            LIMIT ?
        """
        # TODO: Implement email recommendations fetching
        # Steps:
        # 1. Query ai_recommendations for user
        # 2. Filter: status IN ('active', 'in_progress'), valid_until > NOW() or NULL
        # 3. Order by priority (urgent first, then high, medium, low), then created_at desc
        # 4. Limit to specified count
        # 5. Return only: title, description, category, priority columns
        try:
            now = datetime.now(timezone.utc).isoformat()
            query = (
                supabase_admin
                .table("ai_recommendations")
                .select("title, description, category, priority")
                .eq("user_id", user_id)
                .in_("status", ["active", "in_progress"])
                .or_(f"valid_until.gt.{now},valid_until.is.null")
                .order("created_at", desc=True)
                .limit(limit * 2)  # Fetch more to allow for priority sorting
            )

            response = query.execute()

            if not response.data:
                return []

            # Sort by priority in Python since priority ordering by string isn't reliable
            priority_order = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
            sorted_data = sorted(
                response.data,
                key=lambda x: priority_order.get(x.get("priority"), 3)
            )

            return sorted_data[:limit]
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching email recommendations for user {user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch email recommendations"
            )


# Singleton instance
recommendations_service = RecommendationsService()
