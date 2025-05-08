# app/main.py
from fastapi import FastAPI, BackgroundTasks
from app.api.v1.endpoints import pet_interactions
from app.core.settings import settings
from app.core.logging_config import setup_logging
from app.services.pet_service import update_all_pets_tick_globally
import asyncio
import structlog

# Call setup_logging at the very beginning
setup_logging(log_level_str="INFO") # Or from env var

log = structlog.get_logger(__name__)

app = FastAPI(title=settings.PROJECT_NAME)

# --- Background Task for Global Pet Tick ---
TICK_INTERVAL_SECONDS = 10  # Run global tick every 10 seconds, adjust as needed
_keep_ticking = True

async def periodic_global_tick():
    while _keep_ticking:
        try:
            log.debug("Background task: Calling global pet tick.")
            update_all_pets_tick_globally()
        except Exception as e:
            log.error("Background task: Error during global pet tick.", exc_info=True)
        await asyncio.sleep(TICK_INTERVAL_SECONDS)

@app.on_event("startup")
async def startup_event():
    log.info("Application startup: Initializing background tasks.")
    # Start the background task
    asyncio.create_task(periodic_global_tick())

@app.on_event("shutdown")
async def shutdown_event():
    global _keep_ticking
    _keep_ticking = False
    log.info("Application shutdown: Background tasks will stop.")
# --- End Background Task ---


app.include_router(pet_interactions.router, prefix=settings.API_V1_STR, tags=["pet"])

@app.get("/")
async def root():
    log.info("Root endpoint accessed.")
    return {"message": f"Welcome to the {settings.PROJECT_NAME} API!"}

log.info(f"{settings.PROJECT_NAME} API starting up...")