from app.config.database import supabase_admin
from fastapi import HTTPException, status
from typing import Dict, List, Optional
from datetime import datetime, date, timezone
from app.schemas.pet import PetEmotion, BiomarkerScoreBreakdown, HealthScoreResponse
import logging

logger = logging.getLogger(__name__)


# ─── Health Score Rules ───────────────────────────────────────────────────────
# (optimal_low, optimal_high, normal_low, normal_high) — each worth 20 pts

SCORE_RULES = {
    "heart_rate":              (60,   80,   50,  100),
    "blood_pressure_systolic": (100,  120,  90,  140),
    "glucose":                 (70,   100,  70,  125),
    "steps":                   (8000, 12000, 4000, 20000),
    "sleep":                   (7,    9,    5,    12),
}
SCORED_BIOMARKERS = list(SCORE_RULES.keys())


def _score_biomarker(bt: str, value: float) -> tuple[float, str]:
    opt_lo, opt_hi, norm_lo, norm_hi = SCORE_RULES[bt]
    if opt_lo <= value <= opt_hi:
        return 20.0, "In optimal range"
    elif norm_lo <= value <= norm_hi:
        dist = min(abs(value - opt_lo), abs(value - opt_hi))
        span = max(opt_lo - norm_lo, norm_hi - opt_hi) or 1
        return round(10.0 + 9.0 * max(0.0, 1.0 - dist / span), 2), "Within normal range"
    else:
        overshoot = (norm_lo - value) if value < norm_lo else (value - norm_hi)
        span = (norm_lo * 0.5 if value < norm_lo else norm_hi * 0.3) or 1
        return round(max(0.0, 9.0 * (1.0 - overshoot / span)), 2), "Outside normal range"


def _emotion_from_score(score: float) -> PetEmotion:
    if score >= 70:
        return PetEmotion.HAPPY
    elif score >= 40:
        return PetEmotion.NEUTRAL
    return PetEmotion.SAD


def _riv_url(cat: Dict, emotion: PetEmotion) -> str:
    mapping = {
        PetEmotion.HAPPY:   "happy_asset_url",
        PetEmotion.NEUTRAL: "neutral_asset_url",
        PetEmotion.SAD:     "sad_asset_url",
    }
    return cat.get(mapping[emotion], "")


