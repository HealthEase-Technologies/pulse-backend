from pydantic import BaseModel, EmailStr
from typing import Optional
from enum import IntEnum

class UserRole(IntEnum):
    PATIENT = 1
    PROVIDER = 2
    ADMIN = 3
    
    @classmethod
    def get_name(cls, value: int) -> str:
        """Get string name from role value"""
        role_names = {1: "patient", 2: "provider", 3: "admin"}
        return role_names.get(value, "unknown")
    
    @classmethod
    def from_string(cls, role_str: str):
        """Convert string to role enum"""
        role_map = {"patient": cls.PATIENT, "provider": cls.PROVIDER, "admin": cls.ADMIN}
        return role_map.get(role_str.lower())

class UserRegister(BaseModel):
    cognito_id: str
    username: str
    email: EmailStr
    full_name: str
    role: UserRole
    phone: Optional[str] = None

class UserResponse(BaseModel):
    id: str
    cognito_id: str
    username: str
    email: str
    full_name: Optional[str] = None
    role: int
    phone: Optional[str] = None
    is_active: bool
    created_at: str

class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    role: UserRole
    phone: Optional[str] = None
    password: str