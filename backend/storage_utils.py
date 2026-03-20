import os
import uuid
import requests
import logging

logger = logging.getLogger(__name__)

STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
APP_NAME = "associate"
storage_key = None


def init_storage():
    """Initialize storage - call once at startup."""
    global storage_key
    if storage_key:
        return storage_key
    try:
        resp = requests.post(
            f"{STORAGE_URL}/init",
            json={"emergent_key": EMERGENT_KEY},
            timeout=30
        )
        resp.raise_for_status()
        storage_key = resp.json()["storage_key"]
        logger.info("Object storage initialized successfully")
        return storage_key
    except Exception as e:
        logger.error(f"Storage init failed: {e}")
        return None


def put_object(path: str, data: bytes, content_type: str) -> dict:
    """Upload file to object storage."""
    key = init_storage()
    if not key:
        raise Exception("Storage not initialized")
    resp = requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data,
        timeout=120
    )
    resp.raise_for_status()
    return resp.json()


def get_object(path: str) -> tuple:
    """Download file from object storage."""
    key = init_storage()
    if not key:
        raise Exception("Storage not initialized")
    resp = requests.get(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key},
        timeout=60
    )
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")


def generate_storage_path(user_id: str, filename: str) -> str:
    """Generate a unique storage path."""
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "bin"
    return f"{APP_NAME}/uploads/{user_id}/{uuid.uuid4().hex}.{ext}"
