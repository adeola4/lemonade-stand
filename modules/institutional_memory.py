"""Institutional memory — Skills that encode how the company does things.
From leopardracer: "Skills give the agent a memory of how your company likes a job done."
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SKILLS: dict[str, dict] = {
    "sales_research": {
        "name": "Sales Research",
        "description": "Research a prospect company before a sales call",
        "steps": [
            "Find the company website, LinkedIn profile, recent news and funding history.",
            "Review current job postings, customer reviews and recent leadership changes.",
            "Identify the company's likely problems and map them to our product.",
            "Write the findings into the company record and prepare three talking points for the call.",
        ],
        "rules": [
            "Never invent information.",
            "Never contact the prospect directly.",
            "Flag deals above €50,000 for review.",
        ],
        "trigger": ["research", "prospect", "sales call", "company research"],
    },
    "deal_sourcing": {
        "name": "Deal Sourcing",
        "description": "Source and qualify acquisition targets",
        "steps": [
            "Identify target criteria: revenue >$1M, in target geo, owner looking to exit.",
            "Search databases and marketplaces for matching companies.",
            "Qualify each target against Doofus Test criteria.",
            "Rank by fit and flag top 10 for outreach.",
        ],
        "rules": [
            "Must verify financials from at least 2 sources.",
            "Never reach out without qualification score >70.",
        ],
        "trigger": ["source targets", "deal flow", "acquisition targets"],
    },
    "candidate_screening": {
        "name": "Candidate Screening",
        "description": "Screen a job candidate against role requirements",
        "steps": [
            "Review CV against must-have requirements.",
            "Check references for past performance indicators.",
            "Assess culture fit using Five Credos alignment.",
            "Write screening report with hire/no-hire recommendation.",
        ],
        "rules": [
            "Never skip reference check.",
            "Flag any candidate who fails Doofus Test.",
        ],
        "trigger": ["screen candidate", "job applicant", "hiring"],
    },
}


def has_skill(query: str) -> bool:
    """Check if a query matches any known skill."""
    query_lower = query.lower()
    for skill in SKILLS.values():
        for trigger in skill.get("trigger", []):
            if trigger in query_lower:
                return True
    return False


def get_skill(name: str) -> dict | None:
    """Get a skill by name/key."""
    return SKILLS.get(name)


def find_matching_skills(query: str) -> list[dict]:
    """Find skills that match a query."""
    query_lower = query.lower()
    matches = []
    for key, skill in SKILLS.items():
        for trigger in skill.get("trigger", []):
            if trigger in query_lower:
                matches.append({"key": key, **skill})
                break
    return matches


def add_skill(key: str, name: str, description: str, steps: list[str],
               rules: list[str], trigger: list[str]) -> None:
    """Add a new skill to institutional memory."""
    SKILLS[key] = {
        "name": name,
        "description": description,
        "steps": steps,
        "rules": rules,
        "trigger": trigger,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def record_improvement(skill_key: str, mistake: str, fix: str) -> None:
    """Record a mistake-driven improvement to a skill."""
    if skill_key not in SKILLS:
        return
    if "improvements" not in SKILLS[skill_key]:
        SKILLS[skill_key]["improvements"] = []
    SKILLS[skill_key]["improvements"].append({
        "date": datetime.now(timezone.utc).isoformat(),
        "mistake": mistake,
        "fix": fix,
    })
