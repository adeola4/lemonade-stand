"""Discord thread management — create a new thread for each deal/company
so the team can organize each business in its own channel."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class DealThread:
    """A Discord thread created for a specific deal."""
    thread_id: str
    thread_name: str
    company: str
    deal_name: str
    parent_channel_id: str
    created_at: str
    pinned_message_id: str | None = None
    status: str = "active"


# Default parent channel — the "lemonade-stand" thread's parent
# TAN LAB #1 SUPERCOMPUTER / lemonade-stand
DEFAULT_PARENT_CHANNEL_ID = "1530412763166281748"
DEFAULT_GUILD_ID = "1527322778615677059"


def create_deal_thread(
    company: str,
    deal_name: str,
    approach: str = "",
    parent_channel_id: str = DEFAULT_PARENT_CHANNEL_ID,
    guild_id: str = DEFAULT_GUILD_ID,
) -> DealThread:
    """Create a new Discord thread for a deal.
    
    In production, this calls the Discord API via the discord tool.
    For now, it prepares the metadata and the caller invokes the tool.
    """
    thread_name = f"{company} — {deal_name}"
    if approach:
        thread_name += f" ({approach})"
    
    return DealThread(
        thread_id="",  # filled by Discord API after creation
        thread_name=thread_name,
        company=company,
        deal_name=deal_name,
        parent_channel_id=parent_channel_id,
        created_at="",  # filled after creation
    )


def generate_thread_pillow_message(company: str, deal_name: str, approach: str, vertical: str, geo: str) -> str:
    """Generate the initial pinned message for a deal thread."""
    lines = [
        f"🍋 **LEMONADE STAND — NEW DEAL THREAD**",
        f"",
        f"**Company:** {company}",
        f"**Deal:** {deal_name}",
        f"**Approach:** {approach}" if approach else "",
        f"**Vertical:** {vertical}" if vertical else "",
        f"**Geography:** {geo}" if geo else "",
        f"",
        f"---",
        f"",
        f"**QLA Knowledge Base methodology will execute here.**",
        f"",
        f"Use this thread to:",
        f"• Track deal progress step-by-step",
        f"• Store documents, LOIs, research",
        f"• Coordinate outreach and follow-ups",
        f"• Update pipeline status",
        f"",
        f"```",
        f"python main.py execute --company \"{company}\" --vertical \"{vertical}\" --geo \"{geo}\" --idea \"{deal_name}\"",
        f"```",
    ]
    return "\n".join(lines)


def get_thread_for_deal(company: str, deal_name: str) -> str:
    """Get the thread name for a deal."""
    return f"{company} — {deal_name}"
