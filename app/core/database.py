# app/core/database.py
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.settings import settings
import structlog

log = structlog.get_logger(__name__)

class MongoDBConnection:
    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None

db_connection = MongoDBConnection()

async def connect_to_mongo():
    log.info("Connecting to MongoDB...")
    db_connection.client = AsyncIOMotorClient(settings.MONGO_CONNECTION_URI)
    db_connection.db = db_connection.client
    try:
        # The ismaster command is cheap and does not require auth.
        await db_connection.client.admin.command('ismaster')
        log.info("Successfully connected to MongoDB.")
    except Exception as e:
        log.error("Failed to connect to MongoDB", error=str(e))
        # Handle connection error appropriately, perhaps raise an exception or exit
        raise

async def close_mongo_connection():
    log.info("Closing MongoDB connection...")
    if db_connection.client:
        db_connection.client.close()
        log.info("MongoDB connection closed.")

def get_database() -> AsyncIOMotorDatabase:
    if db_connection.db is None:
        # This case should ideally not happen if connect_to_mongo is called on startup
        # For robustness, you might want to raise an error or attempt a reconnect here.
        log.error("Database not initialized. Call connect_to_mongo first.")
        raise RuntimeError("Database not initialized.")
    return db_connection.db

# Collection names
PETS_COLLECTION = "pets"