"""
Chat schemas for AI chatbot
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class ChatMessageRequest(BaseModel):
    """Request schema for sending a chat message"""
    message: str = Field(..., min_length=1, max_length=2000, description="The user's message")


class ChatMessage(BaseModel):
    """Schema for a single chat message"""
    id: Optional[str] = None
    role: str = Field(..., description="Message role: user or assistant")
    content: str = Field(..., description="Message content")
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ChatHistoryResponse(BaseModel):
    """Response schema for chat history"""
    messages: List[ChatMessage]
    total_count: int


class ChatStreamChunk(BaseModel):
    """Schema for streaming chat response chunks"""
    content: str
    done: bool = False
