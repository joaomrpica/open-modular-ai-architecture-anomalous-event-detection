from typing import Optional

import sys
import os

try:
    from pymongo import MongoClient
except Exception:
    print("pymongo not available, MongoDB support disabled")
    MongoClient = None  # type: ignore

# Ensure parent directory (local_system) is on the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from cloud_system.config.system_config import MONGODB_URI, MONGODB_DB

_client: Optional[MongoClient] = None

def get_client() -> Optional[MongoClient]:
    print("Getting MongoDB client...")
    global _client
    if _client is None and MongoClient is not None and MONGODB_URI:
        try:
            print("Connecting to MongoDB...")
            _client = MongoClient(MONGODB_URI)
        except Exception:
            print("Failed to connect to MongoDB")
            _client = None
    print(f"Connected MongoDB client")
    return _client


def get_db():
    client = get_client()
    if client is None:
        print("MongoDB client not available")
        return None
    try:
        print(f"Trying to connected to MongoDB database: {MONGODB_DB}")
        return client[MONGODB_DB]
    except Exception:
        print("Failed to get MongoDB database")
        return None