class PetService:

    # ── Catalog helpers ───────────────────────────────────────────────────────

    @staticmethod
    async def get_catalog() -> List[Dict]:
        try:
            resp = (
                supabase_admin.table("pet_catalog")
                .select("*")
                .eq("is_active", True)
                .order("sort_order")
                .execute()
            )
            return resp.data or []
        except Exception as e:
            logger.error(f"Error fetching pet catalog: {e}")
            raise HTTPException(500, "Failed to fetch pet catalog")

    @staticmethod
    async def _catalog_by_key(pet_key: str) -> Optional[Dict]:
        resp = (
            supabase_admin.table("pet_catalog")
            .select("*")
            .eq("pet_key", pet_key)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        return resp.data[0] if resp.data else None

    @staticmethod
    async def _catalog_by_id(catalog_id: str) -> Optional[Dict]:
        resp = (
            supabase_admin.table("pet_catalog")
            .select("*")
            .eq("id", catalog_id)
            .limit(1)
            .execute()
        )
        return resp.data[0] if resp.data else None

    # ── Health Score ──────────────────────────────────────────────────────────

    @staticmethod
    async def calculate_health_score(user_id: str) -> HealthScoreResponse:
        """
        Calculate today's health score (0-100) from 5 biomarkers.
        Uses most recent reading from today, falls back to yesterday.
        Stores result in daily_health_scores and updates patient_pet_profiles.
        """
        try:
            today     = date.today().isoformat()
            yesterday = date.fromordinal(date.today().toordinal() - 1).isoformat()

            breakdown: List[BiomarkerScoreBreakdown] = []
            total = 0.0

            for bt in SCORED_BIOMARKERS:
                value = None
                for day in [today, yesterday]:
                    resp = (
                        supabase_admin.table("biomarkers")
                        .select("value")
                        .eq("user_id", user_id)
                        .eq("biomarker_type", bt)
                        .gte("recorded_at", f"{day}T00:00:00+00:00")
                        .lte("recorded_at", f"{day}T23:59:59+00:00")
                        .order("recorded_at", desc=True)
                        .limit(1)
                        .execute()
                    )
                    if resp.data:
                        value = resp.data[0]["value"]
                        break

                sc, reason = _score_biomarker(bt, value) if value is not None \
                             else (10.0, "No data — using neutral score")
                total += sc
                breakdown.append(BiomarkerScoreBreakdown(
                    biomarker_type=bt, value=value, score=sc, reason=reason
                ))

            final_score = round(min(total, 100.0), 2)
            emotion     = _emotion_from_score(final_score)
            now         = datetime.now(timezone.utc)

            # Upsert daily_health_scores
            try:
                supabase_admin.table("daily_health_scores").upsert(
                    {
                        "user_id":    user_id,
                        "date":       today,
                        "score":      final_score,
                        "breakdown":  [b.model_dump() for b in breakdown],
                        "updated_at": now.isoformat(),
                    },
                    on_conflict="user_id,date"
                ).execute()
            except Exception as e:
                logger.warning(f"Could not upsert daily_health_scores: {e}")

            # Update pet profile emotion + score
            await PetService._update_pet_state(
                user_id, final_score, emotion, now,
                breakdown=[b.model_dump() for b in breakdown]
            )

            return HealthScoreResponse(
                user_id=user_id, date=today, score=final_score,
                emotion=emotion, breakdown=breakdown, scored_at=now,
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error calculating health score for {user_id}: {e}")
            raise HTTPException(500, "Failed to calculate health score")

    @staticmethod
    async def _update_pet_state(
        user_id: str, score: float, emotion: PetEmotion,
        now: datetime, breakdown: List[Dict] = None
    ):
        """Update current_emotion/current_score on the pet profile and log state event."""
        try:
            pet_resp = (
                supabase_admin.table("patient_pet_profiles")
                .select("id, current_emotion")
                .eq("patient_user_id", user_id)
                .limit(1)
                .execute()
            )
            if not pet_resp.data:
                return  # no pet yet — nothing to update

            pet = pet_resp.data[0]
            prev_emotion = pet["current_emotion"]

            supabase_admin.table("patient_pet_profiles").update({
                "current_emotion":  emotion.value,
                "current_score":    score,
                "last_evaluated_at": now.isoformat(),
                "updated_at":       now.isoformat(),
            }).eq("patient_user_id", user_id).execute()

            # Log state event
            supabase_admin.table("patient_pet_state_events").insert({
                "patient_user_id":       user_id,
                "previous_emotion":      prev_emotion,
                "new_emotion":           emotion.value,
                "final_score":           score,
                "health_score_component": score,
                "trigger_source":        "health_summary_updated",
                "input_snapshot":        {"breakdown": breakdown} if breakdown else None,
            }).execute()
        except Exception as e:
            logger.warning(f"Could not update pet state for {user_id}: {e}")

    # ── Get User Pet ──────────────────────────────────────────────────────────

    @staticmethod
    async def get_user_pet(user_id: str) -> Dict:
        try:
            pet_resp = (
                supabase_admin.table("patient_pet_profiles")
                .select("*")
                .eq("patient_user_id", user_id)
                .limit(1)
                .execute()
            )
            if not pet_resp.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No pet found. Please select a pet first."
                )
            pet = pet_resp.data[0]

            # Get catalog row for asset URLs
            cat = await PetService._catalog_by_id(pet["pet_catalog_id"]) \
                  if pet.get("pet_catalog_id") else None

            emotion = PetEmotion(pet["current_emotion"])
            streak  = await PetService._get_streak(user_id)

            return {
                **pet,
                "pet_key":       cat["pet_key"]          if cat else None,
                "display_name":  cat["display_name"]     if cat else None,
                "riv_url":       _riv_url(cat, emotion)  if cat else "",
                "image_url":     cat["selection_asset_url"] if cat else "",
                "streak_days":   streak,
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching user pet for {user_id}: {e}")
            raise HTTPException(500, "Failed to fetch pet")

    # ── Select Pet ────────────────────────────────────────────────────────────

    @staticmethod
    async def select_pet(user_id: str, pet_key: str) -> Dict:
        try:
            cat = await PetService._catalog_by_key(pet_key)
            if not cat:
                raise HTTPException(400, "Invalid pet type")

            now = datetime.now(timezone.utc).isoformat()
            existing = (
                supabase_admin.table("patient_pet_profiles")
                .select("id, current_emotion")
                .eq("patient_user_id", user_id)
                .execute()
            )

            if existing.data:
                supabase_admin.table("patient_pet_profiles").update({
                    "pet_catalog_id": cat["id"],
                    "updated_at":     now,
                }).eq("patient_user_id", user_id).execute()
            else:
                supabase_admin.table("patient_pet_profiles").insert({
                    "patient_user_id": user_id,
                    "pet_catalog_id":  cat["id"],
                    "current_emotion": "neutral",
                    "current_score":   50.0,
                    "created_at":      now,
                    "updated_at":      now,
                }).execute()

            return await PetService.get_user_pet(user_id)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error selecting pet for {user_id}: {e}")
            raise HTTPException(500, "Failed to select pet")

    # ── Customize Pet ─────────────────────────────────────────────────────────

    @staticmethod
    async def customize_pet(user_id: str, data: Dict) -> Dict:
        try:
            existing = (
                supabase_admin.table("patient_pet_profiles")
                .select("id")
                .eq("patient_user_id", user_id)
                .execute()
            )
            if not existing.data:
                raise HTTPException(404, "No pet found. Please select a pet first.")

            update_data = {k: v for k, v in data.items() if v is not None}
            update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

            supabase_admin.table("patient_pet_profiles").update(update_data) \
                .eq("patient_user_id", user_id).execute()

            # Log profile_updated event
            try:
                pet = (
                    supabase_admin.table("patient_pet_profiles")
                    .select("current_emotion, current_score")
                    .eq("patient_user_id", user_id)
                    .limit(1)
                    .execute()
                ).data[0]
                supabase_admin.table("patient_pet_state_events").insert({
                    "patient_user_id": user_id,
                    "previous_emotion": pet["current_emotion"],
                    "new_emotion":      pet["current_emotion"],
                    "final_score":      pet["current_score"],
                    "trigger_source":   "profile_updated",
                    "input_snapshot":   data,
                }).execute()
            except Exception:
                pass

            return await PetService.get_user_pet(user_id)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error customizing pet for {user_id}: {e}")
            raise HTTPException(500, "Failed to customize pet")

    # ── Streak ────────────────────────────────────────────────────────────────

    @staticmethod
    async def _get_streak(user_id: str) -> int:
        try:
            resp = (
                supabase_admin.table("goal_completions")
                .select("date")
                .eq("user_id", user_id)
                .eq("status", "completed")
                .order("date", desc=True)
                .limit(60)
                .execute()
            )
            if not resp.data:
                return 0
            dates = sorted({r["date"][:10] for r in resp.data}, reverse=True)
            today = date.today()
            streak = 0
            for i, d in enumerate(dates):
                if date.fromisoformat(d).toordinal() == today.toordinal() - i:
                    streak += 1
                else:
                    break
            return streak
        except Exception:
            return 0

    # ── Check & unlock accessory ──────────────────────────────────────────────

    @staticmethod
    async def check_accessory_unlock(user_id: str) -> bool:
        """Unlock accessory if streak >= 7 and not yet unlocked."""
        try:
            pet_resp = (
                supabase_admin.table("patient_pet_profiles")
                .select("id, accessory_unlocked")
                .eq("patient_user_id", user_id)
                .limit(1)
                .execute()
            )
            if not pet_resp.data or pet_resp.data[0]["accessory_unlocked"]:
                return False
            streak = await PetService._get_streak(user_id)
            if streak >= 7:
                now = datetime.now(timezone.utc).isoformat()
                supabase_admin.table("patient_pet_profiles").update({
                    "accessory_unlocked":    True,
                    "accessory_unlocked_at": now,
                    "updated_at":            now,
                }).eq("patient_user_id", user_id).execute()
                return True
            return False
        except Exception:
            return False

    # ── Cron: daily reset ─────────────────────────────────────────────────────

    @staticmethod
    async def recalculate_all_scores() -> Dict:
        try:
            users = (
                supabase_admin.table("patients").select("user_id").execute()
            ).data or []
            success = failed = 0
            for u in users:
                try:
                    await PetService.calculate_health_score(u["user_id"])
                    await PetService.check_accessory_unlock(u["user_id"])
                    success += 1
                except Exception as e:
                    logger.error(f"Score calc failed for {u['user_id']}: {e}")
                    failed += 1
            return {"success": success, "failed": failed, "total": len(users)}
        except Exception as e:
            logger.error(f"Bulk score recalculation error: {e}")
            return {"error": str(e)}


pet_service = PetService()
