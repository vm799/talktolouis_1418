"""MongoDB Atlas async client (PyMongo 4.13+ AsyncMongoClient).

A single AsyncMongoClient is shared across the agent process. PyMongo handles
pooling and reconnects. Call aclose() at shutdown to release the pool.

Per the PyMongo Async migration guide, AsyncMongoClient instances cannot be
shared across event loops; tests that create their own loops should construct
their own client.
"""

import os

from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

DEFAULT_DB_NAME = "livekit_mongo_starter"

_client: AsyncMongoClient | None = None


async def get_mongo_client() -> AsyncMongoClient:
    global _client
    if _client is None:
        uri = os.getenv("MONGODB_URI")
        if not uri:
            raise RuntimeError("MONGODB_URI environment variable is not set.")
        _client = AsyncMongoClient(uri)
    return _client


async def get_db(db_name: str | None = None) -> AsyncDatabase:
    client = await get_mongo_client()
    return client[db_name or os.getenv("MONGODB_DB", DEFAULT_DB_NAME)]


async def aclose() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None
