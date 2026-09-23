"""
Loop Master V1 — Multi-Agent Orchestration

Goal-setter, planner, executor, verifier roles.
Inspired by DeepCode's GoalRuntime and agent-orchestrator's architecture.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Callable, Dict, List, Optional


class AgentRole(StrEnum):
    """Roles in the multi-agent loop orchestration."""
    GOAL_SETTER = "goal_setter"
    PLANNER = "planner"
    EXECUTOR = "executor"
    VERIFIER = "verifier"


@dataclass
class AgentTask:
    """A task for an agent role."""
    id: str = field(default_factory=lambda: f"task_{uuid.uuid4().hex[:12]}")
    role: AgentRole = AgentRole.EXECUTOR
    loop_id: str = ""
    run_id: str = ""
    prompt: str = ""
    result: Optional[str] = None
    status: str = "pending"  # pending, running, completed, failed
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "role": self.role.value,
            "loop_id": self.loop_id,
            "run_id": self.run_id,
            "prompt": self.prompt,
            "result": self.result,
            "status": self.status,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "metadata": self.metadata,
        }


class AgentOrchestrator:
    """
    Coordinates the four agent roles in loop execution.
    
    Flow:
    1. Goal-Setter: Defines/refines the goal
    2. Planner: Breaks goal into executable steps
    3. Executor: Runs each step, collects evidence
    4. Verifier: Reviews evidence, certifies completion
    """

    # Default prompts for each role
    DEFAULT_GOAL_SETTER_PROMPT = (
        "You are a GOAL SETTER. Your job is to take a high-level objective "
        "and define clear, measurable completion criteria.\n\n"
        "Output a JSON object with:\n"
        "- 'goal': clear statement of what to achieve\n"
        "- 'criteria': list of specific, testable completion criteria\n"
        "- 'constraints': any boundaries or limitations"
    )

    DEFAULT_PLANNER_PROMPT = (
        "You are a PLANNER. Your job is to break a goal into executable steps.\n\n"
        "Output a JSON array of steps, each with:\n"
        "- 'action': what to do\n"
        "- 'tool': which tool to use (if any)\n"
        "- 'expected_outcome': what success looks like\n"
        '- "evidence_how": how to collect evidence of completion'
    )

    DEFAULT_EXECUTOR_PROMPT = (
        "You are an EXECUTOR. Your job is to execute steps and collect evidence.\n\n"
        "For each step:\n"
        "1. Execute the action using available tools\n"
        "2. Record what happened (success/failure/output)\n"
        "3. Collect evidence according to the plan\n"
        "4. Report results back to the orchestrator"
    )

    DEFAULT_VERIFIER_PROMPT = (
        "You are a VERIFIER. Your job is to independently verify completion.\n\n"
        "Review the evidence and determine:\n"
        "- Does the evidence support the completion claim?\n"
        "- Are all completion criteria satisfied?\n"
        "- Are there any gaps or concerns?\n\n"
        "Output: PASSED, FAILED, or INCONCLUSIVE with reason."
    )

    def __init__(self):
        self._handlers: Dict[AgentRole, Callable] = {}
        self._tasks: Dict[str, AgentTask] = {}

    def register_handler(self, role: AgentRole, handler: Callable) -> None:
        """Register a handler for an agent role."""
        self._handlers[role] = handler

    def get_handler(self, role: AgentRole) -> Optional[Callable]:
        """Get the handler for a role."""
        return self._handlers.get(role)

    def create_task(
        self,
        role: AgentRole,
        loop_id: str,
        run_id: str,
        prompt: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentTask:
        """Create a new task for an agent role."""
        task = AgentTask(
            role=role,
            loop_id=loop_id,
            run_id=run_id,
            prompt=prompt,
            metadata=metadata or {},
        )
        self._tasks[task.id] = task
        return task

    def complete_task(self, task_id: str, result: str) -> Optional[AgentTask]:
        """Mark a task as completed with result."""
        task = self._tasks.get(task_id)
        if task:
            task.result = result
            task.status = "completed"
            task.completed_at = datetime.now(timezone.utc).isoformat()
        return task

    def fail_task(self, task_id: str, error: str) -> Optional[AgentTask]:
        """Mark a task as failed."""
        task = self._tasks.get(task_id)
        if task:
            task.result = error
            task.status = "failed"
            task.completed_at = datetime.now(timezone.utc).isoformat()
        return task

    def get_tasks_for_run(self, run_id: str) -> List[AgentTask]:
        """Get all tasks for a run."""
        return [t for t in self._tasks.values() if t.run_id == run_id]

    def get_tasks_for_loop(self, loop_id: str) -> List[AgentTask]:
        """Get all tasks for a loop."""
        return [t for t in self._tasks.values() if t.loop_id == loop_id]

    def get_orchestration_prompt(self, role: AgentRole) -> str:
        """Get the default prompt for a role."""
        prompts = {
            AgentRole.GOAL_SETTER: self.DEFAULT_GOAL_SETTER_PROMPT,
            AgentRole.PLANNER: self.DEFAULT_PLANNER_PROMPT,
            AgentRole.EXECUTOR: self.DEFAULT_EXECUTOR_PROMPT,
            AgentRole.VERIFIER: self.DEFAULT_VERIFIER_PROMPT,
        }
        return prompts.get(role, "You are an agent. Complete the task.")

    def orchestrate_run(
        self,
        loop: Any,
        run: Any,
    ) -> Dict[str, Any]:
        """
        Create the full orchestration plan for a loop run.
        Returns a plan dict with tasks for each role.
        """
        plan = {
            "loop_id": loop.id,
            "run_id": run.id,
            "goal": loop.goal,
            "completion_criteria": loop.completion_criteria,
            "tasks": [],
        }

        # Goal Setter task
        goal_task = self.create_task(
            role=AgentRole.GOAL_SETTER,
            loop_id=loop.id,
            run_id=run.id,
            prompt=f"Define clear completion criteria for:\n\nGoal: {loop.goal}\n\nExisting criteria: {loop.completion_criteria}",
        )
        plan["tasks"].append(goal_task.to_dict())

        # Planner task
        planner_task = self.create_task(
            role=AgentRole.PLANNER,
            loop_id=loop.id,
            run_id=run.id,
            prompt=f"Create an executable plan for:\n\nGoal: {loop.goal}\nCriteria: {loop.completion_criteria}",
        )
        plan["tasks"].append(planner_task.to_dict())

        # Executor task(s) - one per anticipated step
        executor_task = self.create_task(
            role=AgentRole.EXECUTOR,
            loop_id=loop.id,
            run_id=run.id,
            prompt=f"Execute the plan for: {loop.goal}",
        )
        plan["tasks"].append(executor_task.to_dict())

        # Verifier task
        verifier_task = self.create_task(
            role=AgentRole.VERIFIER,
            loop_id=loop.id,
            run_id=run.id,
            prompt=f"Verify completion of: {loop.goal}\n\nCriteria: {loop.completion_criteria}",
        )
        plan["tasks"].append(verifier_task.to_dict())

        return plan


def get_orchestrator() -> AgentOrchestrator:
    """Get the global agent orchestrator instance."""
    if not hasattr(get_orchestrator, "_instance"):
        get_orchestrator._instance = AgentOrchestrator()
    return get_orchestrator._instance
