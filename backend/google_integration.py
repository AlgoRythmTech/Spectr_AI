"""
Google Drive + Sheets + Docs Integration for Spectr.

Lets users:
  1. Connect their Google account (OAuth 2.0)
  2. Upload generated Excel/DOCX/PDF files to their Drive
  3. Convert on upload: XLSX → Google Sheet, DOCX → Google Doc
  4. Browse / select destination folder
  5. Edit via chat — modify existing Sheets/Docs by re-running executor

Auth model:
  - OAuth 2.0 authorization code flow (user-consent)
  - Refresh tokens stored per-user in MongoDB
  - Tokens auto-refresh when expired

Scopes requested:
  - drive.file (only files we create/open)
  - spreadsheets
  - documents
  - drive.readonly (for folder listing — minimal footprint)
"""
import os
import json
import logging
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger("google_integration")

# === CONFIGURATION ===
CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")
REDIRECT_URI = os.environ.get("GOOGLE_OAUTH_REDIRECT_URI", "http://localhost:8000/api/google/auth/callback")

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",       # Read/write files we create/open
    "https://www.googleapis.com/auth/spreadsheets",     # Sheets full access
    "https://www.googleapis.com/auth/documents",        # Docs full access
    "https://www.googleapis.com/auth/drive.metadata.readonly",  # List folders
    "openid", "email", "profile",                        # User identity
]

# MIME types
MIME_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MIME_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
MIME_PDF = "application/pdf"
MIME_GSHEET = "application/vnd.google-apps.spreadsheet"
MIME_GDOC = "application/vnd.google-apps.document"
MIME_FOLDER = "application/vnd.google-apps.folder"


# ==================== OAUTH FLOW ====================

def build_auth_url(state: str = "") -> str:
    """Construct the OAuth consent URL for the user to click."""
    from urllib.parse import urlencode
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",           # So we get refresh_token
        "prompt": "consent",                 # Force refresh_token even on re-auth
        "include_granted_scopes": "true",
        "state": state,
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)


async def exchange_code_for_tokens(code: str) -> dict:
    """Exchange OAuth authorization code for access_token + refresh_token."""
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uri": REDIRECT_URI,
                "grant_type": "authorization_code",
            },
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status != 200:
                err = await resp.text()
                raise RuntimeError(f"Token exchange failed ({resp.status}): {err[:300]}")
            return await resp.json()


async def refresh_access_token(refresh_token: str) -> dict:
    """Use refresh_token to get a new access_token."""
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://oauth2.googleapis.com/token",
            data={
                "refresh_token": refresh_token,
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "grant_type": "refresh_token",
            },
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status != 200:
                err = await resp.text()
                raise RuntimeError(f"Refresh failed ({resp.status}): {err[:300]}")
            return await resp.json()


async def get_user_info(access_token: str) -> dict:
    """Fetch the authenticated user's Google profile (email, name, picture)."""
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status != 200:
                return {}
            return await resp.json()


# ==================== TOKEN STORAGE (MongoDB) ====================

async def save_tokens(db, user_id: str, token_data: dict, profile: dict = None) -> None:
    """Persist tokens per user. Access/refresh tokens are Fernet-encrypted at rest."""
    from token_encryption import encrypt

    expires_in = token_data.get("expires_in", 3600)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in - 60)  # 60s safety buffer

    doc = {
        "user_id": user_id,
        # Encrypt sensitive fields BEFORE writing to Mongo
        "access_token": encrypt(token_data.get("access_token", "") or ""),
        "refresh_token": encrypt(token_data.get("refresh_token", "") or ""),
        "token_type": token_data.get("token_type", "Bearer"),
        "scope": token_data.get("scope", ""),
        "expires_at": expires_at,
        "updated_at": datetime.now(timezone.utc),
    }
    if profile:
        doc["google_email"] = profile.get("email", "")
        doc["google_name"] = profile.get("name", "")
        doc["google_picture"] = profile.get("picture", "")

    await db.google_tokens.update_one(
        {"user_id": user_id},
        {"$set": doc, "$setOnInsert": {"created_at": datetime.now(timezone.utc)}},
        upsert=True,
    )


