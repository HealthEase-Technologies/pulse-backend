from fastapi import APIRouter, Depends, Query
from typing import List, Dict
from app.schemas.pet import (
    PetSelectRequest, PetCustomizeRequest, HealthScoreResponse
)
from app.services.pet_service import PetService
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/pets", tags=["Pets & Health Score"])


@router.get("/catalog", response_model=List[Dict])
async def get_pet_catalog():
    """Get all available pet types from catalog."""
    return await PetService.get_catalog()


@router.get("/health-score", response_model=HealthScoreResponse)
async def get_health_score(current_user: dict = Depends(get_current_user)):
    """
    Calculate today's health score (0-100) from 5 biomarkers.
    Also updates the pet's current emotion on the profile.
    Emotion: happy (≥70), neutral (40-69), sad (<40).
    """
    return await PetService.calculate_health_score(current_user["db_user"]["id"])


@router.get("/me", response_model=Dict)
async def get_my_pet(current_user: dict = Depends(get_current_user)):
    """
    Get the user's pet profile with current emotion, health score,
    Rive animation URL, streak days, and accessory unlock status.
    """
    return await PetService.get_user_pet(current_user["db_user"]["id"])


@router.post("/select", response_model=Dict)
async def select_pet(
    body: PetSelectRequest,
    current_user: dict = Depends(get_current_user)
):
    """Select or change pet type (onboarding / pet page)."""
    return await PetService.select_pet(current_user["db_user"]["id"], body.pet_key.value)


@router.put("/customize", response_model=Dict)
async def customize_pet(
    body: PetCustomizeRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Customize pet:
    - pet_name: ≤15 chars, letters/numbers/spaces only (DB-enforced)
    - color_variant: light | medium | dark
    - background_theme: park | home | beach | garden | space
    """
    update = body.model_dump(exclude_none=True)
    # Convert enums to their string values
    for key in ("color_variant", "background_theme"):
        if key in update and hasattr(update[key], "value"):
            update[key] = update[key].value
    return await PetService.customize_pet(current_user["db_user"]["id"], update)


@router.get("/timeline")
async def get_pet_timeline(
    days: int = Query(30, ge=7, le=90),
    current_user: dict = Depends(get_current_user),
):
    """Pet mood timeline: state events + daily score series for last N days."""
    return await PetService.get_state_timeline(current_user["db_user"]["id"], days=days)


@router.post("/check-unlock", response_model=Dict)
async def check_accessory_unlock(current_user: dict = Depends(get_current_user)):
    """Check and apply accessory unlock if 7-day streak is reached."""
    unlocked = await PetService.check_accessory_unlock(current_user["db_user"]["id"])
    return {"newly_unlocked": unlocked}
