from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    app_name: str = "Pulse Backend"
    debug: bool = False
    api_v1_str: str = "/api/v1"
    supabase_url: str
    supabase_key: str
    supabase_service_key: str
    aws_region: str = "us-east-1"
    cognito_user_pool_id: str
    cognito_client_id: str
    aws_access_key_id: str
    aws_secret_access_key: str
    s3_bucket_name: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    email_sender: str
    email_password: str
    smtp_server: str
    smtp_port: int
    gemini_api_key: str

    # Sprint 7 - Alerts & Notifications
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_whatsapp_from: str = "whatsapp:+14155238886"  # Twilio sandbox number
    whatsapp_enabled: bool = False
    alert_cooldown_warning_minutes: int = 30
    alert_cooldown_critical_minutes: int = 15

    class Config:
        env_file = ".env"

settings = Settings()