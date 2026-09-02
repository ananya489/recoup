import os

from motor.motor_asyncio import AsyncIOMotorClient


MONGO_URI = os.environ.get(
    "MONGO_URI",
    "mongodb://localhost:27017",
)

DB_NAME = os.environ.get(
    "MONGO_DB_NAME",
    "recoup",
)


_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client

    if _client is None:
        _client = AsyncIOMotorClient(
            MONGO_URI,
            tz_aware=True,
        )

    return _client


def get_db():
    return get_client()[DB_NAME]