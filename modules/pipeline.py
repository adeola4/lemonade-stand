"""Deal pipeline tracker — moves deals from sourced to closed.
Tracks every deal through Peña's 11 stages.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from modules.outreach import OutreachPlan


@dataclass
class DealRecord:
    name: str
    stage: str = "sourced"
    vertical: str = ""
    geo: str = ""
    estimated_value: str = "TBD"
    owner_name: str = "Unknown"
    outreach_plan: dict | None = None
    red_flags: list = field(default_factory=list)
    scorecard: dict | None = None
    action_plan: dict | None = None
    notes: str = ""
    next_action: str = ""
    next_action_date: str = ""


# Pipeline stages (from Peña)
PIPELINE_STAGES = [
    "sourced",           # Step 1: Identified
    "researched",        # Steps 2-3: Generalities + Specifics
    "scored",            # Step 5: Preliminary decision
    "commit_pending",    # Step 4: Commit (needs human)
    "outreach_sent",     # Contact made
    "meeting_scheduled", # Meeting set
    "meeting_done",      # First meeting complete
    "nda_signed",        # NDA in place
    "loi_drafted",       # Letter of intent
    "loi_negotiated",    # LOI terms being negotiated
    "loi_signed",        # LOI accepted
    "diligence",         # Due diligence phase
    "purchase_agreement",# PA drafted
    "closing",           # Final closing
    "closed",            # Deal complete
    "on_hold",           # Paused (with reason)
    "killed",            # Dead (with reason)
]


def load_pipeline(company: str) -> list[dict]:
    """Load pipeline for a company."""
    pipeline_path = Path(f"~/tan-executive/companies/{company}/pipeline.json").expanduser()
    if pipeline_path.exists():
        with open(pipeline_path) as f:
            return json.load(f)
    return []


def save_pipeline(company: str, deals: list[dict]) -> None:
    """Save pipeline for a company."""
    pipeline_path = Path(f"~/tan-executive/companies/{company}/pipeline.json").expanduser()
    pipeline_path.parent.mkdir(parents=True, exist_ok=True)
    with open(pipeline_path, 'w') as f:
        json.dump(deals, f, indent=2, default=str)


def add_deal(company: str, deal: DealRecord) -> None:
    """Add a deal to the pipeline."""
    deals = load_pipeline(company)
    
    # Check for duplicates
    for existing in deals:
        if existing.get("name") == deal.name and existing.get("stage") != "killed":
            return  # Already tracked
    
    deals.append({
        "name": deal.name,
        "stage": deal.stage,
        "vertical": deal.vertical,
        "geo": deal.geo,
        "estimated_value": deal.estimated_value,
        "owner_name": deal.owner_name,
        "outreach_plan": deal.outreach_plan,
        "red_flags": deal.red_flags,
        "scorecard": deal.scorecard,
        "action_plan": deal.action_plan,
        "notes": deal.notes,
        "next_action": deal.next_action,
        "next_action_date": deal.next_action_date,
    })
    
    save_pipeline(company, deals)


def advance_stage(company: str, deal_name: str, new_stage: str, notes: str = "") -> bool:
    """Move a deal to a new stage."""
    deals = load_pipeline(company)
    
    for deal in deals:
        if deal.get("name") == deal_name:
            old_stage = deal.get("stage", "")
            deal["stage"] = new_stage
            deal["notes"] += f"\n[{new_stage}]: {notes}"
            save_pipeline(company, deals)
            return True
    
    return False


def get_pipeline_summary(company: str) -> dict:
    """Get summary of pipeline status."""
    deals = load_pipeline(company)
    
    stage_counts = {}
    for stage in PIPELINE_STAGES:
        stage_counts[stage] = sum(1 for d in deals if d.get("stage") == stage)
    
    return {
        "company": company,
        "total_deals": len(deals),
        "by_stage": stage_counts,
        "active_deals": [d for d in deals if d.get("stage") not in ("closed", "killed")],
        "needs_action": [d for d in deals if d.get("next_action") and d.get("stage") not in ("closed", "killed")],
    }
