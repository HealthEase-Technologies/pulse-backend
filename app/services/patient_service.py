from app.config.database import supabase_admin
from fastapi import HTTPException, status
from typing import Dict, Optional, List
from datetime import datetime, timezone, date, timedelta


class PatientService:
    """Service layer for patient-related business logic"""

    @staticmethod
    async def get_patient_profile(user_id: str) -> Optional[Dict]:
        """
        Get patient profile data
        Uses admin client to bypass RLS

        Args:
            user_id: The user's ID

        Returns:
            Patient profile data or None if not found
        """
        try:
            result = supabase_admin.table("patients").select("*").eq(
                "user_id", user_id
            ).execute()

            if not result.data:
                return None

            return result.data[0]

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch patient profile: {str(e)}"
            )

    @staticmethod
    async def complete_onboarding(user_id: str, onboarding_data: Dict) -> Dict:
        """
        Complete patient onboarding by updating profile with health information

        Args:
            user_id: The user's ID
            onboarding_data: Dictionary containing onboarding information
                - date_of_birth: Date of birth (YYYY-MM-DD)
                - height_cm: Height in centimeters
                - weight_kg: Weight in kilograms
                - health_goals: List of goal objects with structure [{"goal": "...", "frequency": "..."}]
                - health_restrictions: List of health restrictions
                - reminder_frequency: Frequency for reminders (daily/weekly/monthly/none)
                - emergency_contacts: List of up to 3 emergency contacts

        Returns:
            Updated patient profile
        """
        try:
            # Check if patient profile exists
            existing_profile = await PatientService.get_patient_profile(user_id)

            if not existing_profile:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Patient profile not found"
                )

            # Convert health_restrictions list to comma-separated string
            # health_goals stays as JSONB array with structure: [{"goal": "...", "frequency": "..."}]
            health_restrictions_str = ",".join(onboarding_data.get("health_restrictions", []))

            # Prepare update data
            update_data = {
                "date_of_birth": onboarding_data.get("date_of_birth"),
                "height_cm": onboarding_data.get("height_cm"),
                "weight_kg": onboarding_data.get("weight_kg"),
                "health_goals": onboarding_data.get("health_goals", []),  # JSONB array
                "health_restrictions": health_restrictions_str,
                "reminder_frequency": onboarding_data.get("reminder_frequency", "daily"),
                "onboarding_completed": True,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            # Add emergency contacts if provided (up to 3)
            if onboarding_data.get("emergency_contacts"):
                # Limit to 3 contacts
                contacts = onboarding_data.get("emergency_contacts", [])[:3]
                update_data["emergency_contacts"] = contacts

            # Update patient profile
            result = supabase_admin.table("patients").update(update_data).eq(
                "user_id", user_id
            ).execute()

            if not result.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Failed to update patient profile"
                )

            return result.data[0]

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to complete onboarding: {str(e)}"
            )

    @staticmethod
    async def update_patient_profile(user_id: str, update_data: Dict) -> Dict:
        """
        Update patient profile information

        Args:
            user_id: The user's ID
            update_data: Dictionary containing fields to update

        Returns:
            Updated patient profile
        """
        try:
            # Check if patient profile exists
            existing_profile = await PatientService.get_patient_profile(user_id)

            if not existing_profile:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Patient profile not found"
                )

            # Convert health_restrictions to comma-separated string if present
            # health_goals stays as JSONB array with structure: [{"goal": "...", "frequency": "..."}]
            if "health_restrictions" in update_data and isinstance(update_data["health_restrictions"], list):
                update_data["health_restrictions"] = ",".join(update_data["health_restrictions"])

            # health_goals should already be in correct format [{"goal": "...", "frequency": "..."}]
            # No conversion needed for health_goals as it's stored as JSONB

            # Add timestamp
            update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

            # Update patient profile
            result = supabase_admin.table("patients").update(update_data).eq(
                "user_id", user_id
            ).execute()

            if not result.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Failed to update patient profile"
                )

            return result.data[0]

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update patient profile: {str(e)}"
            )

    @staticmethod
    async def check_onboarding_status(user_id: str) -> Dict:
        """
        Check if patient has completed onboarding

        Args:
            user_id: The user's ID

        Returns:
            Dictionary with onboarding status
        """
        try:
            profile = await PatientService.get_patient_profile(user_id)

            if not profile:
                return {
                    "completed": False,
                    "exists": False
                }

            return {
                "completed": profile.get("onboarding_completed", False),
                "exists": True,
                "profile": profile
            }

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to check onboarding status: {str(e)}"
            )

    @staticmethod
    async def mark_goal_complete(user_id: str, goal_text: str, goal_frequency: str, completion_date: str) -> Dict:
        """
        Mark a goal as completed for a specific date

        Args:
            user_id: The user's ID
            goal_text: The goal text
            goal_frequency: Goal frequency (daily/weekly/monthly)
            completion_date: Date of completion (YYYY-MM-DD format)

        Returns:
            Goal completion record
        """
        try:
            # Check if record already exists
            existing = supabase_admin.table("goal_completions").select("*").eq(
                "user_id", user_id
            ).eq("goal_text", goal_text).eq("completion_date", completion_date).execute()

            if existing.data:
                # Update existing record
                result = supabase_admin.table("goal_completions").update({
                    "status": "completed",
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }).eq("id", existing.data[0]["id"]).execute()
            else:
                # Create new record
                result = supabase_admin.table("goal_completions").insert({
                    "user_id": user_id,
                    "goal_text": goal_text,
                    "goal_frequency": goal_frequency,
                    "completion_date": completion_date,
                    "status": "completed",
                    "completed_at": datetime.now(timezone.utc).isoformat()
                }).execute()

            return result.data[0] if result.data else {}

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to mark goal complete: {str(e)}"
            )

    @staticmethod
    async def unmark_goal_complete(user_id: str, goal_text: str, completion_date: str) -> Dict:
        """
        Unmark a goal completion (change from completed to pending)

        Args:
            user_id: The user's ID
            goal_text: The goal text
            completion_date: Date of completion (YYYY-MM-DD format)

        Returns:
            Updated goal completion record
        """
        try:
            result = supabase_admin.table("goal_completions").update({
                "status": "pending",
                "completed_at": None,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("user_id", user_id).eq("goal_text", goal_text).eq("completion_date", completion_date).execute()

            return result.data[0] if result.data else {}

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to unmark goal: {str(e)}"
            )

    @staticmethod
    async def get_goal_completions(user_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict]:
        """
        Get goal completions for a user within a date range

        Args:
            user_id: The user's ID
            start_date: Start date (YYYY-MM-DD) - defaults to 1 year ago
            end_date: End date (YYYY-MM-DD) - defaults to today

        Returns:
            List of goal completion records
        """
        try:
            # Default date range: last year to today
            if not end_date:
                end_date = date.today().isoformat()
            if not start_date:
                start_date = (date.today() - timedelta(days=365)).isoformat()

            result = supabase_admin.table("goal_completions").select("*").eq(
                "user_id", user_id
            ).gte("completion_date", start_date).lte("completion_date", end_date).order(
                "completion_date", desc=True
            ).execute()

            return result.data or []

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get goal completions: {str(e)}"
            )

    @staticmethod
    async def get_goal_stats(user_id: str) -> Dict:
        """
        Get goal completion statistics for a user

        Args:
            user_id: The user's ID

        Returns:
            Statistics including completion rate, current streak, etc.
        """
        try:
            # Get all completions
            all_completions = supabase_admin.table("goal_completions").select("*").eq(
                "user_id", user_id
            ).order("completion_date", desc=False).execute()

            completions = all_completions.data or []

            # Calculate stats
            total_tracked = len(completions)
            total_completed = len([c for c in completions if c["status"] == "completed"])
            total_missed = len([c for c in completions if c["status"] == "missed"])

            # Calculate completion rate (completed / total tracked goals)
            completion_rate = 0.0
            if total_tracked > 0:
                completion_rate = round((total_completed / total_tracked) * 100, 1)

            # Calculate current streak (consecutive days with all goals completed)
            current_streak = 0
            if completions:
                # Group by date
                from collections import defaultdict
                by_date = defaultdict(list)
                for c in completions:
                    by_date[c["completion_date"]].append(c)

                # Check consecutive days from today backwards
                check_date = date.today()
                while True:
                    date_str = check_date.isoformat()
                    if date_str not in by_date:
                        break

                    day_goals = by_date[date_str]
                    # All goals for this day must be completed
                    if all(g["status"] == "completed" for g in day_goals):
                        current_streak += 1
                        check_date -= timedelta(days=1)
                    else:
                        break

            # Calculate longest streak
            longest_streak = 0
            if completions:
                temp_streak = 0
                last_date = None

                for comp_date in sorted(set(c["completion_date"] for c in completions)):
                    day_goals = [c for c in completions if c["completion_date"] == comp_date]

                    if all(g["status"] == "completed" for g in day_goals):
                        if last_date and (datetime.fromisoformat(comp_date).date() - datetime.fromisoformat(last_date).date()).days == 1:
                            temp_streak += 1
                        else:
                            temp_streak = 1

                        longest_streak = max(longest_streak, temp_streak)
                        last_date = comp_date
                    else:
                        temp_streak = 0
                        last_date = None

            return {
                "total_tracked": total_tracked,
                "total_completed": total_completed,
                "total_missed": total_missed,
                "completion_rate": completion_rate,
                "current_streak": current_streak,
                "longest_streak": longest_streak
            }

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get goal stats: {str(e)}"
            )

    @staticmethod
    async def initialize_daily_goals(user_id: str) -> List[Dict]:
        """
        Initialize pending goal completions for today based on user's health goals

        Args:
            user_id: The user's ID

        Returns:
            List of created goal completion records
        """
        try:
            # Get user's health goals
            profile = await PatientService.get_patient_profile(user_id)
            if not profile or not profile.get("health_goals"):
                return []

            health_goals = profile["health_goals"]
            today = date.today().isoformat()
            created_records = []

            for goal_obj in health_goals:
                goal_text = goal_obj.get("goal", "")
                goal_frequency = goal_obj.get("frequency", "daily")

                if not goal_text:
                    continue

                # Check if already exists for today
                existing = supabase_admin.table("goal_completions").select("*").eq(
                    "user_id", user_id
                ).eq("goal_text", goal_text).eq("completion_date", today).execute()

                if not existing.data:
                    # Create pending record for today
                    result = supabase_admin.table("goal_completions").insert({
                        "user_id": user_id,
                        "goal_text": goal_text,
                        "goal_frequency": goal_frequency,
                        "completion_date": today,
                        "status": "pending"
                    }).execute()

                    if result.data:
                        created_records.extend(result.data)

            return created_records

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to initialize daily goals: {str(e)}"
            )

    @staticmethod
    async def mark_missed_goals() -> int:
        """
        Mark all pending goals from previous days as missed
        This should be called periodically (e.g., daily at midnight)

        Returns:
            Number of goals marked as missed
        """
        try:
            today = date.today().isoformat()

            result = supabase_admin.table("goal_completions").update({
                "status": "missed",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("status", "pending").lt("completion_date", today).execute()

            return len(result.data) if result.data else 0

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to mark missed goals: {str(e)}"
            )

    @staticmethod
    async def initialize_all_patients_daily_goals() -> Dict:
        """
        Initialize daily goals for ALL patients in the system
        This should be called via cron job daily at midnight

        Returns:
            Dictionary with success count and error count
        """
        try:
            # Get all patients with completed onboarding
            result = supabase_admin.table("patients").select("user_id").eq(
                "onboarding_completed", True
            ).execute()

            if not result.data:
                return {"success": 0, "errors": 0, "message": "No patients found"}

            success_count = 0
            error_count = 0

            for patient in result.data:
                try:
                    user_id = patient.get("user_id")
                    if user_id:
                        await PatientService.initialize_daily_goals(user_id)
                        success_count += 1
                except Exception as e:
                    print(f"Error initializing goals for patient {patient.get('user_id')}: {str(e)}")
                    error_count += 1

            return {
                "success": success_count,
                "errors": error_count,
                "message": f"Initialized goals for {success_count} patients, {error_count} errors"
            }

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to initialize all patients' daily goals: {str(e)}"
            )


# Create singleton instance
patient_service = PatientService()
