"""Checkpoint tracker — saves progress to disk and posts updates to Discord/Telegram."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .storage import save_state, save_dashboard, load_state, load_dashboard


def log_checkpoint(company: str, task: str, details: str = "") -> dict:
    """Log a checkpoint for a company."""
    state = load_state(company)
    if not state:
        return {"error": f"No state for {company}"}
    
    checkpoint = {
        "task": task,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "details": details,
        "iteration": state.get("iteration", 0),
    }
    
    if "checkpoints" not in state:
        state["checkpoints"] = []
    state["checkpoints"].append(checkpoint)
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    save_state(state)
    return checkpoint


def post_update_to_discord(company: str, message: str, channel_id: str | None = None) -> bool:
    """Post update to Discord channel."""
    try:
        import subprocess
        cmd = ["python3", "-c", f"""
import sys, json
sys.path.insert(0, "/home/ubuntu/.hermes/skills/messaging-channels")
try:
    from discord_messaging import send_message
    result = send_message({json.dumps(channel_id or "TAN")}, {json.dumps(message)})
    print(result)
except Exception as e:
    print(f"Discord send failed: {{e}}")
"""]
        subprocess.run(cmd, timeout=20, check=False, capture_output=True)
        return True
    except Exception:
        return False


def format_checkpoint_message(company: str, task: str, iteration: int, status: str, details: str = "") -> str:
    """Format a checkpoint message for posting."""
    emoji_map = {
        "complete": "✅",
        "building": "🔄",
        "blocked_on_user": "⏸️",
        "error": "❌",
    }
    emoji = emoji_map.get(status, "📋")
    
    lines = [
        f"{emoji} **{company}** — {task}",
        f"Iteration {iteration} | Status: {status}",
    ]
    if details:
        lines.append(f"Details: {details}")
    
    return "\n".join(lines)


def notify_user_request(company: str, questions: list[str]) -> str:
    """Format a user data request message."""
    lines = [
        f"⏸️ **{company}** — Needs your input",
        "",
        "I need the following to continue building accurately:",
        "",
    ]
    for i, q in enumerate(questions, 1):
        lines.append(f"{i}. {q}")
    lines.append("")
    lines.append("Reply with the details and I'll continue building.")
    
    return "\n".join(lines)


def complete_company(company: str) -> dict:
    """Mark a company as complete."""
    state = load_state(company)
    if not state:
        return {"error": f"No state for {company}"}
    
    state["status"] = "complete"
    state["completed_at"] = datetime.now(timezone.utc).isoformat()
    state["current_task"] = None
    
    save_state(state)
    
    # Update dashboard
    from .executive_loop import load_all_states
    save_dashboard(load_all_states())
    
    return {"status": "complete", "company": company, "iterations": state.get("iteration", 0)}
