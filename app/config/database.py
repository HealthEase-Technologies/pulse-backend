from supabase import create_client, Client
from app.config.settings import settings

# Initialize Supabase client
supabase: Client = create_client(
    settings.supabase_url, 
    settings.supabase_key
)

# Service role client for admin operations
supabase_admin: Client = create_client(
    settings.supabase_url, 
    settings.supabase_service_key
)