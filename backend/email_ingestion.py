"""
Email Document Ingestion
Receives forwarded emails via a webhook endpoint and automatically
ingests attachments into the correct Vault matter.
"""
import os
import json
import base64
import email
import logging
import uuid
import re
from datetime import datetime, timezone
from email import policy
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = AsyncIOMotorClient(MONGO_URI)
db = client["associate_db"]

# Mapping of unique ingest addresses to matter IDs
# Format: {matter_id}@ingest.associate.ai -> routes to that matter's vault
INGEST_DOMAIN = os.getenv("INGEST_DOMAIN", "ingest.associate.ai")

async def process_inbound_email(raw_email: str, recipient_address: str) -> dict:
    """
    Process an inbound forwarded email.
    1. Parse the email
    2. Extract attachments
    3. Route to the correct matter based on recipient address
    4. Save documents to vault
    """
    # Parse the recipient to get matter_id
    matter_id = _extract_matter_id(recipient_address)
    if not matter_id:
        return {"error": "Could not determine target matter from email address"}
    
    # Parse email
    msg = email.message_from_string(raw_email, policy=policy.default)
    
    sender = msg.get("From", "unknown")
    subject = msg.get("Subject", "No Subject")
    date = msg.get("Date", datetime.now().isoformat())
    
    # Extract body
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_content()
                break
    else:
        body = msg.get_content()
    
    # Extract attachments
    attachments = []
    if msg.is_multipart():
        for part in msg.walk():
            filename = part.get_filename()
            if filename:
                content = part.get_payload(decode=True)
                if content:
                    file_ext = os.path.splitext(filename)[1].lower()
                    file_id = f"email_{uuid.uuid4().hex[:12]}"
                    
                    # Save to disk
                    upload_dir = os.path.join("uploads", "email_ingest")
                    os.makedirs(upload_dir, exist_ok=True)
                    file_path = os.path.join(upload_dir, f"{file_id}{file_ext}")
                    
                    with open(file_path, "wb") as f:
                        f.write(content)
                    
                    # Save to MongoDB vault
                    doc_record = {
                        "doc_id": file_id,
                        "filename": filename,
                        "extension": file_ext.replace(".", ""),
                        "size": len(content),
                        "matter_id": matter_id,
                        "source": "email",
                        "email_from": sender,
                        "email_subject": subject,
                        "local_path": file_path,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "doc_type": _classify_doc_type(filename),
                    }
                    
                    await db.vault_documents.insert_one(doc_record)
                    doc_record.pop("_id", None)
                    attachments.append(doc_record)
    
    # Save the email itself as a record
    email_record = {
        "email_id": f"eml_{uuid.uuid4().hex[:12]}",
        "matter_id": matter_id,
        "from": sender,
        "subject": subject,
        "date": date,
        "body_preview": body[:500] if body else "",
        "attachment_count": len(attachments),
        "attachment_ids": [a["doc_id"] for a in attachments],
        "ingested_at": datetime.now(timezone.utc).isoformat()
    }
    await db.email_ingestion_log.insert_one(email_record)
    
    return {
        "matter_id": matter_id,
        "email_from": sender,
        "email_subject": subject,
        "attachments_saved": len(attachments),
        "attachment_filenames": [a["filename"] for a in attachments]
    }


async def process_whatsapp_document(
    phone_number: str,
    media_url: str,
    media_type: str,
    filename: str,
    matter_id: str
) -> dict:
    """
    Process a document received via WhatsApp.
    Downloads the media and saves to vault.
    """
    import aiohttp
    
    file_id = f"wa_{uuid.uuid4().hex[:12]}"
    file_ext = os.path.splitext(filename)[1].lower() if filename else ".pdf"
    
    upload_dir = os.path.join("uploads", "whatsapp_ingest")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"{file_id}{file_ext}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(media_url) as resp:
                if resp.status == 200:
                    content = await resp.read()
                    with open(file_path, "wb") as f:
                        f.write(content)
                    
                    doc_record = {
                        "doc_id": file_id,
                        "filename": filename or f"WhatsApp_Doc_{file_id}{file_ext}",
                        "extension": file_ext.replace(".", ""),
                        "size": len(content),
                        "matter_id": matter_id,
                        "source": "whatsapp",
                        "wa_phone": phone_number,
                        "local_path": file_path,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "doc_type": _classify_doc_type(filename or ""),
                    }
                    
                    await db.vault_documents.insert_one(doc_record)
                    doc_record.pop("_id", None)
                    
                    return {"status": "success", "document": doc_record}
    except Exception as e:
        logger.error(f"WhatsApp document download error: {e}")
        return {"status": "error", "error": str(e)}
    
    return {"status": "error", "error": "Failed to download media"}


async def generate_ingest_address(matter_id: str, user_id: str) -> str:
    """Generate a unique email address for a matter for document forwarding."""
    # Create a short hash for the address
    addr_hash = uuid.uuid4().hex[:8]
    ingest_address = f"{matter_id}-{addr_hash}@{INGEST_DOMAIN}"
    
    # Store the mapping
    await db.ingest_addresses.update_one(
        {"matter_id": matter_id, "user_id": user_id},
        {"$set": {
            "ingest_address": ingest_address,
            "created_at": datetime.now(timezone.utc).isoformat()
        }},
        upsert=True
    )
    
    return ingest_address


def _extract_matter_id(email_address: str) -> str:
    """Extract matter_id from the ingest email address."""
    local_part = email_address.split("@")[0]
    # Format: {matter_id}-{hash}
    parts = local_part.rsplit("-", 1)
    return parts[0] if parts else None


def _classify_doc_type(filename: str) -> str:
    """Simple heuristic to classify document type from filename."""
    lower = filename.lower()
    if any(kw in lower for kw in ["notice", "scn", "show cause"]):
        return "gst_notice"
    if any(kw in lower for kw in ["order", "judgment", "decree"]):
        return "court_order"
    if any(kw in lower for kw in ["agreement", "contract", "mou", "nda"]):
        return "contract"
    if any(kw in lower for kw in ["balance sheet", "p&l", "financial", "audit"]):
        return "financial_statement"
    if any(kw in lower for kw in ["gstr", "return", "itr"]):
        return "tax_return"
    return "other"