async def get_valid_access_token(db, user_id: str) -> Optional[str]:
    """Get a valid access_token for a user, refreshing if needed.

    Decrypts tokens stored at rest. Returns None if user hasn't connected or refresh fails.
    """
    from token_encryption import decrypt

    doc = await db.google_tokens.find_one({"user_id": user_id}, {"_id": 0})
    if not doc:
        return None

    # Check if access token is still valid
    expires_at = doc.get("expires_at")
    if expires_at and isinstance(expires_at, datetime):
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) < expires_at:
            access_token = decrypt(doc.get("access_token", "") or "")
            if access_token:
                return access_token

    # Need to refresh
    refresh_token = decrypt(doc.get("refresh_token", "") or "")
    if not refresh_token:
        logger.warning(f"No refresh_token for user {user_id} — must re-authorize")
        return None

    try:
        fresh = await refresh_access_token(refresh_token)
        # Preserve refresh_token (Google sometimes omits it on refresh response)
        if "refresh_token" not in fresh:
            fresh["refresh_token"] = refresh_token
        await save_tokens(db, user_id, fresh)
        return fresh.get("access_token")
    except Exception as e:
        logger.error(f"Token refresh failed for {user_id}: {e}")
        return None


async def get_connection_status(db, user_id: str) -> dict:
    """Check if a user has Google connected, and return basic info."""
    doc = await db.google_tokens.find_one({"user_id": user_id}, {"_id": 0})
    if not doc:
        return {"connected": False}
    return {
        "connected": True,
        "email": doc.get("google_email", ""),
        "name": doc.get("google_name", ""),
        "picture": doc.get("google_picture", ""),
        "connected_at": doc.get("created_at"),
    }


async def disconnect_google(db, user_id: str) -> bool:
    """Revoke + remove user's Google tokens."""
    from token_encryption import decrypt

    doc = await db.google_tokens.find_one({"user_id": user_id}, {"_id": 0})
    if not doc:
        return False
    # Best-effort revoke (decrypt first)
    try:
        refresh_tok = decrypt(doc.get("refresh_token", "") or "")
        access_tok = decrypt(doc.get("access_token", "") or "")
        revoke_target = refresh_tok or access_tok
        if revoke_target:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                await session.post(
                    "https://oauth2.googleapis.com/revoke",
                    data={"token": revoke_target},
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=aiohttp.ClientTimeout(total=5),
                )
    except Exception as e:
        logger.warning(f"Revoke failed: {e}")
    await db.google_tokens.delete_one({"user_id": user_id})
    return True


# ==================== DRIVE OPERATIONS ====================

async def list_folders(access_token: str, parent_id: str = "root", query: str = "") -> list[dict]:
    """List folders in the user's Drive. parent_id='root' lists top-level folders.

    Optional `query` for name filter (case-insensitive contains).
    """
    import aiohttp
    q_parts = ["mimeType='application/vnd.google-apps.folder'", "trashed=false"]
    if parent_id and parent_id != "root":
        q_parts.append(f"'{parent_id}' in parents")
    elif parent_id == "root":
        q_parts.append("'root' in parents")
    if query:
        safe_q = query.replace("'", "\\'")
        q_parts.append(f"name contains '{safe_q}'")
    q = " and ".join(q_parts)

    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://www.googleapis.com/drive/v3/files",
            headers={"Authorization": f"Bearer {access_token}"},
            params={
                "q": q,
                "fields": "files(id,name,parents,modifiedTime)",
                "pageSize": "100",
                "orderBy": "name",
            },
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status != 200:
                err = await resp.text()
                raise RuntimeError(f"List folders failed ({resp.status}): {err[:300]}")
            data = await resp.json()
            return data.get("files", [])


async def get_folder_path(access_token: str, folder_id: str) -> list[dict]:
    """Walk up from folder_id to root, returning breadcrumb: [{id, name}, ...]."""
    import aiohttp
    path = []
    current = folder_id
    visited = set()
    async with aiohttp.ClientSession() as session:
        while current and current != "root" and current not in visited:
            visited.add(current)
            async with session.get(
                f"https://www.googleapis.com/drive/v3/files/{current}",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"fields": "id,name,parents"},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    break
                folder = await resp.json()
                path.insert(0, {"id": folder.get("id"), "name": folder.get("name")})
                parents = folder.get("parents", [])
                current = parents[0] if parents else None
    path.insert(0, {"id": "root", "name": "My Drive"})
    return path


