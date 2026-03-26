from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import re


class PetKey(str, Enum):
    CAT      = "cat"
    DOG      = "dog"
    ELEPHANT = "elephant"
    LION     = "lion"
    OWL      = "owl"
    PANDA    = "panda"
    PENGUIN  = "penguin"
    RACCOON  = "raccoon"


class PetEmotion(str, Enum):
    HAPPY   = "happy"
    NEUTRAL = "neutral"
    SAD     = "sad"


class ColorVariant(str, Enum):
    LIGHT  = "light"
    MEDIUM = "medium"
    DARK   = "dark"


class BackgroundTheme(str, Enum):
    PARK   = "park"
    HOME   = "home"
    BEACH  = "beach"
    GARDEN = "garden"
    SPACE  = "space"


# ─── Health Score ─────────────────────────────────────────────────────────────

class BiomarkerScoreBreakdown(BaseModel):
    biomarker_type: str
    value:          Optional[float] = None
    score:          float
    max_score:      float = 20.0
    reason:         str


class HealthScoreResponse(BaseModel):
    user_id:    str
    date:       str
    score:      float
    emotion:    PetEmotion
    breakdown:  List[BiomarkerScoreBreakdown]
    scored_at:  datetime


# ─── Pet Responses ────────────────────────────────────────────────────────────

class UserPetResponse(BaseModel):
    id:                    str
    patient_user_id:       str
    pet_catalog_id:        Optional[str]   = None
    pet_key:               Optional[str]   = None
    display_name:          Optional[str]   = None
    pet_name:              Optional[str]   = None
    color_variant:         Optional[str]   = None
    background_theme:      Optional[str]   = None
    accessory_unlocked:    bool            = False
    accessory_unlocked_at: Optional[datetime] = None
    current_emotion:       str             = "neutral"
    current_score:         float           = 50.0
    last_evaluated_at:     Optional[datetime] = None
    riv_url:               str             = ""
    image_url:             str             = ""
    streak_days:           int             = 0
    created_at:            Optional[datetime] = None
    updated_at:            Optional[datetime] = None


# ─── Requests ─────────────────────────────────────────────────────────────────

class PetSelectRequest(BaseModel):
    pet_key: PetKey

    class Config:
        json_schema_extra = {"example": {"pet_key": "dog"}}


class PetCustomizeRequest(BaseModel):
    pet_name:         Optional[str]           = Field(None, max_length=15)
    color_variant:    Optional[ColorVariant]  = None
    background_theme: Optional[BackgroundTheme] = None

    class Config:
        json_schema_extra = {
            "example": {
                "pet_name": "Buddy",
                "color_variant": "light",
                "background_theme": "park"
            }
        }
