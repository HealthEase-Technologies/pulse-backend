from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.auth.dependencies import get_current_patient, get_current_provider
from app.services.recommendations_service import (
    recommendations_service,
    enrich_recommendation,
    calculate_list_stats
)
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
    try:
        patient_user_id = current_user["db_user"]["id"]
        recommendations = await recommendations_service.get_active_recommendations(patient_user_id, category)

        # Enrich each recommendation with computed fields
        enriched = [enrich_recommendation(rec) for rec in recommendations]

        # Calculate summary stats
        stats = calculate_list_stats(enriched)

        return {
            "total_count": len(enriched),
            "recommendations": enriched,
            **stats
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch active recommendations: {str(e)}"
        )


@router.post("/generate", response_model=GenerateRecommendationsResponse)
async def generate_recommendations(
    request: Optional[GenerateRecommendationsRequest] = None,
    current_user: Dict = Depends(get_current_patient)
):
    """
    Generate new AI-powered health recommendations.

    Analyzes patient's health data and generates personalized recommendations
    using Gemini AI.

    Request body is optional. If not provided, generates recommendations for all categories.
    """
    try:
        patient_user_id = current_user["db_user"]["id"]

        # Handle optional request body
        categories = None
        force_regenerate = False

        if request:
            if request.categories:
                categories = [cat.value for cat in request.categories]
            force_regenerate = request.force_regenerate

        result = await recommendations_service.generate_recommendations_for_user(
            user_id=patient_user_id,
            categories=categories,
            force_regenerate=force_regenerate
        )

        # Enrich recommendations with computed fields
        recommendations = result.get("recommendations", [])
        enriched = [enrich_recommendation(rec) for rec in recommendations]

        return {
            "generated_count": result.get("generated_count", 0),
            "recommendations": enriched,
            "message": result.get("message", "Recommendations generated")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate recommendations: {str(e)}"
        )


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
    try:
        if start_date and end_date and start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date cannot be after end_date"
            )

        patient_user_id = current_user["db_user"]["id"]
        result = await recommendations_service.get_recommendation_history(
            user_id=patient_user_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )

        # Enrich recommendations with computed fields
        recommendations = result.get("recommendations", [])
        enriched = [enrich_recommendation(rec) for rec in recommendations]
        stats = calculate_list_stats(enriched)

        return {
            "total_count": result.get("total_count", 0),
            "recommendations": enriched,
            **stats
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch recommendation history: {str(e)}"
        )
        


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
    try:
        patient_user_id = current_user["db_user"]["id"]
        recommendation = await recommendations_service.get_recommendation_by_id(
            recommendation_id=recommendation_id,
            user_id=patient_user_id
        )
        if not recommendation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recommendation not found"
            )
        return enrich_recommendation(recommendation)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch recommendation: {str(e)}"
        )
    

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
    try:
        patient_user_id = current_user["db_user"]["id"]

        # Convert enum to string value
        feedback_value = request.feedback.value if hasattr(request.feedback, "value") else request.feedback
        difficulty_value = None
        if request.difficulty_experienced:
            difficulty_value = request.difficulty_experienced.value if hasattr(request.difficulty_experienced, "value") else request.difficulty_experienced

        updated_recommendation = await recommendations_service.submit_feedback(
            recommendation_id=recommendation_id,
            user_id=patient_user_id,
            feedback=feedback_value,
            notes=request.notes,
            difficulty_experienced=difficulty_value
        )
        return enrich_recommendation(updated_recommendation)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit feedback: {str(e)}"
        )


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
    try:
        patient_user_id = current_user["db_user"]["id"]
        updated_recommendation = await recommendations_service.dismiss_recommendation(
            recommendation_id=recommendation_id,
            user_id=patient_user_id
        )
        return enrich_recommendation(updated_recommendation)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to dismiss recommendation: {str(e)}"
        )


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
    try:
        provider_user_id = current_user["db_user"]["id"]

        # Convert status enum to string value if provided
        status_value = None
        if status_filter:
            status_value = status_filter.value if hasattr(status_filter, "value") else status_filter

        recommendations = await recommendations_service.get_patient_recommendations_for_provider(
            provider_user_id=provider_user_id,
            patient_user_id=patient_user_id,
            status_filter=status_value
        )

        # Enrich recommendations with computed fields
        enriched = [enrich_recommendation(rec) for rec in recommendations]
        stats = calculate_list_stats(enriched)

        return {
            "total_count": len(enriched),
            "recommendations": enriched,
            **stats
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch patient's recommendations: {str(e)}"
        )
        
