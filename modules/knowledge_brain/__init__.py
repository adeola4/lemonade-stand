"""Knowledge Brain — search the 3,010-item Peña doctrine database.
Every deal decision, workflow, and action item traces back to this source.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def load_knowledge_brain() -> list[dict]:
    """Load the master extraction file."""
    kb_path = Path(__file__).resolve().parent.parent.parent / "data" / "YOUR_FIRST_100M_MASTER_EXTRACTION.md"
    if not kb_path.exists():
        return []
    
    with open(kb_path) as f:
        content = f.read()
    
    items = []
    current_category = ""
    
    for line in content.split('\n'):
        # Detect category headers
        if line.startswith('## '):
            current_category = line[3:].strip()
            continue
        
        # Parse item lines: **ID** | text | *chapter*
        match = re.match(r'\*\*([A-Z]+\d+)\*\*\s*\|\s*(.*?)\s*\|\s*\*(.*?)\*', line)
        if match:
            items.append({
                "id": match.group(1),
                "text": match.group(2).strip(),
                "chapter": match.group(3).strip(),
                "category": current_category,
            })
    
    return items


def search_knowledge_brain(query: str, limit: int = 10) -> list[dict]:
    """Search the Knowledge Brain for relevant Peña principles."""
    items = load_knowledge_brain()
    query_lower = query.lower()
    
    # Score each item by relevance
    scored = []
    for item in items:
        text = item.get("text", "").lower()
        score = 0
        
        # Exact word matches
        for word in query_lower.split():
            if word in text:
                score += 3
        
        # Phrase match
        if query_lower in text:
            score += 10
        
        # Category match
        if query_lower in item.get("category", "").lower():
            score += 5
        
        if score > 0:
            scored.append((score, item))
    
    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)
    
    return [item for _, item in scored[:limit]]


def get_action_items_for_phase(phase: str) -> list[dict]:
    """Get Peña's action items for a specific QLA phase."""
    items = load_knowledge_brain()
    
    # Map phases to relevant categories and chapters
    phase_keywords = {
        "foundation": ["Mindset", "Mission", "Vision", "Conditioning"],
        "positioning": ["Perception", "Strategy", "Consolidation"],
        "sourcing": ["Deal", "Negotiation", "Banking", "Flow"],
        "financing": ["Capital", "Financing", "OPM", "Leverage"],
        "execution": ["Execution", "Action", "Operations"],
        "harvest": ["Exit", "Valuation", "Harvest"],
    }
    
    keywords = phase_keywords.get(phase.lower(), [phase])
    
    results = []
    for item in items:
        category = item.get("category", "")
        chapter = item.get("chapter", "")
        for kw in keywords:
            if kw.lower() in category.lower() or kw.lower() in chapter.lower():
                results.append(item)
                break
    
    return results


def get_principles_by_category(category: str) -> list[dict]:
    """Get all principles from a specific category."""
    items = load_knowledge_brain()
    return [item for item in items if item.get("category", "").lower() == category.lower()]


def get_doctrine_summary(topic: str) -> str:
    """Get a summary of Peña's doctrine on a topic."""
    items = search_knowledge_brain(topic, limit=5)
    
    if not items:
        return f"No specific doctrine found for: {topic}"
    
    summary = f"## Peña's Doctrine on: {topic}\n\n"
    for item in items:
        summary += f"- **{item['id']}** ({item['category']}): {item['text']}\n"
    
    return summary


def get_qla_methodology_steps() -> list[dict]:
    """Get the 11-step deal process from the Knowledge Brain."""
    items = load_knowledge_brain()
    steps = []
    
    for item in items:
        text = item.get("text", "")
        if "step" in text.lower() and ("deal" in text.lower() or "acquisition" in text.lower()):
            steps.append(item)
    
    return steps


def get_action_items_count() -> dict:
    """Get count of action items by category."""
    items = load_knowledge_brain()
    counts = {}
    for item in items:
        cat = item.get("category", "Unknown")
        counts[cat] = counts.get(cat, 0) + 1
    return counts
