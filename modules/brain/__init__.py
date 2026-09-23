"""AI Brain — ingestion, routing, and institutional memory.

Two-brain architecture:
- Knowledge Brain: source doctrine (Dan Peña's Your First $100M) — the soul
- AI Brain: ingests data + code, bolts it on, routes commands, remembers how the company works
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

# Knowledge Brain — the doctrine
KNOWLEDGE_BRAIN_MD = Path("/tmp/lemonade_doctrine.md")
DOCTRINE_INDEX = Path.home() / ".hermes" / "skills" / "lemonade-stand" / "modules" / "data" / "doctrine.json"

# AI Brain — the ingestion + memory system
AI_BRAIN_DB = Path.home() / "tan-executive" / "ai-brain" / "ai_brain.db"
COMPANIES_ROOT = Path.home() / "tan-executive" / "companies"


def knowledge_brain_status() -> dict:
    """Check the Knowledge Brain status."""
    return {
        "name": "Knowledge Brain",
        "source": "Dan Peña — Your First $100 Million",
        "path": str(KNOWLEDGE_BRAIN_MD),
        "exists": KNOWLEDGE_BRAIN_MD.exists(),
        "size": KNOWLEDGE_BRAIN_MD.stat().st_size if KNOWLEDGE_BRAIN_MD.exists() else 0,
        "purpose": "Source doctrine — the foundational truth all decisions are measured against",
    }


def ai_brain_status() -> dict:
    """Check the AI Brain status."""
    from modules.brain.ingest import list_all
    items = list_all()
    return {
        "name": "AI Brain",
        "path": str(AI_BRAIN_DB),
        "ingested_items": len(items),
        "recent": items[:5] if items else [],
        "capabilities": [
            "Ingests X threads, GitHub repos, articles, PDFs",
            "Classifies TAN_QLA / MARKETING / GENESIS / GENERAL relevance",
            "Auto-tags doctrine references",
            "Stores institutional memory (Skills)",
            "Routes commands: local pattern match → skill → LLM",
            "Provides cockpit dashboard view",
        ],
        "purpose": "Ingests data + code, bolts it on, learns how your company works",
    }


def both_brains_status() -> dict:
    """Get status of both brains."""
    return {
        "knowledge_brain": knowledge_brain_status(),
        "ai_brain": ai_brain_status(),
        "interaction": "AI Brain searches Knowledge Brain first, then its own ingested content, then web",
    }
