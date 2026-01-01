from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import settings
from app.routers import auth, users, admins, providers, patients, connections
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.services.patient_service import PatientService
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create scheduler instance
scheduler = AsyncIOScheduler()

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    debug=settings.debug
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "https://pulse-so.vercel.app",
        "https://pulse-frontend-git-staging-huzaifa785s-projects.vercel.app",
        "https://pulse-frontend-git-develop-huzaifa785s-projects.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix=settings.api_v1_str)
app.include_router(users.router, prefix=settings.api_v1_str)
app.include_router(admins.router, prefix=settings.api_v1_str)
app.include_router(providers.router, prefix=settings.api_v1_str)
app.include_router(patients.router, prefix=settings.api_v1_str)
app.include_router(connections.router, prefix=settings.api_v1_str)

@app.get("/")
async def root():
    return {"message": "Pulse Backend API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/test-db")
async def test_database():
    try:
        from app.config.database import supabase
        # Simple test query
        result = supabase.table("users").select("count", count="exact").execute()
        return {"database": "connected", "message": "Supabase connection successful"}
    except Exception as e:
        return {"database": "error", "message": str(e)}

# Cron job functions
async def daily_goal_initialization():
    """
    Cron job to initialize daily goals for all patients
    Runs daily at 00:01 UTC
    """
    try:
        logger.info("Starting daily goal initialization for all patients...")
        result = await PatientService.initialize_all_patients_daily_goals()
        logger.info(f"Daily goal initialization completed: {result}")
    except Exception as e:
        logger.error(f"Error in daily goal initialization: {str(e)}")

async def mark_missed_goals():
    """
    Cron job to mark pending goals from previous days as missed
    Runs daily at 00:05 UTC
    """
    try:
        logger.info("Starting to mark missed goals...")
        count = await PatientService.mark_missed_goals()
        logger.info(f"Marked {count} goals as missed")
    except Exception as e:
        logger.error(f"Error marking missed goals: {str(e)}")

@app.on_event("startup")
async def startup_event():
    """
    Initialize and start the scheduler when the app starts
    """
    try:
        # Schedule daily goal initialization at 00:01 UTC
        scheduler.add_job(
            daily_goal_initialization,
            CronTrigger(hour=0, minute=1, timezone="UTC"),
            id="daily_goal_initialization",
            name="Initialize daily goals for all patients",
            replace_existing=True
        )

        # Schedule marking missed goals at 00:05 UTC
        scheduler.add_job(
            mark_missed_goals,
            CronTrigger(hour=0, minute=5, timezone="UTC"),
            id="mark_missed_goals",
            name="Mark pending goals as missed",
            replace_existing=True
        )

        scheduler.start()
        logger.info("Scheduler started successfully with daily cron jobs")
        logger.info("Jobs scheduled:")
        logger.info("  - Daily goal initialization: 00:01 UTC")
        logger.info("  - Mark missed goals: 00:05 UTC")
    except Exception as e:
        logger.error(f"Error starting scheduler: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    """
    Gracefully shutdown the scheduler when the app stops
    """
    try:
        scheduler.shutdown()
        logger.info("Scheduler shutdown successfully")
    except Exception as e:
        logger.error(f"Error shutting down scheduler: {str(e)}")