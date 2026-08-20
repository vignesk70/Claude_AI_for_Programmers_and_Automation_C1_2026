from pymongo import MongoClient
from pymongo.database import Database

from app.core.config import settings

# Global client instance
_client: MongoClient | None = None
_db: Database | None = None


def get_db() -> Database:
    """Get or create the MongoDB database connection."""
    global _client, _db
    
    if _client is None:
        _client = MongoClient(settings.mongodb_url)
        _db = _client[settings.mongodb_database]
    
    return _db


def close_db():
    """Close the MongoDB connection."""
    global _client
    
    if _client is not None:
        _client.close()
        _client = None
