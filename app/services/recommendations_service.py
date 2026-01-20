from app.config.database import supabase_admin
from fastapi import HTTPException, status
from typing import Dict, Optional, List
from datetime import date, datetime, timezone, timedelta
import logging

logger = logging.getLogger(__name__)

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
            # if force_regenerate is False, check for existing active recommendations
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

                if existing_response.error:
                    raise Exception(existing_response.error)

                if existing_response.data and len(existing_response.data) > 0:
                    return existing_response.data

            # 2️⃣ Build health context
            health_context = await RecommendationsService._build_health_context(user_id)

            # 3️⃣ Generate recommendations via Gemini
            recommendations = await gemini_service.generate_health_recommendations(
                health_context,
                categories
            )
            # 4️⃣ Store recommendations
            stored_recommendations = await RecommendationsService._store_recommendations(
                user_id,
                recommendations,
                health_context
            )

            # 5️⃣ Return response
            return stored_recommendations

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
                .select("user_id", distinct=True)
                .eq("summary_date", yesterday.isoformat())
                .execute()
            )

            if users_response.error:
                raise Exception(users_response.error)

            user_ids = [record["user_id"] for record in users_response.data]

            total_users_processed = 0
            recommendations_generated = 0

            # 2️⃣ Generate recommendations for each user
            for user_id in user_ids:
                recs = await RecommendationsService.generate_recommendations_for_user(
                    user_id,
                    force_regenerate=False
                )
                if recs:
                    recommendations_generated += len(recs)
                total_users_processed += 1

            # 3️⃣ Return summary
            return {
                "total_users_processed": total_users_processed,
                "recommendations_generated": recommendations_generated
            }
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

            response = query.order("created_at", ascending=False).execute()
            from datetime import datetime

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

            query = query.order("created_at", ascending=False).limit(limit).offset(offset)

            response = query.execute()

            if response.error:
                raise Exception(response.error)

            return {
                "recommendations": response.data,
                "total_count": response.count or 0
            }
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
                .single()
                .execute()
            )

            if response.error:
                if "No rows found" in str(response.error):
                    return None
                raise Exception(response.error)

            return response.data
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
            query= supabase_admin.table("ai_recommendations").select("*").eq("id", recommendation_id).eq("user_id", user_id).single()
            existing_response = query.execute()
            if existing_response.error:
                raise Exception(existing_response.error)
            if not existing_response.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Recommendation not found"
                )
            
            update_data = {
                "user_feedback": feedback,
                "feedback_notes": notes,
                "difficulty_experienced": difficulty_experienced,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            if feedback == "implemented":
                update_data["status"] = "completed"

            response = (
                supabase_admin
                .table("ai_recommendations")
                .update(update_data)
                .eq("id", recommendation_id)
                .eq("user_id", user_id)
                .single()
                .execute()
            )

            if response.error:
                raise Exception(response.error)

            return response.data
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
            query= supabase_admin.table("ai_recommendations").select("*").eq("id", recommendation_id).eq("user_id", user_id).single()
            existing_response = query.execute()
            if existing_response.error:
                raise Exception(existing_response.error)
            if not existing_response.data:
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
                .single()
                .execute()
            )

            if response.error:
                raise Exception(response.error)

            return response.data
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

            query = query.order("created_at", ascending=False)

            response = query.execute()

            if response.error:
                raise Exception(response.error)

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
                .single()
                .execute()
            )

            if profile_response.error:
                raise Exception(profile_response.error)

            health_context["patient_profile"] = profile_response.data

            # 2️⃣ Fetch recent biomarkers
            seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            biomarkers_response = (
                supabase_admin
                .table("biomarkers")
                .select("biomarker_type, value, recorded_at")
                .eq("user_id", user_id)
                .gte("recorded_at", seven_days_ago)
                .execute()
            )

            if biomarkers_response.error:
                raise Exception(biomarkers_response.error)

            health_context["recent_biomarkers"] = biomarkers_response.data

            # 3️⃣ Fetch latest health summary
            summary_response = (
                supabase_admin
                .table("daily_health_summaries")
                .select("summary_data, overall_status")
                .eq("user_id", user_id)
                .order("summary_date", ascending=False)
                .limit(1)
                .single()
                .execute()
            )

            if summary_response.error:
                raise Exception(summary_response.error)

            health_context["latest_health_summary"] = summary_response.data

            # 4️⃣ Calculate goal completion rate
            completion_response = (
                supabase_admin
                .table("goal_completions")
                .select("status", count="exact")
                .eq("user_id", user_id)
                .gte("completion_date", seven_days_ago)
                .execute()
            )

            if completion_response.error:
                raise Exception(completion_response.error)

            total_goals = completion_response.count or 0
            completed_goals = sum(1 for record in completion_response.data if record["status"] == "completed")
            completion_rate = (completed_goals / total_goals) if total_goals > 0 else 0.0

            health_context["goal_completion_rate"] = completion_rate
            
            # TODO 
            #DO THIS PART !!!!!

            # 5️⃣ Calculate trends for each biomarker (placeholder logic)
            trends = {}
            for biomarker in health_context["recent_biomarkers"]:
                biomarker_type = biomarker["biomarker_type"]
                # Placeholder: In real implementation, analyze historical data for trend
                trends[biomarker_type] = "stable"  # or "improving", "declining"
            
            health_context["biomarker_trends"] = trends
            return health_context
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
        # TODO: Implement recommendation storage
        # Steps:
        # 1. For each recommendation, create record with columns:
        #    - user_id: from parameter
        #    -- Core content
        #    - category: from AI response
        #    - title: from AI response
        #    - description: from AI response
        #    - detailed_explanation: from AI response
        #    -- Why this recommendation
        #    - reasoning: from AI response
        #    - expected_benefit: from AI response
        #    - time_to_results: from AI response
        #    -- Action details
        #    - action_steps: from AI response (JSONB)
        #    - frequency: from AI response
        #    - duration: from AI response
        #    - best_time: from AI response
        #    - effort_minutes_per_day: from AI response
        #    -- Priority & difficulty
        #    - priority: from AI response
        #    - difficulty: from AI response
        #    -- Health context
        #    - related_metrics: from AI response (JSONB)
        #    - related_goal: from AI response
        #    - contraindications: from AI response (JSONB)
        #    - health_context: snapshot (JSONB)
        #    -- Safety
        #    - requires_professional_consultation: from AI response
        #    - safety_warning: from AI response
        #    - disclaimer: standard disclaimer text
        #    -- AI metadata
        #    - ai_model: 'gemini-2.0-flash'
        #    - confidence_score: from AI response
        #    -- Status & timestamps
        #    - status: 'active'
        #    - valid_from: NOW()
        #    - valid_until: NOW() + 7 days
        #    - created_at: NOW()
        #    - updated_at: NOW()
        # 2. Insert into ai_recommendations table
        # 3. Return inserted records with all columns
        pass

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
                .single()
                .execute()
            )

            if provider_response.error:
                raise Exception(provider_response.error)

            if not provider_response.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Provider profile not found"
                )

            provider_id = provider_response.data["id"]

            # Get patient profile ID
            patient_response = (
                supabase_admin
                .table("patients")
                .select("id")
                .eq("user_id", patient_user_id)
                .single()
                .execute()
            )

            if patient_response.error:
                raise Exception(patient_response.error)

            if not patient_response.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Patient profile not found"
                )

            patient_id = patient_response.data["id"]

            # Check connection status
            connection_response = (
                supabase_admin
                .table("patient_provider_connections")
                .select("status")
                .eq("provider_id", provider_id)
                .eq("patient_id", patient_id)
                .eq("status", "accepted")
                .single()
                .execute()
            )

            if connection_response.error or not connection_response.data:
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
            response = (
                supabase_admin
                .table("ai_recommendations")
                .update({
                    "status": "expired",
                    "updated_at": datetime.now(timezone.utc).isoformat()
                })
                .eq("user_id", user_id)
                .in_("status", ["active", "in_progress"])
                .lt("valid_until", datetime.now(timezone.utc).isoformat())
                .execute()
            )

            if response.error:
                raise Exception(response.error)

            return response.count or 0
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
            query = (
                supabase_admin
                .table("ai_recommendations")
                .select("title, description, category, priority")
                .eq("user_id", user_id)
                .in_("status", ["active", "in_progress"])
                .or_("valid_until.gt." + datetime.now(timezone.utc).isoformat() + ",valid_until.is.null")
            )

            query = query.order(
                "priority", #CHECK : priority is varchar 
                ascending=True,
                nulls="last",
                foreign_table=None
            ).order("created_at", ascending=False).limit(limit)

            response = query.execute()

            if response.error:
                raise Exception(response.error)

            return response.data
        except Exception as e:
            logger.error(f"Error fetching email recommendations for user {user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch email recommendations"
            )


# Singleton instance
recommendations_service = RecommendationsService()
