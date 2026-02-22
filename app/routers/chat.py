"""
AI Chatbot Router - Streaming chat with comprehensive health data access
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from app.auth.dependencies import get_current_patient
from app.services.chatbot_service import chatbot_service
from app.schemas.chat import (
    ChatMessageRequest,
    ChatHistoryResponse,
    ChatMessage
)
from typing import Dict, List
import json


router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/message")
async def send_chat_message(
    request: ChatMessageRequest,
    current_user: Dict = Depends(get_current_patient)
):
    """
    Send a message to the AI chatbot and get a response

    The chatbot has access to ALL user health data through function calling:
    - Patient profile & health goals
    - Biomarkers (heart rate, blood pressure, glucose, steps, sleep)
    - AI recommendations
    - Alerts & thresholds
    - Health summaries
    - Connected devices
    - Provider notes
    - And more!
    """
    try:
        user_id = current_user["db_user"]["id"]

        # Get recent chat history for context
        history = await chatbot_service.get_chat_history(user_id, limit=10)

        # Save user message
        await chatbot_service.save_chat_message(
            user_id=user_id,
            role="user",
            content=request.message
        )

        # Get response from chatbot
        assistant_response = await chatbot_service.chat(
            user_id=user_id,
            message=request.message,
            chat_history=history
        )

        # Save assistant response
        await chatbot_service.save_chat_message(
            user_id=user_id,
            role="assistant",
            content=assistant_response
        )

        return {
            "response": assistant_response,
            "message": "Success"
        }

    except Exception as e:
        import traceback
        print(f"Chat error: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send chat message: {str(e)}"
        )


@router.get("/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    limit: int = 50,
    current_user: Dict = Depends(get_current_patient)
):
    """
    Get chat history for the current user

    Returns the most recent chat messages in chronological order
    """
    try:
        user_id = current_user["db_user"]["id"]
        messages = await chatbot_service.get_chat_history(user_id, limit=limit)

        return {
            "messages": messages,
            "total_count": len(messages)
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch chat history: {str(e)}"
        )


@router.delete("/history")
async def clear_chat_history(
    current_user: Dict = Depends(get_current_patient)
):
    """
    Clear all chat history for the current user
    """
    try:
        user_id = current_user["db_user"]["id"]

        # Delete all chat messages for this user
        from app.config.database import supabase_admin
        supabase_admin.table("chat_messages").delete().eq("user_id", user_id).execute()

        return {"message": "Chat history cleared successfully"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear chat history: {str(e)}"
        )
