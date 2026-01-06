from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import settings
from app.routers import auth, users, admins, providers, patients, connections, devices, biomarkers, health_summaries
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.services.patient_service import PatientService
from app.services.health_summary_service import health_summary_service
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
# Sprint 4.2 - Devices and Biomarkers
app.include_router(devices.router, prefix=settings.api_v1_str)
app.include_router(biomarkers.router, prefix=settings.api_v1_str)
# Sprint 4.3 - Health Summaries
app.include_router(health_summaries.router, prefix=settings.api_v1_str)

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

async def generate_morning_briefing():
    """
    Cron job to generate morning briefing for all users
    Runs daily at 00:10 UTC (after goal initialization)
    Aggregates previous day's biomarker data
    """
    try:
        logger.info("Starting morning briefing generation...")
        result = await health_summary_service.generate_morning_briefing()
        logger.info(f"Morning briefing generation completed: {result}")
    except Exception as e:
        logger.error(f"Error generating morning briefing: {str(e)}")

async def send_morning_briefing_emails():
    """
    Cron job to send morning briefing emails
    Runs daily at 00:15 UTC (after briefing generation)
    """
    try:
        logger.info("Starting to send morning briefing emails...")
        count = await health_summary_service.send_morning_briefing_emails()
        logger.info(f"Sent {count} morning briefing emails")
    except Exception as e:
        logger.error(f"Error sending morning briefing emails: {str(e)}")

async def generate_evening_summary():
    """
    Cron job to generate evening summary for all users
    Runs daily at 23:59 UTC
    Aggregates current day's biomarker data
    """
    try:
        logger.info("Starting evening summary generation...")
        result = await health_summary_service.generate_evening_summary()
        logger.info(f"Evening summary generation completed: {result}")
    except Exception as e:
        logger.error(f"Error generating evening summary: {str(e)}")

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

        # Sprint 4.3 - Health Summary Cron Jobs
        # Generate morning briefing at 00:10 UTC (after goal initialization)
        scheduler.add_job(
            generate_morning_briefing,
            CronTrigger(hour=0, minute=10, timezone="UTC"),
            id="generate_morning_briefing",
            name="Generate morning health briefing for all users",
            replace_existing=True
        )

        # Send morning briefing emails at 00:15 UTC
        scheduler.add_job(
            send_morning_briefing_emails,
            CronTrigger(hour=0, minute=15, timezone="UTC"),
            id="send_morning_briefing_emails",
            name="Send morning briefing emails",
            replace_existing=True
        )

        # Generate evening summary at 23:59 UTC
        scheduler.add_job(
            generate_evening_summary,
            CronTrigger(hour=23, minute=59, timezone="UTC"),
            id="generate_evening_summary",
            name="Generate evening health summary for all users",
            replace_existing=True
        )

        scheduler.start()
        logger.info("Scheduler started successfully with daily cron jobs")
        logger.info("Jobs scheduled:")
        logger.info("  - Daily goal initialization: 00:01 UTC")
        logger.info("  - Mark missed goals: 00:05 UTC")
        logger.info("  - Generate morning briefing: 00:10 UTC")
        logger.info("  - Send morning briefing emails: 00:15 UTC")
        logger.info("  - Generate evening summary: 23:59 UTC")
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