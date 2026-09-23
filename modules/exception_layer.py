"""Human exception layer — defines who owns what decisions.
From Avid: 'Humans own strategy, policy, risk, budget, ambiguity, and the final release decision.
Agents own routine execution, coordination, testing, documentation, and policy-bounded decisions.'
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DecisionOwner(str, Enum):
    HUMAN = "human"         # Human must decide
    AGENT = "agent"         # Agent can decide within policy bounds
    HYBRID = "hybrid"       # Agent recommends, human approves


class RiskLevel(str, Enum):
    LOW = "low"             # Routine, reversible
    MEDIUM = "medium"       # Some cost or time impact
    HIGH = "high"           # Significant financial or strategic impact
    CRITICAL = "critical"   # Existential or legal risk


@dataclass
class DecisionRule:
    """Rule for who decides what."""
    category: str
    description: str
    owner: DecisionOwner
    risk_level: RiskLevel
    agent_authority: str = ""   # What the agent CAN decide
    human_triggers: list[str] = field(default_factory=list)  # When to escalate to human
    examples: list[str] = field(default_factory=list)


# Canonical decision rules — Peña doctrine + Avid's human exception layer
DECISION_RULES = [
    DecisionRule(
        category="strategy",
        description="Company direction, market positioning, M&A strategy",
        owner=DecisionOwner.HUMAN,
        risk_level=RiskLevel.HIGH,
        agent_authority="Can analyze and recommend, cannot commit",
        human_triggers=["Any strategic pivot", "New market entry", "Acquisition targets"],
        examples=["Should we enter Texas market?", "Should we buy Company X?"],
    ),
    DecisionRule(
        category="policy",
        description="Company policies, standard operating procedures, hiring guidelines",
        owner=DecisionOwner.HYBRID,
        risk_level=RiskLevel.MEDIUM,
        agent_authority="Can draft and propose within doctrine bounds",
        human_triggers=["Policy exceptions", "Non-standard situations", "Personnel issues"],
        examples=["Standard hiring process", "Vendor selection criteria"],
    ),
    DecisionRule(
        category="risk",
        description="Risk management, insurance, compliance, legal exposure",
        owner=DecisionOwner.HUMAN,
        risk_level=RiskLevel.CRITICAL,
        agent_authority="Can identify and flag risks, cannot approve acceptance",
        human_triggers=["All material risks", "Legal issues", "Insurance claims"],
        examples=["Cyber liability exposure", "E&O claims", "Regulatory changes"],
    ),
    DecisionRule(
        category="budget",
        description="Capital allocation, spending limits, financial commitments",
        owner=DecisionOwner.HUMAN,
        risk_level=RiskLevel.HIGH,
        agent_authority="Can track, report, and flag variances",
        human_triggers=["Any unbudgeted expense", "Overrun >10%", "Capital calls"],
        examples=["Quarterly budget approval", "Emergency spend >$5k"],
    ),
    DecisionRule(
        category="ambiguity",
        description="Novel situations, unclear doctrine, conflicting signals",
        owner=DecisionOwner.HUMAN,
        risk_level=RiskLevel.MEDIUM,
        agent_authority="Can identify ambiguity and present options",
        human_triggers=["No clear doctrine match", "Multiple valid interpretations"],
        examples=["Unusual deal structure", "First-time situation"],
    ),
    DecisionRule(
        category="execution",
        description="Routine execution of defined workflows and SOPs",
        owner=DecisionOwner.AGENT,
        risk_level=RiskLevel.LOW,
        agent_authority="Full authority within SOP bounds",
        human_triggers=["SOP deviation required", "Exception to standard process"],
        examples=["Daily deal sourcing", "SOP execution", "Standard reporting"],
    ),
    DecisionRule(
        category="coordination",
        description="Cross-functional coordination, handoffs, status tracking",
        owner=DecisionOwner.AGENT,
        risk_level=RiskLevel.LOW,
        agent_authority="Full authority for routine coordination",
        human_triggers=["Coordination failures", "Owner unavailable"],
        examples=["Task handoffs", "Meeting scheduling", "Status updates"],
    ),
    DecisionRule(
        category="testing",
        description="Quality assurance, evidence verification, gate reviews",
        owner=DecisionOwner.AGENT,
        risk_level=RiskLevel.LOW,
        agent_authority="Full authority to verify and document",
        human_triggers=["Test failures", "Edge cases not covered by criteria"],
        examples=["Checklist completion", "Evidence review", "Gate sign-off"],
    ),
    DecisionRule(
        category="documentation",
        description="Documentation, filing, knowledge management",
        owner=DecisionOwner.AGENT,
        risk_level=RiskLevel.LOW,
        agent_authority="Full authority for routine documentation",
        human_triggers=["Sensitive information", "Legal documents"],
        examples=["Meeting notes", "Filing SOPs", "Updating brain"],
    ),
    DecisionRule(
        category="release",
        description="Final release/ship decision — all gates must agree",
        owner=DecisionOwner.HUMAN,
        risk_level=RiskLevel.CRITICAL,
        agent_authority="Can aggregate gate reports, cannot approve release",
        human_triggers=["Final release decision", "Any gate failure"],
        examples=["Product launch", "Acquisition close", "Major feature ship"],
    ),
]


def get_rule(category: str) -> DecisionRule | None:
    """Get decision rule by category."""
    for rule in DECISION_RULES:
        if rule.category == category:
            return rule
    return None


def who_decides(category: str, context: dict[str, Any] = None) -> dict[str, Any]:
    """Determine who should decide a given issue."""
    rule = get_rule(category)
    if not rule:
        return {
            "owner": DecisionOwner.HUMAN,
            "reason": f"No rule found for category '{category}' — default to human",
            "agent_can": "Identify and present options",
            "human_must": "Make final decision",
        }
    
    return {
        "owner": rule.owner.value,
        "risk_level": rule.risk_level.value,
        "agent_can": rule.agent_authority,
        "human_must": rule.human_triggers,
        "description": rule.description,
    }


def build_exception_layer_md() -> str:
    """Build markdown summary of the exception layer."""
    lines = [
        "# Human Exception Layer",
        "",
        "Defines who owns what decisions in an AI-native company.",
        "",
        "**Source:** Peña doctrine + 'Humans on the loop, not in every loop' (Avid @av1dlive)",
        "",
        "## Decision Rules",
        "",
    ]
    
    for rule in DECISION_RULES:
        lines.append(f"### {rule.category.upper()} ({rule.owner.value})")
        lines.append(f"**Description:** {rule.description}")
        lines.append(f"**Risk Level:** {rule.risk_level.value}")
        lines.append(f"**Agent Can:** {rule.agent_authority}")
        lines.append(f"**Human Must:** {', '.join(rule.human_triggers) if rule.human_triggers else 'N/A'}")
        if rule.examples:
            lines.append(f"**Examples:** {', '.join(rule.examples)}")
        lines.append("")
    
    lines.extend([
        "## Operating Principles",
        "",
        "1. **Agents own routine, humans own exceptions** — normal workflows run without human relay",
        "2. **Policy-bounded authority** — agents decide within doctrine-approved bounds",
        "3. **Escalation by rule, not by default** — agent escalates only when triggers are hit",
        "4. **Humans set strategy, agents execute** — the division is clean and auditable",
        "5. **All exceptions are logged** — patterns in exceptions improve the rules over time",
        "",
    ])
    
    return "\n".join(lines)
