#!/usr/bin/env python3
"""
Loop Master — Multi-Channel Notification Module

Sends loop status notifications across multiple channels:
- Discord webhook
- Email (SMTP)
- Slack webhook
- SMS (via Twilio or similar)
- Local log aggregation
- In-app notification queue
"""

from __future__ import annotations

import json
import os
import smtplib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.mime.text import MIMEText
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

NOTIFICATION_CONFIG_PATH = os.path.expanduser("~/tan-executive/loop_master/notification_config.json")
NOTIFICATION_LOG_PATH = os.path.expanduser("~/tan-executive/loop_master/notification_log.jsonl")


class NotificationChannel(str, Enum):
    """Supported notification channels."""
    DISCORD = "discord"
    EMAIL = "email"
    SLACK = "slack"
    SMS = "sms"
    LOG = "log"
    WEBHOOK = "webhook"


class NotificationSeverity(str, Enum):
    """Severity levels for notifications."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class NotificationConfig:
    """Configuration for a notification channel."""
    channel: NotificationChannel
    enabled: bool = True
    min_severity: NotificationSeverity = NotificationSeverity.WARNING
    # Channel-specific settings
    webhook_url: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    email_to: Optional[str] = None
    email_from: Optional[str] = None
    phone_to: Optional[str] = None
    custom_headers: Dict[str, str] = field(default_factory=dict)
    # Rate limiting
    rate_limit_seconds: int = 60  # minimum seconds between same-type notifications
    last_sent: Optional[str] = None


@dataclass
class LoopNotification:
    """A notification about a loop event."""
    loop_id: str
    loop_name: str
    event: str  # e.g., "started", "completed", "error", "frozen"
    severity: NotificationSeverity
    message: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


class NotificationEngine:
    """
    Multi-channel notification system for loop events.
    Handles routing, rate limiting, and delivery.
    """

    def __init__(self):
        self._configs: Dict[NotificationChannel, NotificationConfig] = {}
        self._custom_handlers: Dict[str, Callable] = {}
        self._load()

    def _load(self):
        """Load notification configuration from disk."""
        if os.path.exists(NOTIFICATION_CONFIG_PATH):
            try:
                with open(NOTIFICATION_CONFIG_PATH, "r") as f:
                    data = json.load(f)
                for channel_data in data.get("channels", []):
                    config = NotificationConfig(
                        channel=NotificationChannel(channel_data["channel"]),
                        enabled=channel_data.get("enabled", True),
                        min_severity=NotificationSeverity(channel_data.get("min_severity", "warning")),
                        webhook_url=channel_data.get("webhook_url"),
                        smtp_host=channel_data.get("smtp_host"),
                        smtp_port=channel_data.get("smtp_port", 587),
                        smtp_user=channel_data.get("smtp_user"),
                        smtp_password=channel_data.get("smtp_password"),
                        email_to=channel_data.get("email_to"),
                        email_from=channel_data.get("email_from"),
                        phone_to=channel_data.get("phone_to"),
                        custom_headers=channel_data.get("custom_headers", {}),
                        rate_limit_seconds=channel_data.get("rate_limit_seconds", 60),
                    )
                    self._configs[config.channel] = config
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        """Persist notification configuration."""
        os.makedirs(os.path.dirname(NOTIFICATION_CONFIG_PATH), exist_ok=True)
        data = {
            "channels": [
                {
                    "channel": config.channel.value,
                    "enabled": config.enabled,
                    "min_severity": config.min_severity.value,
                    "webhook_url": config.webhook_url,
                    "smtp_host": config.smtp_host,
                    "smtp_port": config.smtp_port,
                    "smtp_user": config.smtp_user,
                    "smtp_password": config.smtp_password,
                    "email_to": config.email_to,
                    "email_from": config.email_from,
                    "phone_to": config.phone_to,
                    "custom_headers": config.custom_headers,
                    "rate_limit_seconds": config.rate_limit_seconds,
                    "last_sent": config.last_sent,
                }
                for config in self._configs.values()
            ],
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(NOTIFICATION_CONFIG_PATH, "w") as f:
            json.dump(data, f, indent=2)

    def configure_channel(self, config: NotificationConfig):
        """Configure a notification channel."""
        self._configs[config.channel] = config
        self._save()

    def register_custom_handler(self, name: str, handler: Callable):
        """Register a custom notification handler."""
        self._custom_handlers[name] = handler

    def _check_rate_limit(self, config: NotificationConfig) -> bool:
        """Check if a channel is rate limited. Returns True if can send."""
        if not config.last_sent:
            return True

        try:
            last_time = datetime.fromisoformat(config.last_sent)
            now = datetime.now(timezone.utc)
            elapsed = (now - last_time).total_seconds()
            return elapsed >= config.rate_limit_seconds
        except (ValueError, TypeError):
            return True

    def _send_discord(self, config: NotificationConfig, notification: LoopNotification) -> bool:
        """Send notification via Discord webhook."""
        import urllib.request
        import urllib.error

        if not config.webhook_url:
            return False

        color_map = {
            NotificationSeverity.INFO: 0x3498DB,      # Blue
            NotificationSeverity.WARNING: 0xF39C12,   # Orange
            NotificationSeverity.ERROR: 0xE74C3C,     # Red
            NotificationSeverity.CRITICAL: 0x8B0000,  # Dark Red
        }

        payload = {
            "embeds": [{
                "title": f"🔄 Loop: {notification.loop_name}",
                "description": notification.message,
                "color": color_map.get(notification.severity, 0x95A5A6),
                "fields": [
                    {"name": "Event", "value": notification.event, "inline": True},
                    {"name": "Loop ID", "value": notification.loop_id, "inline": True},
                    {"name": "Severity", "value": notification.severity.value, "inline": True},
                ],
                "timestamp": notification.timestamp,
            }]
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                config.webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req, timeout=10)
            return True
        except urllib.error.URLError:
            return False

    def _send_slack(self, config: NotificationConfig, notification: LoopNotification) -> bool:
        """Send notification via Slack webhook."""
        import urllib.request
        import urllib.error

        if not config.webhook_url:
            return False

        emoji_map = {
            NotificationSeverity.INFO: ":information_source:",
            NotificationSeverity.WARNING: ":warning:",
            NotificationSeverity.ERROR: ":x:",
            NotificationSeverity.CRITICAL: ":rotating_light:",
        }

        payload = {
            "text": f"{emoji_map.get(notification.severity, ':bell:')} Loop Notification",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{emoji_map.get(notification.severity, ':bell:')} {notification.loop_name}",
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Event:*\n{notification.event}"},
                        {"type": "mrkdwn", "text": f"*Severity:*\n{notification.severity.value}"},
                        {"type": "mrkdwn", "text": f"*Loop ID:*\n`{notification.loop_id}`"},
                        {"type": "mrkdwn", "text": f"*Time:*\n{notification.timestamp}"},
                    ]
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*Message:*\n{notification.message}"},
                }
            ]
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                config.webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req, timeout=10)
            return True
        except urllib.error.URLError:
            return False

    def _send_email(self, config: NotificationConfig, notification: LoopNotification) -> bool:
        """Send notification via email."""
        if not all([config.smtp_host, config.email_to, config.email_from]):
            return False

        subject_map = {
            NotificationSeverity.INFO: "[INFO]",
            NotificationSeverity.WARNING: "[WARNING]",
            NotificationSeverity.ERROR: "[ERROR]",
            NotificationSeverity.CRITICAL: "[CRITICAL]",
        }

        subject = f"{subject_map.get(notification.severity, '[INFO]')} Loop: {notification.loop_name} - {notification.event}"
        body = f"""
