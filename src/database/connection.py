import logging
from motor.motor_asyncio import AsyncIOMotorClient
from src.config import settings

logger = logging.getLogger("investmind.database")

class MongoDB:
    client: AsyncIOMotorClient = None
    db = None

    @classmethod
    async def connect(cls):
        if cls.client is None:
            try:
                logger.info(f"Connecting to MongoDB at: {settings.MONGO_URI}")
                cls.client = AsyncIOMotorClient(settings.MONGO_URI, serverSelectionTimeoutMS=3000)
                cls.db = cls.client[settings.MONGO_DB_NAME]
                # Force a connection check (ping)
                await cls.client.admin.command('ping')
                logger.info("Successfully connected to MongoDB.")
            except Exception as e:
                logger.error(f"Failed to connect to MongoDB: {e}")
                cls.client = None
                cls.db = None
                raise e

    @classmethod
    async def close(cls):
        if cls.client is not None:
            cls.client.close()
            cls.client = None
            cls.db = None
            logger.info("MongoDB connection closed.")

async def get_db():
    if MongoDB.db is None:
        await MongoDB.connect()
    return MongoDB.db
