"""Cost optimization layer — route simple commands to parsers, not LLMs.
From leopardracer: "Don't spend an expensive model call on a command a simple parser could handle."
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class Route(str, Enum):
    LOCAL = "local"       # Pattern-matched, no LLM needed
    LLM = "llm"           # Needs reasoning
    SKILL = "skill"       # Matches existing skill/procedure


@dataclass
class RouteDecision:
    route: Route
    confidence: float
    action: str
    params: dict
    reason: str


# Command patterns that can be handled locally
LOCAL_PATTERNS = [
    (r'^create task:\s*(.+)$', 'create_task'),
    (r'^assign\s+(.+?)\s+to\s+(.+)$', 'assign_task'),
    (r'^complete\s+(.+)$', 'complete_task'),
    (r'^delete\s+(.+)$', 'delete_item'),
    (r'^show\s+(.+)$', 'show_item'),
    (r'^status\s*(.*)$', 'show_status'),
    (r'^help$', 'show_help'),
    (r'^changelog$', 'show_changelog'),
    (r'^versions?$', 'show_versions'),
    (r'^rollback\s+(\d+)$', 'rollback'),
    (r'^snapshot$', 'create_snapshot'),
    (r'^brain\s+(.+)$', 'brain_ingest'),
    (r'^search\s+(.+)$', 'brain_search'),
    (r'^list$', 'brain_list'),
]


def route_command(input_text: str) -> RouteDecision:
    """Decide whether a command needs an LLM or can be handled locally."""
    text = input_text.strip()
    
    for pattern, action in LOCAL_PATTERNS:
        match = re.match(pattern, text, re.I)
        if match:
            groups = match.groups()
            return RouteDecision(
                route=Route.LOCAL,
                confidence=1.0,
                action=action,
                params={"groups": groups},
                reason=f"Pattern matched: {pattern}",
            )
    
    # Check if it matches a known skill
    if _matches_skill(text):
        return RouteDecision(
            route=Route.SKILL,
            confidence=0.9,
            action="run_skill",
            params={"query": text},
            reason="Matches existing skill/procedure",
        )
    
    # Default: needs LLM reasoning
    return RouteDecision(
        route=Route.LLM,
        confidence=0.5,
        action="reason_and_act",
        params={"query": text},
        reason="No pattern or skill match — needs reasoning",
    )


def _matches_skill(text: str) -> bool:
    """Check if text matches any known skill."""
    from modules.institutional_memory import has_skill
    return has_skill(text)


def estimate_cost(decision: RouteDecision) -> dict:
    """Estimate the cost of a routing decision."""
    costs = {
        Route.LOCAL: {"tokens": 0, "cost": 0.0, "latency": "instant"},
        Route.SKILL: {"tokens": 50, "cost": 0.001, "latency": "<1s"},
        Route.LLM: {"tokens": 1000, "cost": 0.01, "latency": "3-10s"},
    }
    return costs.get(decision.route, costs[Route.LLM])
