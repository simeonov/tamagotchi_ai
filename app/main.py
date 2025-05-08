# app/main.py
from fastapi import FastAPI
from app.api.v1.endpoints import pet_interactions
from app.core.config import settings # We'll create this later
import structlog
from fastapi_structlog import InputValidationExceptionMiddleware, CorrelationIdMiddleware # and others
from app.core.logging_config import setup_logging # You'll create this file


app = FastAPI(title=settings.PROJECT_NAME)

# Call setup_logging at the beginning
setup_logging() # This will configure structlog

# Add middleware (optional but good for request IDs etc.)
app.add_middleware(CorrelationIdMiddleware)
# app.add_middleware(AccessLogMiddleware) # If using fastapi-structlog's access logger
app.add_middleware(InputValidationExceptionMiddleware) # Handles Pydantic validation errors nicely

log = structlog.get_logger(__name__)
log.info("AI Tamagotchi API starting up...")

app.include_router(pet_interactions.router, prefix=settings.API_V1_STR, tags=["pet"])

@app.get("/")
async def root():
    return {"message": "Welcome to the AI Tamagotchi API!"}

# (Later, we'll add logging setup here too)