async def upload_file_to_drive(
    access_token: str,
    filename: str,
    content: bytes,
    folder_id: Optional[str] = None,
    convert_to_google_format: bool = True,
) -> dict:
    """Upload a file to Drive. Optionally convert xlsx→Sheets, docx→Docs.

    Returns: {id, name, webViewLink, mimeType, converted}
    """
    import aiohttp

    # Determine source mime type
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    mime_map = {
        "xlsx": MIME_XLSX,
        "xlsm": MIME_XLSX,
        "docx": MIME_DOCX,
        "pdf": MIME_PDF,
        "csv": "text/csv",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "txt": "text/plain",
        "json": "application/json",
        "html": "text/html",
    }
    source_mime = mime_map.get(ext, "application/octet-stream")

    # Target mime (for conversion) — only convert Office formats
    target_mime = None
    if convert_to_google_format:
        if source_mime == MIME_XLSX:
            target_mime = MIME_GSHEET
        elif source_mime == MIME_DOCX:
            target_mime = MIME_GDOC

    # Metadata
    clean_name = filename.rsplit(".", 1)[0] if "." in filename and target_mime else filename
    metadata = {
        "name": clean_name,
    }
    if folder_id and folder_id != "root":
        metadata["parents"] = [folder_id]
    if target_mime:
        metadata["mimeType"] = target_mime

    # Multipart upload
    boundary = "SpectrDriveBoundary" + os.urandom(8).hex()
    body_parts = [
        f"--{boundary}".encode(),
        b"Content-Type: application/json; charset=UTF-8",
        b"",
        json.dumps(metadata).encode(),
        f"--{boundary}".encode(),
        f"Content-Type: {source_mime}".encode(),
        b"Content-Transfer-Encoding: binary",
        b"",
        content,
        f"--{boundary}--".encode(),
    ]
    body = b"\r\n".join(body_parts)

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://www.googleapis.com/upload/drive/v3/files",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": f"multipart/related; boundary={boundary}",
            },
            params={"uploadType": "multipart", "fields": "id,name,webViewLink,mimeType"},
            data=body,
            timeout=aiohttp.ClientTimeout(total=120),
        ) as resp:
            if resp.status not in (200, 201):
                err = await resp.text()
                raise RuntimeError(f"Drive upload failed ({resp.status}): {err[:500]}")
            result = await resp.json()
            result["converted"] = bool(target_mime)
            return result


async def create_folder(access_token: str, name: str, parent_id: str = "root") -> dict:
    """Create a new folder in Drive."""
    import aiohttp
    metadata = {
        "name": name,
        "mimeType": MIME_FOLDER,
    }
    if parent_id and parent_id != "root":
        metadata["parents"] = [parent_id]
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://www.googleapis.com/drive/v3/files",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            params={"fields": "id,name,parents,webViewLink"},
            data=json.dumps(metadata),
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status not in (200, 201):
                err = await resp.text()
                raise RuntimeError(f"Create folder failed ({resp.status}): {err[:300]}")
            return await resp.json()


async def download_drive_file(access_token: str, file_id: str, export_format: Optional[str] = None) -> bytes:
    """Download a file from Drive by ID.

    For Google-native docs (Sheets/Docs), provide export_format:
      'xlsx' for Sheets, 'docx' for Docs, 'pdf' for either.
    For regular binary files, leave export_format=None.
    """
    import aiohttp

    export_mime_map = {
        "xlsx": MIME_XLSX,
        "docx": MIME_DOCX,
        "pdf": MIME_PDF,
    }

    async with aiohttp.ClientSession() as session:
        if export_format:
            export_mime = export_mime_map.get(export_format)
            url = f"https://www.googleapis.com/drive/v3/files/{file_id}/export"
            params = {"mimeType": export_mime}
        else:
            url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
            params = {"alt": "media"}

        async with session.get(
            url,
            headers={"Authorization": f"Bearer {access_token}"},
            params=params,
            timeout=aiohttp.ClientTimeout(total=60),
        ) as resp:
            if resp.status != 200:
                err = await resp.text()
                raise RuntimeError(f"Download failed ({resp.status}): {err[:300]}")
            return await resp.read()


