from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import IndexModel, ASCENDING, DESCENDING
import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "darpanai_db")

client: AsyncIOMotorClient = None


async def connect_db():
    global client
    client = AsyncIOMotorClient(MONGO_URI)
    await create_indexes()


async def close_db():
    global client
    if client:
        client.close()


def get_db():
    return client[DB_NAME]


async def create_indexes():
    db = get_db()

    await db.users.create_index([("user_id", ASCENDING)], unique=True)
    await db.users.create_index([("email", ASCENDING)], unique=True)

    await db.health_logs.create_index([("user_id", ASCENDING), ("timestamp", DESCENDING)])
    await db.health_logs.create_index([("log_id", ASCENDING)], unique=True)
    await db.health_logs.create_index([("timestamp", ASCENDING)], expireAfterSeconds=63072000)

    await db.risk_scores.create_index([("user_id", ASCENDING), ("timestamp", DESCENDING)])
    await db.risk_scores.create_index([("log_id", ASCENDING)])

    await db.simulations.create_index([("user_id", ASCENDING), ("generated_at", DESCENDING)])

    await db.anomalies.create_index([("user_id", ASCENDING), ("detected_at", DESCENDING)])
    await db.anomalies.create_index([("user_id", ASCENDING), ("acknowledged", ASCENDING)])
