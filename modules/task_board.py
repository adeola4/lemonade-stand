"""Task board — durable handoffs with full lifecycle.
From Avid: 'A message is temporary. A task is durable.'
Tasks have objective, owner, acceptance criteria, dependencies, test requirements,
evidence requirements, and final status.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class TaskState(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    BLOCKED = "blocked"


@dataclass
class Task:
    """Durable task — lives beyond the chat that created it."""
    id: str
    objective: str
    owner: str
    acceptance_criteria: str
    state: TaskState = TaskState.TODO
    dependencies: list[str] = field(default_factory=list)
    test_requirements: str = ""
    evidence_requirements: str = ""
    evidence_provided: str = ""
    result_artifact: str = ""
    notes: str = ""
    created_at: str = ""
    updated_at: str = ""
    completed_at: str = ""
    exceptions: list[str] = field(default_factory=list)
    escalation_triggered: bool = False

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        self.updated_at = self.created_at

    def to_dict(self) -> dict:
        d = asdict(self)
        d["state"] = self.state.value
        return d

    def is_ready(self, all_tasks: dict[str, "Task"]) -> bool:
        """Check if all dependencies are done."""
        return all(
            all_tasks[dep].state == TaskState.DONE
            for dep in self.dependencies
            if dep in all_tasks
        )

    def can_start(self) -> bool:
        return self.state == TaskState.TODO

    def can_review(self) -> bool:
        return self.state == TaskState.IN_PROGRESS and self.evidence_provided

    def can_complete(self) -> bool:
        return self.state == TaskState.IN_REVIEW


def load_board(company_path: Path) -> dict[str, Task]:
    """Load task board for a company."""
    board_file = company_path / "task_board.json"
    if not board_file.exists():
        return {}
    data = json.loads(board_file.read_text())
    return {tid: Task(**t) for tid, t in data.items()}


def save_board(company_path: Path, tasks: dict[str, Task]) -> None:
    """Save task board for a company."""
    board_file = company_path / "task_board.json"
    board_file.write_text(json.dumps(
        {tid: t.to_dict() for tid, t in tasks.items()},
        indent=2
    ))


def create_task(board: dict[str, Task], task_id: str, objective: str, owner: str,
                acceptance_criteria: str, **kwargs) -> Task:
    """Add a new task to the board."""
    task = Task(
        id=task_id,
        objective=objective,
        owner=owner,
        acceptance_criteria=acceptance_criteria,
        **kwargs,
    )
    board[task_id] = task
    return task


def transition_task(board: dict[str, Task], task_id: str, new_state: TaskState,
                    note: str = "") -> Task:
    """Transition a task to a new state."""
    task = board[task_id]
    task.state = new_state
    task.updated_at = datetime.now(timezone.utc).isoformat()
    if note:
        task.notes += f"\n[{datetime.now(timezone.utc).isoformat()[:19]}] {note}"
    if new_state == TaskState.DONE:
        task.completed_at = datetime.now(timezone.utc).isoformat()
    return task


def get_next_todo(board: dict[str, Task]) -> Task | None:
    """Get next ready-to-start task."""
    for task in board.values():
        if task.can_start() and task.is_ready(board):
            return task
    return None


def get_blocked_tasks(board: dict[str, Task]) -> list[Task]:
    """Get tasks blocked on user (escalated)."""
    return [t for t in board.values() if t.escalation_triggered]


def get_workflow_metrics(board: dict[str, Task]) -> dict:
    """Get board metrics."""
    total = len(board)
    by_state = {}
    for t in board.values():
        s = t.state.value
        by_state[s] = by_state.get(s, 0) + 1
    blocked = len(get_blocked_tasks(board))
    done = by_state.get(TaskState.DONE.value, 0)
    return {
        "total": total,
        "by_state": by_state,
        "done": done,
        "blocked": blocked,
        "completion_pct": (done / total * 100) if total > 0 else 0,
    }


# Standard task templates per workflow stage
WORKFLOW_TASK_TEMPLATES = {
    "deal_sourcing": [
        {
            "task_id": "source_targets",
            "objective": "Source 20 qualified acquisition targets",
            "owner": "deal_lead",
            "acceptance_criteria": "20 companies with revenue >$1M, in target geo, verified financials",
            "test_requirements": "Financial data cross-referenced with at least 2 sources",
            "evidence_requirements": "Target list with revenue, location, ownership structure",
        },
        {
            "task_id": "qualify_targets",
            "objective": "Qualify top 10 targets to shortlist",
            "owner": "deal_lead",
            "acceptance_criteria": "10 companies passing Doofus Test with >70 qualification score",
            "dependencies": ["source_targets"],
            "test_requirements": "Qualification scorecard complete for all 20",
            "evidence_requirements": "Scorecards, notes, ranking rationale",
        },
    ],
    "operations_setup": [
        {
            "task_id": "draft_sops",
            "objective": "Draft core SOPs for recurring operations",
            "owner": "operations_lead",
            "acceptance_criteria": "10 SOPs covering all key workflows with checklist format",
            "test_requirements": "Each SOP has been walked through at least once",
            "evidence_requirements": "SOP files with last-reviewed date",
        },
    ],
    "build_loop": [
        {
            "task_id": "product_contract",
            "objective": "Write product contract with measurable acceptance criteria",
            "owner": "chief_of_staff",
            "acceptance_criteria": "Contract has: objective, constraints, acceptance criteria, test approach",
            "test_requirements": "Acceptance criteria are independently verifiable",
            "evidence_requirements": "Contract document with sign-off",
        },
        {
            "task_id": "red_tests",
            "objective": "Write failing tests before implementation (RED phase)",
            "owner": "research_lead",
            "acceptance_criteria": "Tests exist for all acceptance criteria and all currently fail",
            "dependencies": ["product_contract"],
            "test_requirements": "Test runner shows all tests failing with clear messages",
            "evidence_requirements": "Test output showing failures",
        },
        {
            "task_id": "implementation",
            "objective": "Implement to make tests pass (GREEN phase)",
            "owner": "research_lead",
            "acceptance_criteria": "All RED tests now pass",
            "dependencies": ["red_tests"],
            "test_requirements": "Test runner shows all tests passing",
            "evidence_requirements": "Test output showing passes",
        },
        {
            "task_id": "independent_qa",
            "objective": "Independent QA gate — verify implementation against contract",
            "owner": "chief_of_staff",
            "acceptance_criteria": "Independent review confirms all acceptance criteria met",
            "dependencies": ["implementation"],
            "test_requirements": "Reviewer who wrote the tests runs the verification",
            "evidence_requirements": "QA report with pass/fail per criterion",
        },
        {
            "task_id": "visual_review",
            "objective": "Visual/perception review — output matches doctrine-aligned brand",
            "owner": "chief_of_staff",
            "acceptance_criteria": "Output passes perception checklist (professional, clear, on-brand)",
            "dependencies": ["implementation"],
            "test_requirements": "Checklist complete with no critical items failed",
            "evidence_requirements": "Completed perception checklist",
        },
        {
            "task_id": "release_decision",
            "objective": "Release decision — all gates must agree",
            "owner": "chief_of_staff",
            "acceptance_criteria": "All 4 gates (tests, QA, visual, process) report green",
            "dependencies": ["independent_qa", "visual_review"],
            "test_requirements": "All gate reports are current and green",
            "evidence_requirements": "Release record with all gate results",
        },
    ],
}
