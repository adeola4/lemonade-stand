"""
Loop Master V1 — Loop Lifecycle State Machine

Implements the full state machine for autonomous loop execution.
Inspired by DeepCode's Turn lifecycle and agent-orchestrator's RunStatus.
"""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any, Dict, List, Optional


class LoopV1State(StrEnum):
    """Loop lifecycle states."""
    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"

    @property
    def is_terminal(self) -> bool:
        return self in {LoopV1State.COMPLETED, LoopV1State.FAILED}

    @property
    def is_active(self) -> bool:
        return self in {LoopV1State.PLANNING, LoopV1State.EXECUTING, LoopV1State.VERIFYING}

    @property
    def can_pause(self) -> bool:
        return self in {LoopV1State.PLANNING, LoopV1State.EXECUTING}

    @property
    def can_resume(self) -> bool:
        return self == LoopV1State.PAUSED


class RunStatus(StrEnum):
    """Individual run status within a loop."""
    QUEUED = "queued"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class LoopV1Run:
    """A single execution run of a loop."""
    id: str = field(default_factory=lambda: f"run_{uuid.uuid4().hex[:12]}")
    loop_id: str = ""
    status: RunStatus = RunStatus.QUEUED
    attempt: int = 0
    max_attempts: int = 3
    turns_used: int = 0
    max_turns: int = 50
    tokens_used: int = 0
    max_tokens: int = 100000
    cost_cents: float = 0.0
    output: Optional[str] = None
    error: Optional[str] = None
    trigger: str = "manual"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    next_run_at: Optional[str] = None
    evidence_refs: List[str] = field(default_factory=list)
    session_id: Optional[str] = None
    hit_turn_cap: bool = False
    hit_token_cap: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "LoopV1Run":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class LoopV1:
    """
    A goal-driven autonomous loop with completion criteria.

    Inherits patterns from:
    - DeepCode: ThreadGoal lifecycle, evidence refs, execution security
    - agent-orchestrator: budget guardrails, concurrency caps, retry/backoff
    """
    id: str = field(default_factory=lambda: f"loop_{uuid.uuid4().hex[:12]}")
    name: str = "Untitled Loop"
    description: str = ""
    goal: str = ""  # What this loop aims to achieve
    completion_criteria: str = ""  # How to know it's done
    state: LoopV1State = LoopV1State.PENDING
    priority: int = 2  # 1=low, 2=normal, 3=high, 4=critical

    # Execution config
    max_iterations: int = 100
    current_iteration: int = 0
    max_turns_per_run: int = 50
    max_tokens_per_run: int = 100000
    max_wall_time_seconds: int = 3600

    # Scheduling
    cron: Optional[str] = None  # 5-field cron expression
    timezone: str = "UTC"
    enabled: bool = True

    # Guardrails
    requires_approval: bool = False
    monthly_budget_cents: Optional[float] = None
    est_run_cost_cents: float = 5.0

    # Session management
    current_session_id: Optional[str] = None
    auto_compact: bool = True
    compact_threshold: float = 0.9

    # Multi-agent orchestration
    orchestrator_id: Optional[str] = None
    goal_setter_prompt: str = ""
    planner_prompt: str = ""
    executor_prompt: str = ""
    verifier_prompt: str = ""

    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_run_at: Optional[str] = None
    next_scheduled_at: Optional[str] = None
    total_runs: int = 0
    total_successes: int = 0
    total_failures: int = 0
    total_tokens_used: int = 0
    total_cost_cents: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["state"] = self.state.value
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "LoopV1":
        data["state"] = LoopV1State(data.get("state", "pending"))
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class LoopV1Store:
    """Persistent storage for V1 loops."""

    STORAGE_PATH = os.path.expanduser("~/tan-executive/loop_master/v1/loops.json")

    def __init__(self):
        self.loops: Dict[str, LoopV1] = {}
        self.runs: Dict[str, LoopV1Run] = {}
        self._load()

    def _load(self):
        if os.path.exists(self.STORAGE_PATH):
            try:
                with open(self.STORAGE_PATH, "r") as f:
                    data = json.load(f)
                for loop_data in data.get("loops", []):
                    loop = LoopV1.from_dict(loop_data)
                    self.loops[loop.id] = loop
                for run_data in data.get("runs", []):
                    run = LoopV1Run.from_dict(run_data)
                    self.runs[run.id] = run
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        os.makedirs(os.path.dirname(self.STORAGE_PATH), exist_ok=True)
        with open(self.STORAGE_PATH, "w") as f:
            json.dump({
                "loops": [loop.to_dict() for loop in self.loops.values()],
                "runs": [run.to_dict() for run in self.runs.values()],
                "saved_at": datetime.now(timezone.utc).isoformat()
            }, f, indent=2, default=str)

    def create(self, loop: LoopV1) -> LoopV1:
        self.loops[loop.id] = loop
        self._save()
        return loop

    def get(self, loop_id: str) -> Optional[LoopV1]:
        return self.loops.get(loop_id)

    def list_all(self, state: Optional[LoopV1State] = None) -> List[LoopV1]:
        loops = list(self.loops.values())
        if state:
            loops = [l for l in loops if l.state == state]
        return sorted(loops, key=lambda l: (-l.priority, l.created_at))

    def update(self, loop_id: str, **kwargs) -> Optional[LoopV1]:
        loop = self.loops.get(loop_id)
        if not loop:
            return None
        for key, value in kwargs.items():
            if hasattr(loop, key):
                setattr(loop, key, value)
        loop.updated_at = datetime.now(timezone.utc).isoformat()
        self._save()
        return loop

    def delete(self, loop_id: str) -> bool:
        if loop_id in self.loops:
            del self.loops[loop_id]
            # Also delete associated runs
            self.runs = {k: v for k, v in self.runs.items() if v.loop_id != loop_id}
            self._save()
            return True
        return False

    def add_run(self, run: LoopV1Run) -> LoopV1Run:
        self.runs[run.id] = run
        self._save()
        return run

    def get_run(self, run_id: str) -> Optional[LoopV1Run]:
        return self.runs.get(run_id)

    def list_runs(self, loop_id: str) -> List[LoopV1Run]:
        return [r for r in self.runs.values() if r.loop_id == loop_id]

    def get_active_runs(self) -> List[LoopV1Run]:
        return [r for r in self.runs.values() if r.status == RunStatus.RUNNING]


def get_v1_store() -> LoopV1Store:
    """Get the global V1 store instance."""
    if not hasattr(get_v1_store, "_instance"):
        get_v1_store._instance = LoopV1Store()
    return get_v1_store._instance
