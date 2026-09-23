"""
Loop Master Execution Bridge — translates loop definitions into Hermes agent calls.

This is the missing layer: loops have entry_point + params, and this module
actually executes them against the Hermes LLM endpoint, captures results,
and returns structured data for state/metrics/evidence updates.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pathlib import Path

import urllib.request
import urllib.error


@dataclass
class ExecutionResult:
    """Result of a single loop iteration."""
    loop_id: str
    success: bool
    response: str
    tokens_used: int = 0
    duration_seconds: float = 0.0
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    iteration: int = 0

    def to_dict(self) -> dict:
        return {
            "loop_id": self.loop_id,
            "success": self.success,
            "response": self.response,
            "tokens_used": self.tokens_used,
            "duration_seconds": round(self.duration_seconds, 2),
            "error": self.error,
            "timestamp": self.timestamp,
            "iteration": self.iteration,
        }


class LoopExecutor:
    """
    Executes loop iterations by dispatching to the Hermes LLM endpoint.
    
    Supports both V0 loops (simple entry_point + params) and V1 loops
    (goal-driven with completion criteria).
    """

    DEFAULT_ENDPOINT = "http://127.0.0.1:8645/v1/chat/completions"
    DEFAULT_MODEL = "meituan/longcat-2.0:free"
    DEFAULT_MAX_TOKENS = 4000
    DEFAULT_TIMEOUT = 120  # seconds

    def __init__(
        self,
        endpoint: str = DEFAULT_ENDPOINT,
        model: str = DEFAULT_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        timeout: int = DEFAULT_TIMEOUT,
        log_dir: str = "~/tan-executive/loop_master/execution_logs",
    ):
        self.endpoint = endpoint
        self.model = model
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.log_dir = Path(log_dir).expanduser()
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._results_buffer: List[ExecutionResult] = []

    def build_prompt(self, entry_point: str, params: Optional[Dict[str, Any]] = None,
                     goal: str = "", criteria: str = "") -> str:
        """Build the full prompt for a loop iteration."""
        parts = [
            "You are an autonomous loop in the Lemonade Stand system.",
            "Execute the following task:",
            "",
            entry_point,
        ]
        if goal:
            parts.extend(["", f"Goal: {goal}"])
        if criteria:
            parts.extend(["", f"Completion criteria: {criteria}"])
        if params and isinstance(params, dict) and params:
            parts.extend(["", "Context (JSON):", json.dumps(params, indent=2, default=str)])
        parts.extend([
            "",
            "Respond with a concise result. If the task requires multiple steps, execute them all.",
        ])
        return "\n".join(parts)

    def execute(self, loop_id: str, entry_point: str,
                params: Optional[Dict[str, Any]] = None,
                goal: str = "", criteria: str = "",
                iteration: int = 0) -> ExecutionResult:
        """
        Execute one loop iteration synchronously.
        
        This is the core method — builds prompt, calls Hermes LLM, captures result.
        """
        start_time = time.time()
        prompt = self.build_prompt(entry_point, params, goal, criteria)

        payload = json.dumps({
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.max_tokens,
            "temperature": 0.7,
        }).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        req = urllib.request.Request(self.endpoint, data=payload, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
                data = json.loads(raw)

            content = ""
            tokens = 0
            if "choices" in data and data["choices"]:
                choice = data["choices"][0]
                content = choice.get("message", {}).get("content", "") or choice.get("text", "")
                tokens = data.get("usage", {}).get("completion_tokens", 0)
            elif "content" in data:
                content = data["content"]
                tokens = data.get("tokens_used", 0)

            duration = time.time() - start_time
            result = ExecutionResult(
                loop_id=loop_id,
                success=True,
                response=content,
                tokens_used=tokens,
                duration_seconds=duration,
                iteration=iteration,
            )

        except urllib.error.HTTPError as e:
            duration = time.time() - start_time
            body = ""
            try:
                body = e.read().decode("utf-8")[:500]
            except Exception:
                pass
            result = ExecutionResult(
                loop_id=loop_id,
                success=False,
                response="",
                duration_seconds=duration,
                error=f"HTTP {e.code}: {body or e.reason}",
                iteration=iteration,
            )

        except Exception as e:
            duration = time.time() - start_time
            result = ExecutionResult(
                loop_id=loop_id,
                success=False,
                response="",
                duration_seconds=duration,
                error=str(e),
                iteration=iteration,
            )

        self._log_result(result)
        return result

    def _log_result(self, result: ExecutionResult):
        """Persist result to execution log."""
        self._results_buffer.append(result)

        # Write to daily log file
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        log_file = self.log_dir / f"executions_{date_str}.jsonl"

        try:
            with open(log_file, "a") as f:
                f.write(json.dumps(result.to_dict()) + "\n")
        except Exception:
            pass  # Don't let logging failures crash execution

    def get_recent_results(self, loop_id: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Get recent execution results, optionally filtered by loop."""
        results = self._results_buffer
        if loop_id:
            results = [r for r in results if r.loop_id == loop_id]
        return [r.to_dict() for r in results[-limit:]]

    def get_log_files(self) -> List[str]:
        """List all execution log files."""
        return sorted([str(f) for f in self.log_dir.glob("executions_*.jsonl")])

    def read_log(self, date_str: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Read executions from a log file."""
        if date_str is None:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        log_file = self.log_dir / f"executions_{date_str}.jsonl"
        if not log_file.exists():
            return []
        results = []
        with open(log_file, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        results.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return results[-limit:]

    def health_check(self) -> Dict[str, Any]:
        """Check if the Hermes endpoint is reachable."""
        try:
            payload = json.dumps({
                "model": self.model,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 10,
            }).encode("utf-8")
            req = urllib.request.Request(
                self.endpoint, data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return {"healthy": True, "status": resp.status}
        except Exception as e:
            return {"healthy": False, "error": str(e)}


def get_executor(
    endpoint: str = LoopExecutor.DEFAULT_ENDPOINT,
    model: str = LoopExecutor.DEFAULT_MODEL,
) -> LoopExecutor:
    """Factory for the singleton executor."""
    return LoopExecutor(endpoint=endpoint, model=model)
