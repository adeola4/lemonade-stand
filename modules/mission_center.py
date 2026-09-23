"""Mission Center — manual mission CRUD for the Lemonade Stand dashboard + Discord agent.

This module implements the same storage format as the mission-scroll-generator skill
(mission_id, title, priority, status, assigned_staff, created_at, pct_complete) and
is designed to be read by the tracker's post_deploy_hook."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

MISSIONS_FILE = Path.home() / "tan-executive" / "missions.json"
VALID_PRIORITIES = {"critical", "standard", "routine"}
VALID_STATUSES = {"draft", "active", "blocked", "completed", "archived"}


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:24]


def _generate_id(title: str) -> str:
    return f"m-{_slug(title)}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"


@dataclass
class Mission:
    mission_id: str
    title: str
    description: str
    priority: str  # critical | standard | routine
    status: str  # draft | active | blocked | completed | archived
    assigned_staff: list[str]
    company: str
    deal_thread: str
    pct_complete: int
    blockers: str
    created_at: str
    updated_at: str
    due_date: str
    tags: list[str]
    source: str  # "web" | "discord" | "agent"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_missions() -> list[dict[str, Any]]:
    if not MISSIONS_FILE.exists():
        return []
    return json.loads(MISSIONS_FILE.read_text())


def save_missions(missions: list[dict[str, Any]]) -> None:
    MISSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    MISSIONS_FILE.write_text(json.dumps(missions, indent=2))


def create_mission(
    title: str,
    description: str = "",
    priority: str = "standard",
    company: str = "",
    deal_thread: str = "",
    assigned_staff: list[str] | None = None,
    due_date: str = "",
    tags: list[str] | None = None,
    source: str = "web",
) -> dict[str, Any]:
    priority = priority if priority in VALID_PRIORITIES else "standard"
    mission = Mission(
        mission_id=_generate_id(title),
        title=title,
        description=description,
        priority=priority,
        status="active",
        assigned_staff=assigned_staff or [],
        company=company,
        deal_thread=deal_thread,
        pct_complete=0,
        blockers="",
        created_at=_now(),
        updated_at=_now(),
        due_date=due_date,
        tags=tags or [],
        source=source,
    )
    missions = load_missions()
    missions.append(mission.to_dict())
    save_missions(missions)
    return mission.to_dict()


def update_mission(mission_id: str, **kwargs: Any) -> dict[str, Any] | None:
    missions = load_missions()
    for m in missions:
        if m["mission_id"] == mission_id:
            for k, v in kwargs.items():
                if k in m:
                    m[k] = v
            m["updated_at"] = _now()
            save_missions(missions)
            return m
    return None


def get_mission(mission_id: str) -> dict[str, Any] | None:
    for m in load_missions():
        if m["mission_id"] == mission_id:
            return m
    return None


def list_missions(
    status: str | None = None,
    priority: str | None = None,
    company: str | None = None,
    source: str | None = None,
) -> list[dict[str, Any]]:
    missions = load_missions()
    if status:
        missions = [m for m in missions if m["status"] == status]
    if priority:
        missions = [m for m in missions if m["priority"] == priority]
    if company:
        missions = [m for m in missions if m["company"].lower() == company.lower()]
    if source:
        missions = [m for m in missions if m["source"] == source]
    return sorted(missions, key=lambda x: ("critical", "standard", "routine").index(x["priority"]))


def get_stats() -> dict[str, Any]:
    missions = load_missions()
    return {
        "total": len(missions),
        "active": sum(1 for m in missions if m["status"] == "active"),
        "blocked": sum(1 for m in missions if m["status"] == "blocked"),
        "completed": sum(1 for m in missions if m["status"] == "completed"),
        "critical": sum(1 for m in missions if m["priority"] == "critical" and m["status"] != "completed"),
        "by_source": {
            "web": sum(1 for m in missions if m["source"] == "web"),
            "discord": sum(1 for m in missions if m["source"] == "discord"),
            "agent": sum(1 for m in missions if m["source"] == "agent"),
        },
        "avg_pct_complete": (
            sum(m["pct_complete"] for m in missions) / len(missions) if missions else 0
        ),
    }


def format_for_discord(mission: dict[str, Any]) -> str:
    """Format a mission for Discord display."""
    priority_emoji = {"critical": "🔴", "standard": "🟠", "routine": "🟢"}[mission["priority"]]
    status_emoji = {
        "draft": "📝", "active": "🚀", "blocked": "🛑",
        "completed": "✅", "archived": "📦",
    }[mission["status"]]

    lines = [
        f"**{priority_emoji} {mission['title']}**",
        f"ID: `{mission['mission_id']}`",
        f"Status: {status_emoji} {mission['status']} | Complete: {mission['pct_complete']}%",
        f"Priority: {mission['priority']}",
        f"Company: {mission['company'] or 'N/A'}",
        f"Source: {mission['source']}",
        f"Created: {mission['created_at'][:10]}",
        f"Assigned: {', '.join(mission['assigned_staff']) if mission['assigned_staff'] else 'Unassigned'}",
    ]
    if mission["due_date"]:
        lines.append(f"Due: {mission['due_date']}")
    if mission["blockers"]:
        lines.append(f"Blockers: {mission['blockers']}")
    if mission["description"]:
        lines.append(f"\n{mission['description']}")
    return "\n".join(lines)
