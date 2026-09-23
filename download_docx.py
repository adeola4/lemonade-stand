"""Re-fetch Google Drive .docx as binary."""
import json
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io

token_path = Path.home() / ".hermes" / "google_token.json"
token = json.loads(token_path.read_text())

creds = Credentials(
    token=token.get("access_token"),
    refresh_token=token.get("refresh_token"),
    token_uri=token.get("token_uri", "https://oauth2.googleapis.com/token"),
    client_id=token.get("client_id"),
    client_secret=token.get("client_secret"),
)

service = build("drive", "v3", credentials=creds)
FILE_ID = "16GXfeIH_Vbpp2HV6L0kcQRPjpFQR1wWz"

request = service.files().get_media(fileId=FILE_ID)

out_path = Path("/tmp/yf100m.docx")
with open(out_path, "wb") as fh:
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
        if status:
            print(f"Download {int(status.progress() * 100)}%")

print(f"Downloaded to {out_path}")
print(f"Size: {out_path.stat().st_size} bytes")
