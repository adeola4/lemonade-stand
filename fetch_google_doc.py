"""Fetch Google Doc/Office file content using Drive API."""
import json
import sys
from pathlib import Path

# Load token
token_path = Path.home() / ".hermes" / "google_token.json"
if not token_path.exists():
    print("No token found")
    sys.exit(1)

token = json.loads(token_path.read_text())
print("Token loaded")

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io

creds = Credentials(
    token=token.get("access_token"),
    refresh_token=token.get("refresh_token"),
    token_uri=token.get("token_uri", "https://oauth2.googleapis.com/token"),
    client_id=token.get("client_id"),
    client_secret=token.get("client_secret"),
)

service = build("drive", "v3", credentials=creds)

# Document ID from URL
FILE_ID = "16GXfeIH_Vbpp2HV6L0kcQRPjpFQR1wWz"

try:
    # Get file metadata
    meta = service.files().get(fileId=FILE_ID).execute()
    print(f"File name: {meta.get('name')}")
    print(f"MIME type: {meta.get('mimeType')}")
    print(f"Size: {meta.get('size', 'unknown')}")
    
    # Download as plain text if it's a Google Doc, or as-is if Office file
    if meta.get("mimeType") == "application/vnd.google-apps.document":
        # Export as plain text
        request = service.files().export_media(fileId=FILE_ID, mimeType="text/plain")
    else:
        # Download directly
        request = service.files().get_media(fileId=FILE_ID)
    
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
        if status:
            print(f"Download {int(status.progress() * 100)}%")
    
    content = fh.getvalue()
    print(f"Downloaded {len(content)} bytes")
    
    # Try to decode as text
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1")
    
    # Save to file
    out = Path("/tmp/yf100m_google_doc.md")
    out.write_text(text)
    print(f"Saved to {out}")
    print(f"First 500 chars: {text[:500]}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
