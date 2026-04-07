"""
WhatsApp Business API Integration Engine
Sends compliance alerts, matter updates, document delivery, and
voice note transcription via WhatsApp Business API (Meta Cloud API).
"""
import os
import logging
import aiohttp
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

WHATSAPP_API_URL = "https://graph.facebook.com/v18.0"
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "associate_verify_2026")


async def send_text_message(to_number: str, message: str) -> dict:
    """Send a plain text WhatsApp message."""
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_ID:
        logger.warning("WhatsApp not configured. Set WHATSAPP_TOKEN and WHATSAPP_PHONE_ID.")
        return {"status": "unconfigured", "message": message, "to": to_number}
    
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_number,
        "type": "text",
        "text": {"preview_url": False, "body": message}
    }
    return await _send_whatsapp(payload)


async def send_compliance_alert(to_number: str, alert_text: str, deadline_title: str) -> dict:
    """Send a formatted compliance deadline alert via WhatsApp."""
    return await send_text_message(to_number, alert_text)


async def send_document_notification(to_number: str, filename: str, matter_name: str, download_url: str) -> dict:
    """Notify client that a document is ready for download."""
    message = (
        f"📄 *Document Ready — {matter_name}*\n\n"
        f"Your lawyer has shared: *{filename}*\n\n"
        f"🔗 Download: {download_url}\n\n"
        f"_This is a secure link from Associate AI. Do not share._"
    )
    return await send_text_message(to_number, message)


async def send_matter_update(to_number: str, matter_name: str, update: str, next_date: str = "") -> dict:
    """Send a matter status update to a client."""
    next_date_line = f"\n📅 *Next Date:* {next_date}" if next_date else ""
    message = (
        f"⚖️ *Matter Update: {matter_name}*\n\n"
        f"{update}"
        f"{next_date_line}\n\n"
        f"_Sent via Associate AI Legal Platform_"
    )
    return await send_text_message(to_number, message)


async def send_hearing_reminder(to_number: str, case_name: str, court: str, hearing_date: str, matter_id: str) -> dict:
    """Send a hearing date reminder 48 and 24 hours before."""
    message = (
        f"🏛️ *Hearing Reminder*\n\n"
        f"*Case:* {case_name}\n"
        f"*Court:* {court}\n"
        f"*Date:* {hearing_date}\n\n"
        f"Please confirm your attendance or contact your advocate immediately.\n\n"
        f"_Associate AI — Matter ID: {matter_id}_"
    )
    return await send_text_message(to_number, message)


async def send_bulk_compliance_digest(to_number: str, client_name: str, deadlines: list) -> dict:
    """Send a weekly digest of upcoming compliance deadlines."""
    if not deadlines:
        return {"status": "no_deadlines"}
    
    lines = [f"📋 *Weekly Compliance Digest — {client_name}*\n"]
    for dl in deadlines[:10]:  # Max 10 deadlines per digest
        urgency = "🚨" if dl.get("urgency") == "CRITICAL" else "⚠️" if dl.get("urgency") == "WARNING" else "📅"
        days = dl.get("days_until", "?")
        lines.append(f"{urgency} *{dl['title']}* — {days} days ({dl['date']})")
    
    lines.append("\n_Reply STOP to opt out of reminders_")
    message = "\n".join(lines)
    return await send_text_message(to_number, message)


async def _send_whatsapp(payload: dict) -> dict:
    """Internal: POST to WhatsApp Cloud API."""
    url = f"{WHATSAPP_API_URL}/{WHATSAPP_PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                data = await resp.json()
                return {"status": "sent" if resp.status == 200 else "error", "response": data}
    except Exception as e:
        logger.error(f"WhatsApp send error: {e}")
        return {"status": "error", "error": str(e)}
