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
    try:
        patient_user_id = current_user["db_user"]["id"]
        recommendations = await recommendations_service.get_active_recommendations(patient_user_id, category)
        return {
            "total_count": len(recommendations),
            "recommendations": recommendations
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
    try:
        patient_user_id = current_user["db_user"]["id"]
        generated_recommendations = await recommendations_service.generate_recommendations_for_user(
            user_id=patient_user_id,
            health_data=request.health_data
        )
        return {
            "generated_count": len(generated_recommendations),
            "generated_recommendations": generated_recommendations,
            "message": f"Generated {len(generated_recommendations['recommendations'])} new personalized recommendations"       
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
        history_recommendations = await recommendations_service.get_recommendation_history(
            user_id=patient_user_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )
        return {
            "total_count": len(history_recommendations),
            "recommendations": history_recommendations
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
            user_id=patient_user_id,
            recommendation_id=recommendation_id
        )
        if not recommendation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recommendation not found"
            )
        return recommendation
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
        updated_recommendation = await recommendations_service.submit_feedback(
            user_id=patient_user_id,
            recommendation_id=recommendation_id,
            feedback=request.feedback
        )
        return updated_recommendation
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
            user_id=patient_user_id,
            recommendation_id=recommendation_id
        )
        return updated_recommendation
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
        recommendations = await recommendations_service.get_patient_recommendations_for_provider(
            provider_user_id=provider_user_id,
            patient_user_id=patient_user_id,
            status_filter=status_filter
        )
        return {
            "total_count": len(recommendations),
            "recommendations": recommendations
        }
    except HTTPException:
        raise
    except Exception as e:  
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch patient's recommendations: {str(e)}"
        )
        
