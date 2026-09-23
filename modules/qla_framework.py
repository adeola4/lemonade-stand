"""QLA Framework — Maps company folders to Dan Peña's methodology.

The 12-step executive loop is restructured around Peña's actual QLA methodology,
not generic business folders. Each folder maps to a specific QLA phase with
action items extracted directly from the Knowledge Brain.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

KNOWLEDGE_BRAIN = Path.home() / ".hermes" / "skills" / "tan-executive-agent" / "data" / "YOUR_FIRST_100M_MASTER_EXTRACTION.md"


@dataclass
class QLAFolder:
    """A folder in the QLA company scaffold."""
    number: str
    name: str
    qla_phase: str
    description: str
    knowledge_brain_tags: list[str]  # Tags to search for in the Knowledge Brain
    core_actions: list[str]  # Pre-built action items from Peña
    workflows: list[dict] = field(default_factory=list)


# QLA Methodology Folder Structure
QLA_FOLDERS = [
    QLAFolder(
        number="00",
        name="MISSION_VISION",
        qla_phase="Phase 1: Foundation",
        description="QLA mission rooted in Peña's Expectations of Super Success",
        knowledge_brain_tags=["M", "mission", "vision", "super success"],
        core_actions=[
            "Write your Quantum Leap mission using Peña's 'masterful illusion' framework",
            "Define your Expectations of Super Success (M16)",
            "Establish your Pay-Price-to-Action — what you will sacrifice (M33)",
            "Commit publicly to the project (D6)",
            "Write your 100M vision statement using Peña's dream-big framework",
        ],
    ),
    QLAFolder(
        number="01",
        name="MINDSET_CONDITIONING",
        qla_phase="Phase 1: Foundation",
        description="Expand comfort zone and condition high-performance mindset",
        knowledge_brain_tags=["M", "mindset", "comfort zone", "high performance"],
        core_actions=[
            "Complete Peña's Doofus Test self-assessment (Appendix B)",
            "Identify your comfort zone boundaries — plan to expand them (M20, M21)",
            "Study the Five Credos and integrate into daily operations",
            "Practice 'simulation' — rehearse scenarios before they happen (M21)",
            "Adopt the 'double your failure rate' philosophy (M11)",
            "Eliminate conventional wisdom from your decision-making process (M9)",
        ],
    ),
    QLAFolder(
        number="02",
        name="PERCEPTION_MANAGEMENT",
        qla_phase="Phase 2: Positioning",
        description="Build perception that creates reality — image as weapon",
        knowledge_brain_tags=["PER", "perception", "illusion", "image"],
        core_actions=[
            "Design your 'masterful illusion' — make success seem inevitable (M35)",
            "Audit your image against Peña's 'first 30 seconds' rule",
            "Build perception of value before the substance exists",
            "Use Patton's principle: act as if it's already done",
            "Structure follows strategy — design org to project success (M30)",
            "Create physical/digital presence that commands premium pricing",
        ],
    ),
    QLAFolder(
        number="03",
        name="STRATEGY_CONSOLIDATION",
        qla_phase="Phase 2: Positioning",
        description="Find fragmented industries and execute quantum consolidation",
        knowledge_brain_tags=["S", "strategy", "consolidation", "acquisition", "fragment"],
        core_actions=[
            "Identify 10 fragmented industries dominated by mom-and-pops (D15)",
            "Screen for 20-40% margins and owner-operators looking to exit",
            "Map the 11-step deal process for each target industry (D2)",
            "Build a quantum growth thesis: arithmetic growth is unacceptable (D11)",
            "Define your 'stick to your knitting' boundaries (D13)",
            "Plan the second acquisition that complements the first (D20)",
        ],
    ),
    QLAFolder(
        number="04",
        name="DEAL_FLOW",
        qla_phase="Phase 3: Sourcing",
        description="Execute Peña's 11-step deal methodology",
        knowledge_brain_tags=["D", "deal", "11 steps", "investigation", "red flag"],
        core_actions=[
            "Implement the full 11-step deal process (D2):",
            "  Step 1: Identify targets via industry research",
            "  Step 2: Investigate generalities — market size, trends, competition",
            "  Step 3: Investigate specifics — financials, ownership, operations",
            "  Step 4: Commit publicly to the project",
            "  Step 5: Preliminary decision — go/no-go with criteria",
            "  Step 6: Investigation continues — deep due diligence",
            "  Step 7: Action Plan — timeline, resources, milestones",
            "  Step 8: Critical Path — identify dependencies and blockers",
            "  Step 9: Implement — execute the plan",
            "  Step 10: Execute — manage and monitor progress",
            "  Step 11: Review — assess results and adjust",
            "Build red-flag checklist from Appendix C for every target (D4)",
            "Maintain deal pipeline with weekly two-presentation minimum (PI: two presentations a week)",
        ],
    ),
    QLAFolder(
        number="05",
        name="NEGOTIATION_BANKING",
        qla_phase="Phase 3: Sourcing",
        description="Master Peña's negotiation tactics and banker relationships",
        knowledge_brain_tags=["N", "negotiation", "bank", "lender", "OPM"],
        core_actions=[
            "Map the other party's comfort zone before every negotiation (PI: comfort zone)",
            "Define your Pay-Price-to-Action — know your walk-away point (D8)",
            "Never share a doubt — maintain unwavering confidence (D7)",
            "Build romance with 3-5 bankers using Peña's 'banker psychology' framework",
            "Approach lenders with structured deals, not desperation",
            "Use seller financing as default — OPM over own capital",
            "When the first red flag appears, exit immediately (D4)",
        ],
    ),
    QLAFolder(
        number="06",
        name="CAPITAL_STACK",
        qla_phase="Phase 4: Financing",
        description="Structure capital using Peña's OPM frameworks",
        knowledge_brain_tags=["C", "capital", "financing", "OPM", "leverage"],
        core_actions=[
            "Structure capital stack: minimal equity, maximum OPM",
            "Never use operating funds for equity contribution (D19)",
            "Target 80%+ seller financing or lender capital",
            "Build relationships with community banks, not just money centers",
            "Prepare the 'banker package' — Peña's romance documents",
            "Maintain clean financials and transparent communication with lenders",
            "Plan for stress — give ulcers, don't get them (D17)",
        ],
    ),
    QLAFolder(
        number="07",
        name="DREAM_TEAM",
        qla_phase="Phase 4: Financing",
        description="Build accountability board and specialist team",
        knowledge_brain_tags=["T", "team", "board", "director", "hire"],
        core_actions=[
            "Establish Board of Directors with 3-5 independent members",
            "Hire for Doofus Test — no exceptions (Appendix B)",
            "Demand employees pay themselves first — including you (PI: pay yourself first)",
            "Build dream team with equity participation where possible",
            "Apply the 'clean break' rule — no hooks for failed hires",
            "Outside advisors: accounting, legal, industry experts (PI: trusted advisors)",
        ],
    ),
    QLAFolder(
        number="08",
        name="OPERATIONS_EXCELLENCE",
        qla_phase="Phase 5: Execution",
        description="Run the business with Peña's high-performance systems",
        knowledge_brain_tags=["E", "execution", "action", "plan", "implement"],
        core_actions=[
            "Implement the 21-hour rule: act within 21 hours of a decision",
            "Maintain a 'no Plan B' mentality — total commitment",
            "Daily war room: metrics, blockers, next actions",
            "Quarterly strategy reviews with Board of Directors",
            "Track: time from signal to decision, completed workflows per human, escalation rate",
            "Create order from chaos — daily discipline over inspiration",
        ],
    ),
    QLAFolder(
        number="09",
        name="RESEARCH_INTELLIGENCE",
        qla_phase="Phase 5: Execution",
        description="Deep vertical research using Peña's investigate-before-you-invest framework",
        knowledge_brain_tags=["E", "investigation", "research", "market"],
        core_actions=[
            "Maintain active intelligence on 3-5 target industries",
            "Investigate before you invest — the more you investigate, the less you invest (M32)",
            "Build target lists of 50+ candidates per industry",
            "Track hiring activity, job postings, and expansion signals",
            "Maintain competitive intelligence on other consolidators",
            "Monthly industry deep-dives with actionable findings",
        ],
    ),
    QLAFolder(
        number="10",
        name="EXIT_VALUATION",
        qla_phase="Phase 6: Harvest",
        description="Plan and execute Peña's grand exit strategy",
        knowledge_brain_tags=["exit", "sell", "valuation", "grand exit"],
        core_actions=[
            "Design exit strategy from Day 1 — structure the company to sell",
            "Build perception of value that exceeds reality",
            "Maintain clean books and transparent operations",
            "Diversify customer base to reduce concentration risk",
            "Time the market — sell into strength, not weakness",
            "Target 3-5x EBITDA multiple minimum for consolidation plays",
            "Prepare 'sample letters' package from Appendix M",
        ],
    ),
    QLAFolder(
        number="11",
        name="PENA_ISMS_LIBRARY",
        qla_phase="Reference",
        description="Living library of 170+ Peña-isms applied to your company",
        knowledge_brain_tags=["PI", "peña-ism", "quote"],
        core_actions=[
            "Study Peña-isms daily — integrate into decision-making",
            "Post top 10 Peña-isms in your workspace",
            "Reference Peña-isms during strategy sessions",
            "Add new Peña-isms as you discover them",
            "Apply 'If you want things to change, first you have to change' to your operations",
        ],
    ),
    QLAFolder(
        number="12",
        name="AGENT_TECH",
        qla_phase="Infrastructure",
        description="AI agent configuration, contracts, and self-healing",
        knowledge_brain_tags=[],
        core_actions=[
            "Configure agent contracts with QLA-specific authority levels",
            "Set up Knowledge Brain search integration for all executive decisions",
            "Establish exception layer: agent handles routine, human handles strategy/risk",
            "Build institutional memory (Skills) for recurring QLA workflows",
            "Self-healing: every mistake becomes a new rule in the fix library",
        ],
    ),
]


def get_qla_folder(number: str) -> QLAFolder | None:
    """Get a QLA folder by number."""
    for f in QLA_FOLDERS:
        if f.number == number:
            return f
    return None


def all_qla_folders() -> list[QLAFolder]:
    """Get all QLA folders."""
    return QLA_FOLDERS
