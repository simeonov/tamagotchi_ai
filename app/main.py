# app/main.py
from fastapi import FastAPI
from app.api.v1.endpoints import pet_interactions
from app.core.settings import settings
from app.core.logging_config import setup_logging
from app.core.database import connect_to_mongo, close_mongo_connection
from app.services.pet_service import update_all_pets_tick_globally  # Now async
import asyncio
import structlog

setup_logging(log_level_str="INFO")  # Or from env var, e.g., settings.LOG_LEVEL
log = structlog.get_logger(__name__)

app = FastAPI(title=settings.PROJECT_NAME)

# --- Background Task for Global Pet Tick ---
# Consider making TICK_INTERVAL_SECONDS configurable via settings.py
TICK_INTERVAL_SECONDS = int(settings.GLOBAL_TICK_INTERVAL_SECONDS) if hasattr(settings,
                                                                              'GLOBAL_TICK_INTERVAL_SECONDS') else 10
_keep_ticking = True


async def periodic_global_tick():
    log.info("Background tick task started.", interval_seconds=TICK_INTERVAL_SECONDS)
    while _keep_ticking:
        try:
            log.debug("Background task: Initiating global pet tick.")
            await update_all_pets_tick_globally()
            log.debug("Background task: Global pet tick completed.")
        except Exception as e:
            # This catches errors in the overall update_all_pets_tick_globally call itself,
            # or if it's not an async function and raises an error before awaiting.
            # Individual pet errors within the loop in update_all_pets_tick_globally should be logged there.
            log.error("Background task: Unhandled error during global pet tick execution.", error=str(e), exc_info=True)

        try:
            await asyncio.sleep(TICK_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            log.info("Background tick task cancelled.")
            break  # Exit the loop if the task is cancelled
    log.info("Background tick task stopped.")


@app.on_event("startup")
async def startup_event():
    log.info("Application startup: Connecting to database and initializing background tasks.")
    await connect_to_mongo()
    # Start the background task
    # Store the task in app.state to be ableable to cancel it on shutdown if needed,
    # though changing _keep_ticking should be sufficient for a clean stop.
    app.state.tick_task = asyncio.create_task(periodic_global_tick())


@app.on_event("shutdown")
async def shutdown_event():
    global _keep_ticking
    _keep_ticking = False
    log.info("Application shutdown: Signalling background task to stop.")

    # Optionally, wait for the task to finish if it's critical
    if hasattr(app.state, 'tick_task') and app.state.tick_task:
        try:
            # Give it a moment to stop gracefully
            await asyncio.wait_for(app.state.tick_task, timeout=TICK_INTERVAL_SECONDS + 2)
            log.info("Background tick task finished.")
        except asyncio.TimeoutError:
            log.warn("Background tick task did not finish in time, cancelling.")
            app.state.tick_task.cancel()
        except Exception as e:
            log.error("Error during background task shutdown", error=str(e))

    await close_mongo_connection()
    log.info("Application shutdown complete.")


app.include_router(pet_interactions.router, prefix=settings.API_V1_STR, tags=["pet"])


@app.get("/")
async def root():
    log.info("Root endpoint accessed.")
    return {"message": f"Welcome to the {settings.PROJECT_NAME} API!"}


log.info(f"{settings.PROJECT_NAME} API starting up...")