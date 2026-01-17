from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.auth.dependencies import get_current_patient, get_current_provider
from app.services.recommendations_service import recommendations_service
from app.schemas.recommendations import (
    RecommendationResponse,
    RecommendationListResponse,
    FeedbackRequest,
    GenerateRecommendationsRequest,
    GenerateRecommendationsResponse,
    RecommendationStatus
)
from typing import Dict, List, Optional
from datetime import date

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


# =============================================================================
# PATIENT ENDPOINTS
# =============================================================================

@router.get("", response_model=RecommendationListResponse)
async def get_active_recommendations(
    category: Optional[str] = Query(None, description="Filter by category"),
    current_user: Dict = Depends(get_current_patient)
):
    """
    Get active AI recommendations for the authenticated patient.

    Returns list of active recommendations ordered by priority.
    """
    # TODO: Implement endpoint
    # Steps:
    # 1. Get user_id from current_user
    # 2. Call recommendations_service.get_active_recommendations()
    # 3. Format and return response
    pass


@router.post("/generate", response_model=GenerateRecommendationsResponse)
async def generate_recommendations(
    request: GenerateRecommendationsRequest,
    current_user: Dict = Depends(get_current_patient)
):
    """
    Generate new AI-powered health recommendations.

    Analyzes patient's health data and generates personalized recommendations
    using Gemini AI.
    """
    # TODO: Implement endpoint
    # Steps:
    # 1. Get user_id from current_user
    # 2. Call recommendations_service.generate_recommendations_for_user()
    # 3. Return generated recommendations
    pass


@router.get("/history", response_model=RecommendationListResponse)
async def get_recommendation_history(
    start_date: Optional[date] = Query(None, description="Start date filter"),
    end_date: Optional[date] = Query(None, description="End date filter"),
    limit: int = Query(50, ge=1, le=100, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: Dict = Depends(get_current_patient)
):
    """
    Get recommendation history for the authenticated patient.

    Supports date range filtering and pagination.
    """
    # TODO: Implement endpoint
    # Steps:
    # 1. Validate date range if both provided
    # 2. Get user_id from current_user
    # 3. Call recommendations_service.get_recommendation_history()
    # 4. Format and return response
    pass


@router.get("/{recommendation_id}", response_model=RecommendationResponse)
async def get_recommendation_by_id(
    recommendation_id: str,
    current_user: Dict = Depends(get_current_patient)
):
    """
    Get a specific recommendation by ID.
    """
    # TODO: Implement endpoint
    # Steps:
    # 1. Get user_id from current_user
    # 2. Call recommendations_service.get_recommendation_by_id()
    # 3. Raise 404 if not found
    # 4. Return recommendation
    pass


@router.patch("/{recommendation_id}/feedback", response_model=RecommendationResponse)
async def submit_feedback(
    recommendation_id: str,
    request: FeedbackRequest,
    current_user: Dict = Depends(get_current_patient)
):
    """
    Submit feedback for a recommendation.

    Feedback helps improve future recommendations.
    """
    # TODO: Implement endpoint
    # Steps:
    # 1. Get user_id from current_user
    # 2. Call recommendations_service.submit_feedback()
    # 3. Return updated recommendation
    pass


@router.patch("/{recommendation_id}/dismiss", response_model=RecommendationResponse)
async def dismiss_recommendation(
    recommendation_id: str,
    current_user: Dict = Depends(get_current_patient)
):
    """
    Dismiss a recommendation.

    Dismissed recommendations will no longer appear in active list.
    """
    # TODO: Implement endpoint
    # Steps:
    # 1. Get user_id from current_user
    # 2. Call recommendations_service.dismiss_recommendation()
    # 3. Return updated recommendation
    pass


# =============================================================================
# PROVIDER ENDPOINTS
# =============================================================================

@router.get("/patient/{patient_user_id}", response_model=RecommendationListResponse)
async def get_patient_recommendations(
    patient_user_id: str,
    status_filter: Optional[RecommendationStatus] = Query(None, description="Filter by status"),
    current_user: Dict = Depends(get_current_provider)
):
    """
    Provider gets a patient's AI recommendations.

    Requires an accepted connection with the patient.
    """
    # TODO: Implement endpoint
    # Steps:
    # 1. Get provider_user_id from current_user
    # 2. Call recommendations_service.get_patient_recommendations_for_provider()
    # 3. Format and return response
    pass
