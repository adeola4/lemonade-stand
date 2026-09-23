"""
Loop Master Daemon — 24/7 process manager for autonomous loop execution.

Runs as a background thread, polls running loops every second, and fires
due iterations through the executor. Supports graceful start/stop and
persists execution history for the UI.

This is synchronous (threading-based) to stay compatible with the existing
storage layer without asyncio migration.
"""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .engine import LoopMaster, LoopStatus
from .executor import LoopExecutor, ExecutionResult, get_executor


class LoopDaemon:
    """
    Background daemon that executes running loops on their intervals.
    
    Usage:
        daemon = LoopDaemon(engine, executor)
        daemon.start()  # starts background thread
        daemon.stop()   # graceful shutdown
    """

    def __init__(
        self,
        engine: LoopMaster,
        executor: Optional[LoopExecutor] = None,
        tick_interval: float = 1.0,
        max_concurrent: int = 3,
        history_file: str = "~/tan-executive/loop_master/execution_history.json",
    ):
        self.engine = engine
        self.executor = executor or get_executor()
        self.tick_interval = tick_interval
        self.max_concurrent = max_concurrent
        self.history_file = Path(history_file).expanduser()
        self.history_file.parent.mkdir(parents=True, exist_ok=True)

        self._shutdown_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._execution_semaphore = threading.Semaphore(max_concurrent)
        self._active_iterations: Dict[str, threading.Thread] = {}
        self._history: List[Dict[str, Any]] = []
        self._load_history()

    def _load_history(self):
        """Load execution history from disk."""
        if self.history_file.exists():
            try:
                with open(self.history_file, "r") as f:
                    data = json.load(f)
                self._history = data.get("history", [])
            except (json.JSONDecodeError, KeyError):
                self._history = []

    def _save_history(self):
        """Persist execution history to disk."""
        try:
            with open(self.history_file, "w") as f:
                json.dump({
                    "history": self._history[-500:],  # keep last 500
                    "saved_at": datetime.now(timezone.utc).isoformat(),
                }, f, indent=2)
        except Exception:
            pass

    def _is_due(self, loop, now: float) -> bool:
        """Check if a loop is due for execution."""
        if not loop.last_run:
            return True
        try:
            last = datetime.fromisoformat(loop.last_run.replace("Z", "+00:00"))
            elapsed = (now - last.timestamp())
            return elapsed >= loop.interval
        except (ValueError, TypeError):
            return True

    def _execute_and_record(self, loop):
        """Execute one iteration and record the result."""
        with self._execution_semaphore:
            try:
                result_dict = self.engine.run_iteration(loop.id, executor=self.executor)
                self._history.append({
                    "loop_id": loop.id,
                    "loop_name": loop.name,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    **result_dict,
                })
                self._save_history()
            except Exception as e:
                self._history.append({
                    "loop_id": loop.id,
                    "loop_name": loop.name,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "success": False,
                    "error": str(e),
                })
                self._save_history()
            finally:
                self._active_iterations.pop(loop.id, None)

    def _tick(self):
        """One daemon tick — check for due loops and fire them."""
        now = time.time()
        for loop in self.engine.list_loops(status=LoopStatus.RUNNING):
            if loop.id in self._active_iterations:
                continue  # already executing
            if self._is_due(loop, now):
                t = threading.Thread(
                    target=self._execute_and_record,
                    args=(loop,),
                    daemon=True,
                    name=f"loop-{loop.id[:8]}",
                )
                self._active_iterations[loop.id] = t
                t.start()

    def run(self):
        """Main daemon loop — runs until stop() is called."""
        while not self._shutdown_event.is_set():
            self._tick()
            self._shutdown_event.wait(self.tick_interval)

    def start(self):
        """Start daemon in background thread."""
        if self._thread and self._thread.is_alive():
            return False
        self._shutdown_event.clear()
        self._thread = threading.Thread(
            target=self.run,
            daemon=True,
            name="loop-daemon",
        )
        self._thread.start()
        return True

    def stop(self):
        """Graceful shutdown."""
        self._shutdown_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        # Wait for active iterations to finish
        for t in list(self._active_iterations.values()):
            t.join(timeout=10)

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def get_status(self) -> Dict[str, Any]:
        """Get daemon status for UI/CLI."""
        return {
            "running": self.is_running,
            "tick_interval": self.tick_interval,
            "max_concurrent": self.max_concurrent,
            "active_iterations": len(self._active_iterations),
            "history_count": len(self._history),
        }

    def get_history(self, loop_id: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Get execution history, optionally filtered by loop."""
        results = self._history
        if loop_id:
            results = [r for r in results if r.get("loop_id") == loop_id]
        return results[-limit:]

    def get_active_loops(self) -> List[Dict[str, Any]]:
        """Get currently executing loops."""
        return [
            {
                "loop_id": lid,
                "name": self.engine.loops.get(lid).name if lid in self.engine.loops else "Unknown",
            }
            for lid in self._active_iterations
        ]


# Singleton daemon instance (for CLI/UI access)
_daemon_instance: Optional[LoopDaemon] = None


def get_daemon(engine: Optional[LoopMaster] = None, executor: Optional[LoopExecutor] = None) -> LoopDaemon:
    """Get or create the singleton daemon instance."""
    global _daemon_instance
    if _daemon_instance is None:
        if engine is None:
            engine = LoopMaster()
        _daemon_instance = LoopDaemon(engine, executor)
    return _daemon_instance
