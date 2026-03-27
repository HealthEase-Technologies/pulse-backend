from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from app.config.database import supabase

router = APIRouter(prefix="/contact", tags=["contact"])


class ContactSubmission(BaseModel):
    name: str
    email: EmailStr
    reason: str
    message: str


@router.post("/submit", status_code=status.HTTP_201_CREATED)
async def submit_contact_form(data: ContactSubmission):
    try:
        result = supabase.table("contact_submissions").insert(data.model_dump()).execute()
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to save submission")
        return {"success": True, "id": result.data[0]["id"]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