async def get_file_metadata(access_token: str, file_id: str) -> dict:
    """Get metadata (name, mimeType, modifiedTime, webViewLink) for a file."""
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://www.googleapis.com/drive/v3/files/{file_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"fields": "id,name,mimeType,modifiedTime,webViewLink,parents,size"},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status != 200:
                err = await resp.text()
                raise RuntimeError(f"Get metadata failed ({resp.status}): {err[:300]}")
            return await resp.json()


# ==================== SHEETS API ====================

async def read_sheet_values(access_token: str, sheet_id: str, range_a1: str = "A1:ZZ1000") -> list[list]:
    """Read a range of values from a Google Sheet."""
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{range_a1}",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status != 200:
                err = await resp.text()
                raise RuntimeError(f"Read sheet failed ({resp.status}): {err[:300]}")
            data = await resp.json()
            return data.get("values", [])


async def update_sheet_values(
    access_token: str,
    sheet_id: str,
    range_a1: str,
    values: list[list],
    value_input_option: str = "USER_ENTERED",
) -> dict:
    """Write values to a sheet range. USER_ENTERED lets formulas work."""
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.put(
            f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{range_a1}",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            params={"valueInputOption": value_input_option},
            data=json.dumps({"values": values}),
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            if resp.status != 200:
                err = await resp.text()
                raise RuntimeError(f"Update sheet failed ({resp.status}): {err[:300]}")
            return await resp.json()


async def batch_update_sheet(access_token: str, sheet_id: str, requests: list[dict]) -> dict:
    """Apply formatting, add sheets, etc. via batchUpdate API."""
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}:batchUpdate",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            data=json.dumps({"requests": requests}),
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            if resp.status != 200:
                err = await resp.text()
                raise RuntimeError(f"batchUpdate failed ({resp.status}): {err[:300]}")
            return await resp.json()


# ==================== DOCS API ====================

async def get_doc(access_token: str, doc_id: str) -> dict:
    """Fetch full Google Doc content (structured elements)."""
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://docs.googleapis.com/v1/documents/{doc_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status != 200:
                err = await resp.text()
                raise RuntimeError(f"Get doc failed ({resp.status}): {err[:300]}")
            return await resp.json()


async def batch_update_doc(access_token: str, doc_id: str, requests: list[dict]) -> dict:
    """Apply edits via Docs batchUpdate (insert text, replace text, format, etc.)."""
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"https://docs.googleapis.com/v1/documents/{doc_id}:batchUpdate",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            data=json.dumps({"requests": requests}),
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            if resp.status != 200:
                err = await resp.text()
                raise RuntimeError(f"Doc batchUpdate failed ({resp.status}): {err[:300]}")
            return await resp.json()


def plain_text_from_doc(doc: dict) -> str:
    """Extract plain text from a Google Doc structure."""
    body = doc.get("body", {})
    content = body.get("content", [])
    lines = []
    for element in content:
        para = element.get("paragraph")
        if para:
            text = ""
            for el in para.get("elements", []):
                tr = el.get("textRun")
                if tr:
                    text += tr.get("content", "")
            if text.strip():
                lines.append(text)
        table = element.get("table")
        if table:
            for row in table.get("tableRows", []):
                cells = []
                for cell in row.get("tableCells", []):
                    cell_text = ""
                    for cell_elem in cell.get("content", []):
                        cp = cell_elem.get("paragraph")
                        if cp:
                            for el in cp.get("elements", []):
                                tr = el.get("textRun")
                                if tr:
                                    cell_text += tr.get("content", "").strip()
                    cells.append(cell_text)
                lines.append(" | ".join(cells))
    return "\n".join(lines)


# ==================== HIGH-LEVEL FLOWS ====================

async def upload_generated_file(
    db,
    user_id: str,
    filename: str,
    content: bytes,
    folder_id: Optional[str] = None,
    convert: bool = True,
) -> dict:
    """High-level flow: get valid token, upload file, return Drive file info."""
    token = await get_valid_access_token(db, user_id)
    if not token:
        raise RuntimeError("User has not connected Google account, or refresh failed")
    return await upload_file_to_drive(token, filename, content, folder_id, convert)


async def is_configured() -> dict:
    """Check if Google OAuth is configured on this backend (client_id + secret present)."""
    return {
        "configured": bool(CLIENT_ID and CLIENT_SECRET),
        "client_id_set": bool(CLIENT_ID),
        "client_secret_set": bool(CLIENT_SECRET),
        "redirect_uri": REDIRECT_URI,
    }
