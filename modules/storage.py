"""Centralized storage and Google Drive sync."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

# Local storage paths
TAN_EXECUTIVE_ROOT = Path.home() / "tan-executive"
COMPANIES_DIR = TAN_EXECUTIVE_ROOT / "companies"
DASHBOARD_FILE = TAN_EXECUTIVE_ROOT / "dashboard.json"

# Google Drive paths (synced via gdrive or similar)
GDRIVE_ROOT = Path.home() / "gdrive" / "tan-executive"


def ensure_dirs() -> None:
    """Create all required directories."""
    COMPANIES_DIR.mkdir(parents=True, exist_ok=True)
    GDRIVE_ROOT.mkdir(parents=True, exist_ok=True)


def sync_to_drive(local_path: Path, drive_subpath: str) -> bool:
    """Sync a local file to Google Drive."""
    try:
        drive_dest = GDRIVE_ROOT / drive_subpath
        drive_dest.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["cp", "-r", str(local_path), str(drive_dest)],
            timeout=30, check=True
        )
        return True
    except Exception:
        return False


def save_state(state: dict) -> None:
    """Save company state locally and sync to drive."""
    ensure_dirs()
    company = state.get("company", "unknown")
    slug = company.lower().replace(" ", "-")
    
    local_path = COMPANIES_DIR / slug / "state.json"
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(json.dumps(state, indent=2))
    
    # Sync to drive
    sync_to_drive(local_path, f"companies/{slug}/state.json")


def load_state(company: str) -> dict | None:
    """Load company state."""
    slug = company.lower().replace(" ", "-")
    local_path = COMPANIES_DIR / slug / "state.json"
    if local_path.exists():
        return json.loads(local_path.read_text())
    return None


def save_dashboard(states: list[dict]) -> None:
    """Save centralized dashboard."""
    ensure_dirs()
    summary = [{
        "company": s.get("company", "unknown"),
        "vertical": s.get("vertical", ""),
        "status": s.get("status", ""),
        "iteration": s.get("iteration", 0),
        "current_task": s.get("current_task"),
        "blocked_count": len(s.get("blocked_on_user", [])),
        "completed_count": len(s.get("completed_tasks", [])),
        "total_tasks": 12,
        "updated_at": s.get("updated_at", ""),
    } for s in states]
    DASHBOARD_FILE.write_text(json.dumps(summary, indent=2))
    sync_to_drive(DASHBOARD_FILE, "dashboard.json")


def load_dashboard() -> list[dict]:
    """Load dashboard."""
    if DASHBOARD_FILE.exists():
        return json.loads(DASHBOARD_FILE.read_text())
    return []


def get_company_list() -> list[str]:
    """Get list of all companies."""
    if not COMPANIES_DIR.exists():
        return []
    return [d.name for d in COMPANIES_DIR.iterdir() if d.is_dir()]


def get_company_status(company: str) -> dict | None:
    """Get status of a specific company."""
    return load_state(company)
