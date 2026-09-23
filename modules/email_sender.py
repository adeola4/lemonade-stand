"""Gmail sender — sends outreach emails and deal documents.
Uses Google Apps Script or Gmail API to send from transactionactionnetwork@gmail.com.
"""
from __future__ import annotations

import json
import smtplib
import subprocess
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any


GMAIL_ADDRESS = "transactionactionnetwork@gmail.com"
APPS_SCRIPT_WEB_APP_URL = ""  # Will be set if user provides Apps Script URL
SHARED_SECRET = ""  # Will be set if user provides secret


def send_email_via_gmail_api(to_email: str, subject: str, body_html: str, 
                               body_text: str = "") -> dict:
    """Send email using Gmail API via google_token.json."""
    token_path = Path.home() / ".hermes/google_token.json"
    
    if not token_path.exists():
        return {"error": "Google token not found. Run: gcloud auth login --enable-gmail-api"}
    
    try:
        with open(token_path) as f:
            creds = json.load(f)
        
        access_token = creds.get("access_token", "")
        if not access_token:
            return {"error": "No access token in google_token.json"}
        
        # Build raw email
        msg = MIMEMultipart("alternative")
        msg["From"] = GMAIL_ADDRESS
        msg["To"] = to_email
        msg["Subject"] = subject
        
        if body_text:
            msg.attach(MIMEText(body_text, "plain"))
        msg.attach(MIMEText(body_html, "html"))
        
        # Use curl to send via Gmail API
        import base64
        raw_msg = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        
        result = subprocess.run(
            ["curl", "-s", "-X", "POST",
             f"https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
             "-H", f"Authorization: Bearer {access_token}",
             "-H", "Content-Type: application/json",
             "-d", json.dumps({"raw": raw_msg})],
            capture_output=True, text=True, timeout=15
        )
        
        if result.returncode == 0:
            response = json.loads(result.stdout)
            return {"status": "sent", "message_id": response.get("id", "")}
        else:
            return {"error": f"curl failed: {result.stderr[:200]}"}
    
    except Exception as e:
        return {"error": str(e)}


def send_email_via_apps_script(to_email: str, subject: str, body_html: str, 
                                 body_text: str = "") -> dict:
    """Send via Google Apps Script web app (if configured)."""
    if not APPS_SCRIPT_WEB_APP_URL:
        return {"error": "Apps Script web app URL not configured"}
    
    try:
        payload = {
            "to": to_email,
            "from": GMAIL_ADDRESS,
            "subject": subject,
            "htmlBody": body_html,
            "textBody": body_text,
        }
        
        if SHARED_SECRET:
            payload["secret"] = SHARED_SECRET
        
        result = subprocess.run(
            ["curl", "-s", "-X", "POST",
             APPS_SCRIPT_WEB_APP_URL,
             "-H", "Content-Type: application/json",
             "-d", json.dumps(payload)],
            capture_output=True, text=True, timeout=15
        )
        
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            return {"error": f"Request failed: {result.stderr[:200]}"}
    
    except Exception as e:
        return {"error": str(e)}


def send_outreach_email(to_email: str, target_name: str, owner_name: str,
                         buyer_name: str, deal_details: dict) -> dict:
    """Compose and send outreach email for a deal."""
    subject = f"Question about {target_name}"
    
    html = f"""<html><body>
<p>{owner_name if owner_name else "Hello"},</p>

<p>I'll be direct.</p>

<p>I'm acquiring home health care agencies in the Southeast. Your company came across my radar, and I'd like to have a brief conversation.</p>

<p>I'm not a broker. I'm a buyer.</p>

<p>Here's what I bring to the table:</p>
<ul>
<li>Close within 60 days</li>
<li>Keep your team intact</li>
<li>Honor your legacy</li>
<li>Fair price based on real numbers</li>
</ul>

<p>If you've ever considered selling — even casually — let's talk. No obligation. Confidential.</p>

<p>Call me directly: [YOUR PHONE]<br>
Or reply to this email.</p>

<p>Best,<br>
{buyer_name}</p>
</body></html>"""
    
    text = f"""{owner_name if owner_name else "Hello"},

I'll be direct.

I'm acquiring home health care agencies in the Southeast. Your company came across my radar, and I'd like to have a brief conversation.

I'm not a broker. I'm a buyer.

Here's what I bring to the table:
- Close within 60 days
- Keep your team intact
- Honor your legacy
- Fair price based on real numbers

If you've ever considered selling — even casually — let's talk. No obligation. Confidential.

Call me directly: [YOUR PHONE]
Or reply to this email.

Best,
{buyer_name}"""
    
    # Try Gmail API first, fall back to Apps Script
    result = send_email_via_gmail_api(to_email, subject, html, text)
    if result.get("status") == "sent":
        return result
    
    if APPS_SCRIPT_WEB_APP_URL:
        result2 = send_email_via_apps_script(to_email, subject, html, text)
        return result2
    
    return result  # Return the original error


def configure_apps_script(web_app_url: str, shared_secret: str = "") -> None:
    """Configure Apps Script web app for email sending."""
    global APPS_SCRIPT_WEB_APP_URL, SHARED_SECRET
    APPS_SCRIPT_WEB_APP_URL = web_app_url
    SHARED_SECRET = shared_secret
    
    # Save to config file
    config = {
        "web_app_url": web_app_url,
        "shared_secret": shared_secret,
        "gmail_address": GMAIL_ADDRESS,
    }
    config_path = Path.home() / ".hermes/skills/tan-executive-agent/config/email_config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
