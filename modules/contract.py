"""Agent contract system — formalizes every agent with scope, authority, and rules.
From the Avid article: 'Give each agent a name, scope, inputs, outputs, authority,
escalation rules, and definition of done. Otherwise the company has a chat list, not an org chart.'
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class AgentContract:
    """Formal agent contract — replaces informal agent_config.yaml"""
    name: str
    owns: str                          # workflow or outcome
    receives: str                      # trigger and required context
    produces: str                      # artifact and next action
    can_decide: str                    # policy-bounded authority
    escalates: str                     # exceptions and risk conditions
    done_means: str                    # observable acceptance criteria
    scope: str = ""                    # scope description
    inputs: str = ""                   # explicit inputs
    outputs: str = ""                  # explicit outputs
    authority: str = ""                # decision authority
    escalation_rules: str = ""         # when to escalate
    definition_of_done: str = ""       # acceptance criteria
    tools: list[str] = field(default_factory=list)  # tools this agent can use
    evidence_required: bool = True     # requires evidence at each gate

    def to_dict(self) -> dict:
        return asdict(self)


# Default executive agent contracts based on the Raft model
DEFAULT_CONTRACTS = {
    "chief_of_staff": AgentContract(
        name="Chief of Staff",
        owns="Company operating cadence — turns intent into executable work",
        receives="Company goals, board decisions, cross-functional status",
        produces="Prioritized task list, status reports, escalation alerts",
        can_decide="Task assignment, routine scheduling, progress tracking",
        escalates="Budget changes, strategic pivots, personnel decisions, risk events",
        done_means="All active workflows have clear owners and next actions",
        scope="Orchestration. Does not execute specialist work.",
        tools=["task_tracker", "channel", "board", "evidence_log"],
        evidence_required=True,
    ),
    "deal_lead": AgentContract(
        name="Deal Lead",
        owns="Deal flow — sourcing, qualification, negotiation, close",
        receives="Target list, criteria, authority limits, market data",
        produces="Qualified pipeline, LOI drafts, due diligence packages",
        can_decide="Initial outreach, qualification screening, standard LOI terms",
        escalates="Non-standard terms, price above authority, legal issues",
        done_means="Signed LOI with verified financials and clear path to close",
        tools=["crm", "financial_model", "loi_templates", "due_diligence_checklist"],
        evidence_required=True,
    ),
    "operations_lead": AgentContract(
        name="Operations Lead",
        owns="Day-to-day operations across all portfolio companies",
        receives="SOPs, performance metrics, exception reports",
        produces="Updated SOPs, performance dashboards, escalation summaries",
        can_decide="Routine process adjustments, staffing within budget, vendor selection",
        escalates="Budget overruns, SOP violations, safety incidents",
        done_means="All KPIs within range, all SOPs current, all escalations resolved",
        tools=["kpi_dashboard", "sop_library", "vendor_db"],
        evidence_required=True,
    ),
    "research_lead": AgentContract(
        name="Research Lead",
        owns="Market intelligence, competitive analysis, opportunity identification",
        receives="Research questions, market segments, competitive targets",
        produces="Research briefs, opportunity reports, competitive analysis",
        can_decide="Research methodology, source selection, initial filtering",
        escalates="Findings requiring strategic response, market shifts",
        done_means="Research brief with citations, confidence rating, and recommendation",
        tools=["web_search", "doctrine_index", "brain_db"],
        evidence_required=True,
    ),
    "finance_lead": AgentContract(
        name="Finance Lead",
        owns="Financial modeling, capital structure, investor reporting",
        receives="Deal terms, financial statements, performance data",
        produces="Models, reports, investor updates, compliance filings",
        can_decide="Standard modeling assumptions, report formatting, routine filings",
        escalates="Non-standard structures, material changes, regulatory questions",
        done_means="Model reviewed, assumptions documented, sources cited",
        tools=["financial_model", "reporting_template", "compliance_checklist"],
        evidence_required=True,
    ),
}


def get_contract(role: str) -> AgentContract:
    """Get the contract for a role."""
    return DEFAULT_CONTRACTS.get(role)


def all_contracts() -> dict[str, AgentContract]:
    """Get all default contracts."""
    return DEFAULT_CONTRACTS


def write_contract_templates(path: Path) -> None:
    """Write contract templates to a directory."""
    path.mkdir(parents=True, exist_ok=True)
    for role, contract in DEFAULT_CONTRACTS.items():
        out = path / f"{role}_contract.json"
        out.write_text(json.dumps(contract.to_dict(), indent=2))
