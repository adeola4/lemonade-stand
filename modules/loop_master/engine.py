"""
QLA Loop Master — Autonomous 24/7 Business Loop Engine
Manages hundreds of concurrent loops with full lifecycle control.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


class LoopStatus(str, Enum):
    """Possible states for a loop."""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    FROZEN = "frozen"
    ERROR = "error"
    COMPLETED = "completed"


class LoopPriority(int, Enum):
    """Priority levels for loop execution."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Loop:
    """A single autonomous loop."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    name: str = "Untitled Loop"
    description: str = ""
    status: LoopStatus = LoopStatus.STOPPED
    priority: LoopPriority = LoopPriority.NORMAL
    interval: int = 60  # seconds between iterations
    max_retries: int = 3
    retry_count: int = 0
    timeout: int = 300  # max seconds per iteration
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_run: Optional[str] = None
    last_error: Optional[str] = None
    run_count: int = 0
    success_count: int = 0
    error_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    # The function/callable this loop runs (stored as string reference for persistence)
    entry_point: str = ""
    params: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        d["priority"] = self.priority.value
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "Loop":
        data["status"] = LoopStatus(data.get("status", "stopped"))
        data["priority"] = LoopPriority(data.get("priority", 2))
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class LoopMaster:
    """
    Central engine that manages all autonomous loops.
    Handles creation, scheduling, execution, monitoring, and lifecycle.
    """

    STORAGE_PATH = os.path.expanduser("~/tan-executive/loop_master/loops.json")

    def __init__(self):
        self.loops: Dict[str, Loop] = {}
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._handlers: Dict[str, Callable] = {}  # entry_point -> callable
        self._load()

    def _load(self):
        """Load loops from disk."""
        if os.path.exists(self.STORAGE_PATH):
            try:
                with open(self.STORAGE_PATH, "r") as f:
                    data = json.load(f)
                for loop_data in data.get("loops", []):
                    loop = Loop.from_dict(loop_data)
                    self.loops[loop.id] = loop
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        """Persist loops to disk."""
        os.makedirs(os.path.dirname(self.STORAGE_PATH), exist_ok=True)
        with open(self.STORAGE_PATH, "w") as f:
            json.dump({
                "loops": [loop.to_dict() for loop in self.loops.values()],
                "saved_at": datetime.now(timezone.utc).isoformat()
            }, f, indent=2)

    def register_handler(self, name: str, handler: Callable):
        """Register a callable that a loop can execute."""
        self._handlers[name] = handler

    def create_loop(
        self,
        name: str,
        description: str = "",
        entry_point: str = "",
        params: Optional[Dict[str, Any]] = None,
        interval: int = 60,
        priority: LoopPriority = LoopPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Loop:
        """Create a new loop."""
        loop = Loop(
            name=name,
            description=description,
            entry_point=entry_point,
            params=params or {},
            interval=interval,
            priority=priority,
            metadata=metadata or {},
        )
        self.loops[loop.id] = loop
        self._save()
        return loop

    def get_loop(self, loop_id: str) -> Optional[Loop]:
        """Get a loop by ID."""
        return self.loops.get(loop_id)

    def list_loops(
        self,
        status: Optional[LoopStatus] = None,
        priority: Optional[LoopPriority] = None,
    ) -> List[Loop]:
        """List all loops, optionally filtered."""
        loops = list(self.loops.values())
        if status:
            loops = [l for l in loops if l.status == status]
        if priority:
            loops = [l for l in loops if l.priority == priority]
        return sorted(loops, key=lambda l: (l.priority.value * -1, l.created_at))

    def update_loop(self, loop_id: str, **kwargs) -> Optional[Loop]:
        """Update loop properties."""
        loop = self.loops.get(loop_id)
        if not loop:
            return None
        for key, value in kwargs.items():
            if hasattr(loop, key):
                setattr(loop, key, value)
        loop.updated_at = datetime.now(timezone.utc).isoformat()
        self._save()
        return loop

    def delete_loop(self, loop_id: str) -> bool:
        """Permanently delete a loop."""
        if loop_id in self._running_tasks:
            self._running_tasks[loop_id].cancel()
            del self._running_tasks[loop_id]
        if loop_id in self.loops:
            del self.loops[loop_id]
            self._save()
            return True
        return False

    def start_loop(self, loop_id: str) -> bool:
        """Start a loop (begin executing on interval)."""
        loop = self.loops.get(loop_id)
        if not loop:
            return False
        if loop.status == LoopStatus.RUNNING:
            return True
        loop.status = LoopStatus.RUNNING
        loop.retry_count = 0
        loop.updated_at = datetime.now(timezone.utc).isoformat()
        self._save()
        return True

    def stop_loop(self, loop_id: str) -> bool:
        """Stop a loop permanently."""
        loop = self.loops.get(loop_id)
        if not loop:
            return False
        if loop_id in self._running_tasks:
            self._running_tasks[loop_id].cancel()
            del self._running_tasks[loop_id]
        loop.status = LoopStatus.STOPPED
        loop.updated_at = datetime.now(timezone.utc).isoformat()
        self._save()
        return True

    def pause_loop(self, loop_id: str) -> bool:
        """Pause a loop (can be resumed)."""
        loop = self.loops.get(loop_id)
        if not loop or loop.status != LoopStatus.RUNNING:
            return False
        if loop_id in self._running_tasks:
            self._running_tasks[loop_id].cancel()
            del self._running_tasks[loop_id]
        loop.status = LoopStatus.PAUSED
        loop.updated_at = datetime.now(timezone.utc).isoformat()
        self._save()
        return True

    def freeze_loop(self, loop_id: str) -> bool:
        """Freeze a loop (no execution, preserved state)."""
        loop = self.loops.get(loop_id)
        if not loop:
            return False
        if loop_id in self._running_tasks:
            self._running_tasks[loop_id].cancel()
            del self._running_tasks[loop_id]
        loop.status = LoopStatus.FROZEN
        loop.updated_at = datetime.now(timezone.utc).isoformat()
        self._save()
        return True

    def resume_loop(self, loop_id: str) -> bool:
        """Resume a paused/frozen loop."""
        loop = self.loops.get(loop_id)
        if not loop or loop.status not in (LoopStatus.PAUSED, LoopStatus.FROZEN):
            return False
        loop.status = LoopStatus.RUNNING
        loop.updated_at = datetime.now(timezone.utc).isoformat()
        self._save()
        return True

    def run_loop_now(self, loop_id: str) -> bool:
        """Trigger an immediate execution of a loop (one-shot)."""
        loop = self.loops.get(loop_id)
        if not loop or loop.status != LoopStatus.RUNNING:
            return False
        # In async context, we'd schedule this. For now, mark last_run.
        loop.last_run = datetime.now(timezone.utc).isoformat()
        loop.run_count += 1
        self._save()
        return True

    def get_stats(self) -> Dict[str, Any]:
        """Get aggregate statistics across all loops."""
        total = len(self.loops)
        by_status = {}
        for status in LoopStatus:
            count = sum(1 for l in self.loops.values() if l.status == status)
            by_status[status.value] = count
        total_runs = sum(l.run_count for l in self.loops.values())
        total_errors = sum(l.error_count for l in self.loops.values())
        return {
            "total": total,
            "by_status": by_status,
            "total_runs": total_runs,
            "total_errors": total_errors,
            "success_rate": (
                f"{((total_runs - total_errors) / total_runs * 100):.1f}%"
                if total_runs > 0 else "N/A"
            ),
        }

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get full data for the web dashboard."""
        # Import and integrate new modules
        try:
            from .adaptive_interval import get_adaptive_engine
            adaptive_data = {
                "adaptive_intervals": get_adaptive_engine().get_all_reports(),
            }
        except ImportError:
            adaptive_data = {"adaptive_intervals": []}

        try:
            from .dependency_graph import get_dependency_engine
            dep_data = {
                "dependency_graph": get_dependency_engine().get_dependency_report(),
            }
        except ImportError:
            dep_data = {"dependency_graph": {}}

        try:
            from .metrics import get_metrics_engine
            metrics_data = {
                "metrics_summary": get_metrics_engine().get_dashboard_summary(),
            }
        except ImportError:
            metrics_data = {"metrics_summary": {}}

        try:
            from .self_healing import get_self_healing_engine
            healing_data = {
                "healing_summary": get_self_healing_engine().get_health_summary(),
            }
        except ImportError:
            healing_data = {"healing_summary": {}}

        try:
            from .notifications import get_notification_engine
            notif_data = {
                "recent_notifications": get_notification_engine().get_notification_log(20),
            }
        except ImportError:
            notif_data = {"recent_notifications": []}

        try:
            from .template_library import get_template_library
            tmpl_data = {
                "template_catalog": get_template_library().get_catalog(),
            }
        except ImportError:
            tmpl_data = {"template_catalog": {}}

        try:
            from .scheduler import get_scheduling_engine
            sched_data = {
                "scheduler_summary": get_scheduling_engine().get_scheduler_summary(),
            }
        except ImportError:
            sched_data = {"scheduler_summary": {}}

        try:
            from .resource_monitor import get_resource_monitor
            res_data = {
                "resource_status": get_resource_monitor().get_status_report(),
            }
        except ImportError:
            res_data = {"resource_status": {}}

        base_data = {
            "stats": self.get_stats(),
            "loops": [loop.to_dict() for loop in self.list_loops()],
            "registered_handlers": list(self._handlers.keys()),
        }

        return {**base_data, **adaptive_data, **dep_data, **metrics_data, **healing_data, **notif_data, **tmpl_data, **sched_data, **res_data}

    def get_loop_metrics(self, loop_id: str) -> Optional[Dict[str, Any]]:
        """Get metrics for a specific loop (via metrics module)."""
        from .metrics import get_metrics_engine
        return get_metrics_engine().get_loop_metrics(loop_id)

    def get_adaptive_interval(self, loop_id: str, current_interval: int, target_interval: Optional[int] = None) -> Tuple[int, str]:
        """Get adaptive interval suggestion for a loop."""
        from .adaptive_interval import get_adaptive_engine
        return get_adaptive_engine().suggest_interval(loop_id, current_interval, target_interval)

    def check_self_healing(self, loop_id: str) -> Dict[str, Any]:
        """Check self-healing status and recommendations for a loop."""
        from .self_healing import get_self_healing_engine
        engine = get_self_healing_engine()
        can_execute, reason = engine.can_execute(loop_id)
        recommendation = engine.get_recommended_action(loop_id)
        health = engine.get_health_summary(loop_id)
        return {
            "can_execute": can_execute,
            "reason": reason,
            "recommendation": recommendation,
            "health": health,
        }

    def check_resource_throttle(self, loop_id: str, priority: int) -> Dict[str, Any]:
        """Check if a loop should be throttled due to resource pressure."""
        from .resource_monitor import get_resource_monitor
        decision = get_resource_monitor().should_run_loop(loop_id, priority)
        return {
            "should_run": decision.should_run,
            "throttle_level": decision.throttle_level.value,
            "reason": decision.reason,
            "suggested_delay": decision.suggested_delay,
        }

    def get_execution_queue(self, loop_ids: List[str]) -> List[Dict[str, Any]]:
        """Get prioritized execution queue with scheduler integration."""
        from .scheduler import get_scheduling_engine
        return get_scheduling_engine().get_execution_queue(loop_ids)
