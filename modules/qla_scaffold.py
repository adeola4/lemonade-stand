"""QLA Company Scaffold Builder — restructures folders around Peña's methodology."""
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone

from modules.qla_framework import all_qla_folders, QLAFolder
from modules.contract import write_contract_templates
from modules.task_board import save_board, create_task, TaskState, WORKFLOW_TASK_TEMPLATES
from modules.exception_layer import build_exception_layer_md


def build_qla_scaffold(company_path: Path, vertical: str, company: str) -> None:
    """Build the QLA-structured company scaffold."""
    
    # Create QLA folders
    for folder in all_qla_folders():
        folder_path = company_path = company_path / f"{folder.number}_{folder.name}"
        folder_path.mkdir(parents=True, exist_ok=True)
        
        # README.md
        readme = _build_readme(folder, vertical, company)
        (folder_path / "README.md").write_text(readme, encoding="utf-8")
        
        # actions.md
        actions = _build_actions(folder, vertical, company)
        (folder_path / "actions.md").write_text(actions, encoding="utf-8")
        
        # workflow.md
        workflow = _build_workflow(folder, vertical, company)
        (folder_path / "workflow.md").write_text(workflow, encoding="utf-8")
        
        # checklist.md
        checklist = _build_checklist(folder, vertical, company)
        (folder_path / "checklist.md").write_text(checklist, encoding="utf-8")
    
    # Build AGENT_TECH with QLA-specific config
    agent_tech = company_path / "12_AGENT_TECH"
    write_contract_templates(agent_tech / "contracts")
    
    # Agent config
    config = {
        "company": company,
        "vertical": vertical,
        "qla_enabled": True,
        "knowledge_brain_search": True,
        "exception_layer": "12_AGENT_TECH/exception_layer.md",
        "task_board": "task_board.json",
        "contracts_dir": "12_AGENT_TECH/contracts",
        "phases": ["foundation", "positioning", "sourcing", "financing", "execution", "harvest"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (agent_tech / "agent_config.yaml").write_text(json.dumps(config, indent=2))
    
    # Exception layer
    (agent_tech / "exception_layer.md").write_text(build_exception_layer_md())
    
    # Self-healing log
    (agent_tech / "self_healing_log.md").write_text(
        "# Self-Healing Log\n\n"
        "Every error, diagnosis, and fix is logged here.\n\n"
        "Format:\n"
        "- Error: <what failed>\n"
        "- Root Cause: <why it failed>\n"
        "- Fix: <what was done>\n"
        "- QLA Principle: <which principle was violated>\n\n"
    )
    
    # Fix library
    (agent_tech / "fix_library.md").write_text(
        "# Fix Library\n\n"
        "Known fixes for recurring problems.\n\n"
        "| Error | Fix | QLA Principle |\n"
        "|---|---|---|\n"
        "| Jina 403 on X | Fall back to api.fxtwitter.com | Be prepared |\n"
        "| SQL column missing | Drop + recreate table | Investigate before invest |\n"
        "| Module not found | Set PYTHONPATH | Structure follows strategy |\n"
    )
    
    # Create task board with deal sourcing workflow
    board = {}
    for tmpl in WORKFLOW_TASK_TEMPLATES.get("deal_sourcing", []):
        task_id = tmpl["task_id"]
        create_task(
            board, task_id,
            objective=tmpl["objective"],
            owner=tmpl["owner"],
            acceptance_criteria=tmpl["acceptance_criteria"],
            test_requirements=tmpl.get("test_requirements", ""),
            evidence_requirements=tmpl.get("evidence_requirements", ""),
            dependencies=tmpl.get("dependencies", []),
        )
    save_board(company_path, board)
    
    # Runbook
    (company_path / "12_AGENT_TECH" / "RUNBOOK.md").write_text(
        f"# RUNBOOK — {company}\n\n"
        f"## What This Folder Contains\n"
        f"Everything an AI agent needs to operate this company using Peña's QLA methodology.\n\n"
        f"## How to Use\n"
        f"1. Read `state.json` for current status\n"
        f"2. Read `task_board.json` for workflow state\n"
        f"3. Read `12_AGENT_TECH/contracts/` for agent roles\n"
        f"4. Read `12_AGENT_TECH/exception_layer.md` for decision rules\n"
        f"5. Follow the 12-phase QLA process\n\n"
        f"## QLA Operating Rules\n"
        f"- All decisions must be doctrine-grounded (Knowledge Brain)\n"
        f"- All tasks must have evidence before completion\n"
        f"- All escalations must cite the specific QLA rule triggered\n"
        f"- All exceptions are logged for pattern analysis\n"
        f"- Perception is reality — structure follows strategy\n"
        f"- Investigate before you invest — always\n"
    )


def _build_readme(folder: QLAFolder, vertical: str, company: str) -> str:
    """Build README.md for a QLA folder."""
    lines = [
        f"# {folder.number}_{folder.name}",
        "",
        f"**QLA Phase:** {folder.qla_phase}",
        f"**Company:** {company}",
        f"**Vertical:** {vertical}",
        "",
        f"## Description",
        folder.description,
        "",
        f"## Purpose",
        f"This folder contains everything needed to execute the **{folder.name}** phase of your QLA journey.",
        "",
        f"## Key Actions",
    ]
    for action in folder.core_actions[:5]:
        lines.append(f"- {action}")
    lines.append("")
    lines.append(f"## Knowledge Brain Tags")
    lines.append(f"Search the Knowledge Brain for: {', '.join(folder.knowledge_brain_tags)}")
    lines.append("")
    lines.append("## Files")
    lines.append("- `README.md` — This file")
    lines.append("- `actions.md` — Specific action items from Peña's methodology")
    lines.append("- `workflow.md` — Step-by-step workflow for this phase")
    lines.append("- `checklist.md` — Progress tracking checklist")
    lines.append("")
    
    return "\n".join(lines)


def _build_actions(folder: QLAFolder, vertical: str, company: str) -> str:
    """Build actions.md for a QLA folder."""
    lines = [
        f"# Actions — {folder.name}",
        "",
        f"**QLA Phase:** {folder.qla_phase}",
        "",
        "## Core Actions (from Peña's Methodology)",
        "",
    ]
    for i, action in enumerate(folder.core_actions, 1):
        lines.append(f"{i}. **{action}**")
        lines.append(f"   - Status: ☐ Pending")
        lines.append(f"   - QLA Source: Knowledge Brain")
        lines.append("")
    
    lines.append("## Custom Actions")
    lines.append("")
    lines.append("_Add company-specific actions below_")
    lines.append("")
    
    return "\n".join(lines)


def _build_workflow(folder: QLAFolder, vertical: str, company: str) -> str:
    """Build workflow.md for a QLA folder."""
    lines = [
        f"# Workflow — {folder.name}",
        "",
        f"**QLA Phase:** {folder.qla_phase}",
        "",
        "## Process Overview",
        "",
        f"1. Review this phase's purpose in `README.md`",
        f"2. Execute actions in `actions.md` in order",
        f"3. Track progress in `checklist.md`",
        f"4. Record results in the executive loop",
        "",
        "## QLA Decision Rules",
        "",
        f"- Search Knowledge Brain before making any decision",
        f"- Apply the exception layer: agent handles routine, human handles strategy/risk",
        f"- Every action must cite its QLA principle source",
        f"- Escalate only when human-only data is required",
        "",
        "## Completion Criteria",
        "",
        f"- [ ] All core actions complete",
        f"- [ ] All checklists verified",
        f"- [ ] Evidence documented for each action",
        f"- [ ] Next phase can begin",
        "",
    ]
    
    return "\n".join(lines)


def _build_checklist(folder: QLAFolder, vertical: str, company: str) -> str:
    """Build checklist.md for a QLA folder."""
    lines = [
        f"# Checklist — {folder.name}",
        "",
        f"**QLA Phase:** {folder.qla_phase}",
        "",
        "## Progress Tracking",
        "",
    ]
    for action in folder.core_actions:
        lines.append(f"- [ ] {action}")
    lines.append("")
    lines.append("## Verification")
    lines.append("")
    lines.append(f"- [ ] All actions have evidence")
    lines.append(f"- [ ] QLA principles cited for each action")
    lines.append(f"- [ ] Exceptions logged if any")
    lines.append(f"- [ ] Next phase can proceed")
    lines.append("")
    
    return "\n".join(lines)