Loop Notification
================

Loop: {notification.loop_name}
ID: {notification.loop_id}
Event: {notification.event}
Severity: {notification.severity.value}
Time: {notification.timestamp}

Message:
{notification.message}
"""

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = config.email_from
        msg["To"] = config.email_to

        try:
            with smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=10) as server:
                if config.smtp_user and config.smtp_password:
                    server.starttls()
                    server.login(config.smtp_user, config.smtp_password)
                server.send_message(msg)
            return True
        except Exception:
            return False

    def _send_log(self, config: NotificationConfig, notification: LoopNotification) -> bool:
        """Log notification to local file."""
        os.makedirs(os.path.dirname(NOTIFICATION_LOG_PATH), exist_ok=True)
        log_entry = {
            "timestamp": notification.timestamp,
            "loop_id": notification.loop_id,
            "loop_name": notification.loop_name,
            "event": notification.event,
            "severity": notification.severity.value,
            "message": notification.message,
            "metadata": notification.metadata,
        }
        with open(NOTIFICATION_LOG_PATH, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        return True

    def notify(self, notification: LoopNotification, channels: Optional[List[NotificationChannel]] = None):
        """
        Send a notification through configured channels.
        
        Args:
            notification: The notification to send
            channels: Optional list of channels to use (defaults to all enabled)
        """
        if channels is None:
            channels = [ch for ch, cfg in self._configs.items() if cfg.enabled]

        results = {}
        for channel in channels:
            config = self._configs.get(channel)
            if not config:
                continue

            # Check severity threshold
            severity_order = {
                NotificationSeverity.INFO: 0,
                NotificationSeverity.WARNING: 1,
                NotificationSeverity.ERROR: 2,
                NotificationSeverity.CRITICAL: 3,
            }
            if severity_order.get(notification.severity, 0) < severity_order.get(config.min_severity, 0):
                continue

            # Check rate limit
            if not self._check_rate_limit(config):
                continue

            # Send
            success = False
            if channel == NotificationChannel.DISCORD:
                success = self._send_discord(config, notification)
            elif channel == NotificationChannel.SLACK:
                success = self._send_slack(config, notification)
            elif channel == NotificationChannel.EMAIL:
                success = self._send_email(config, notification)
            elif channel == NotificationChannel.LOG:
                success = self._send_log(config, notification)
            elif channel == NotificationChannel.WEBHOOK:
                success = self._send_discord(config, notification)  # Generic webhook

            if success:
                config.last_sent = datetime.now(timezone.utc).isoformat()
                results[channel.value] = "sent"
            else:
                results[channel.value] = "failed"

        self._save()
        return results

    def notify_loop_event(
        self,
        loop_id: str,
        loop_name: str,
        event: str,
        message: str,
        severity: NotificationSeverity = NotificationSeverity.INFO,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """Convenience method to create and send a loop event notification."""
        notification = LoopNotification(
            loop_id=loop_id,
            loop_name=loop_name,
            event=event,
            severity=severity,
            message=message,
            metadata=metadata or {},
        )
        return self.notify(notification)

    def get_notification_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent notification log entries."""
        if not os.path.exists(NOTIFICATION_LOG_PATH):
            return []

        entries = []
        with open(NOTIFICATION_LOG_PATH, "r") as f:
            for line in f:
                try:
                    entries.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue

        return entries[-limit:]


# Global singleton
_notification_engine: Optional[NotificationEngine] = None


def get_notification_engine() -> NotificationEngine:
    """Get or create the global NotificationEngine singleton."""
    global _notification_engine
    if _notification_engine is None:
        _notification_engine = NotificationEngine()
    return _notification_engine
