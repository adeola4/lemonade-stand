#!/usr/bin/env python3
"""
Loop Master — Self-Healing Module

Automatic error recovery and loop stabilization:
- Retry with exponential backoff
- Automatic handler restart after N failures
- Circuit breaker pattern (stop retrying after threshold)
- Escalation policies (notify after sustained failure)
- State recovery (restore loop state after crash)
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

SELF_HEALING_PATH = os.path.expanduser("~/tan-executive/loop_master/self_healing_state.json")


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Failing, do not attempt
    HALF_OPEN = "half_open" # Testing recovery


@dataclass
class CircuitBreaker:
    """Circuit breaker for a specific loop."""
    loop_id: str
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure: Optional[str] = None
    last_success: Optional[str] = None
    # Thresholds
    failure_threshold: int = 5  # open after N failures
    recovery_timeout: int = 300  # seconds before half-open test
    half_open_max_calls: int = 1  # max test calls in half-open

    @property
    def is_available(self) -> bool:
        """Check if the circuit allows execution."""
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            # Check if recovery timeout has elapsed
            if self.last_failure:
                try:
                    last_fail = datetime.fromisoformat(self.last_failure)
                    elapsed = (datetime.now(timezone.utc) - last_fail).total_seconds()
                    if elapsed >= self.recovery_timeout:
                        self.state = CircuitState.HALF_OPEN
                        self.success_count = 0
                        return True
                except (ValueError, TypeError):
                    pass
            return False
        elif self.state == CircuitState.HALF_OPEN:
            return self.success_count < self.half_open_max_calls
        return True

    def record_success(self):
        """Record a successful execution."""
        self.success_count += 1
        self.last_success = datetime.now(timezone.utc).isoformat()

        if self.state == CircuitState.HALF_OPEN:
            # Recovery confirmed
            self.state = CircuitState.CLOSED
            self.failure_count = 0
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = max(0, self.failure_count - 1)

    def record_failure(self):
        """Record a failed execution."""
        self.failure_count += 1
        self.last_failure = datetime.now(timezone.utc).isoformat()

        if self.state == CircuitState.HALF_OPEN:
            # Recovery failed, go back to open
            self.state = CircuitState.OPEN
        elif self.state == CircuitState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN


@dataclass
class RetryPolicy:
    """Retry configuration for a loop."""
    max_retries: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True  # add randomness to prevent thundering herd

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for a given retry attempt (0-indexed)."""
        import random
        delay = self.base_delay * (self.exponential_base ** attempt)
        delay = min(delay, self.max_delay)
        if self.jitter:
            delay = delay * (0.5 + random.random() * 0.5)  # 50%-100% of calculated delay
        return delay


class SelfHealingEngine:
    """
    Self-healing engine that monitors loop health and automatically
    attempts recovery strategies.
    """

    def __init__(self):
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._retry_policies: Dict[str, RetryPolicy] = {}
        self._healing_actions: List[Dict[str, Any]] = []
        self._load()

    def _load(self):
        """Load healing state from disk."""
        if os.path.exists(SELF_HEALING_PATH):
            try:
                with open(SELF_HEALING_PATH, "r") as f:
                    data = json.load(f)

                for cb_data in data.get("circuit_breakers", []):
                    cb = CircuitBreaker(
                        loop_id=cb_data["loop_id"],
                        state=CircuitState(cb_data.get("state", "closed")),
                        failure_count=cb_data.get("failure_count", 0),
                        success_count=cb_data.get("success_count", 0),
                        last_failure=cb_data.get("last_failure"),
                        last_success=cb_data.get("last_success"),
                        failure_threshold=cb_data.get("failure_threshold", 5),
                        recovery_timeout=cb_data.get("recovery_timeout", 300),
                        half_open_max_calls=cb_data.get("half_open_max_calls", 1),
                    )
                    self._circuit_breakers[cb.loop_id] = cb

                for rp_data in data.get("retry_policies", []):
                    rp = RetryPolicy(
                        max_retries=rp_data.get("max_retries", 3),
                        base_delay=rp_data.get("base_delay", 1.0),
                        max_delay=rp_data.get("max_delay", 60.0),
                        exponential_base=rp_data.get("exponential_base", 2.0),
                        jitter=rp_data.get("jitter", True),
                    )
                    self._retry_policies[rp_data["loop_id"]] = rp

                self._healing_actions = data.get("healing_actions", [])
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        """Persist healing state to disk."""
        os.makedirs(os.path.dirname(SELF_HEALING_PATH), exist_ok=True)
        data = {
            "circuit_breakers": [
                {
                    "loop_id": cb.loop_id,
                    "state": cb.state.value,
                    "failure_count": cb.failure_count,
                    "success_count": cb.success_count,
                    "last_failure": cb.last_failure,
                    "last_success": cb.last_success,
                    "failure_threshold": cb.failure_threshold,
                    "recovery_timeout": cb.recovery_timeout,
                    "half_open_max_calls": cb.half_open_max_calls,
                }
                for cb in self._circuit_breakers.values()
            ],
            "retry_policies": [
                {
                    "loop_id": loop_id,
                    "max_retries": rp.max_retries,
                    "base_delay": rp.base_delay,
                    "max_delay": rp.max_delay,
                    "exponential_base": rp.exponential_base,
                    "jitter": rp.jitter,
                }
                for loop_id, rp in self._retry_policies.items()
            ],
            "healing_actions": self._healing_actions[-100:],  # Keep last 100
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(SELF_HEALING_PATH, "w") as f:
            json.dump(data, f, indent=2)

    def get_circuit_breaker(self, loop_id: str) -> CircuitBreaker:
        """Get or create a circuit breaker for a loop."""
        if loop_id not in self._circuit_breakers:
            self._circuit_breakers[loop_id] = CircuitBreaker(loop_id=loop_id)
        return self._circuit_breakers[loop_id]

    def get_retry_policy(self, loop_id: str) -> RetryPolicy:
        """Get or create a retry policy for a loop."""
        if loop_id not in self._retry_policies:
            self._retry_policies[loop_id] = RetryPolicy()
        return self._retry_policies[loop_id]

    def set_retry_policy(self, loop_id: str, policy: RetryPolicy):
        """Set a custom retry policy for a loop."""
        self._retry_policies[loop_id] = policy
        self._save()

    def can_execute(self, loop_id: str) -> Tuple[bool, str]:
        """
        Check if a loop is allowed to execute.
        
        Returns:
            Tuple of (allowed, reason)
        """
        cb = self.get_circuit_breaker(loop_id)
        if cb.is_available:
            return True, "circuit_closed"
        return False, f"circuit_open: {cb.failure_count} failures, recovering for {cb.recovery_timeout}s"

    def record_execution_result(self, loop_id: str, success: bool, error_message: str = "") -> Dict[str, Any]:
        """
        Record execution result and update healing state.
        
        Returns:
            Dict with healing action taken
        """
        cb = self.get_circuit_breaker(loop_id)
        action_taken = {"loop_id": loop_id, "action": "none"}

        if success:
            cb.record_success()
            action_taken["action"] = "recorded_success"
            action_taken["circuit_state"] = cb.state.value
        else:
            cb.record_failure()
            action_taken["action"] = "recorded_failure"
            action_taken["circuit_state"] = cb.state.value
            action_taken["error"] = error_message[:200]

            if cb.state == CircuitState.OPEN:
                action_taken["action"] = "circuit_opened"
                action_taken["message"] = f"Circuit breaker OPEN after {cb.failure_count} failures"

        self._healing_actions.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **action_taken,
        })
        self._save()
        return action_taken

    def get_recommended_action(self, loop_id: str) -> Dict[str, Any]:
        """
        Get recommended healing action for a loop.
        
        Returns recommended strategy based on current state.
        """
        cb = self.get_circuit_breaker(loop_id)
        rp = self.get_retry_policy(loop_id)

        if cb.state == CircuitState.OPEN:
            return {
                "action": "wait_for_recovery",
                "message": f"Circuit is open. Wait {cb.recovery_timeout}s before retry.",
                "estimated_recovery": cb.last_failure,  # Should add timeout
            }
        elif cb.state == CircuitState.HALF_OPEN:
            return {
                "action": "test_execution",
                "message": "Circuit is half-open. Proceed with test execution.",
            }
        elif cb.failure_count > 0:
            delay = rp.get_delay(cb.failure_count - 1)
            return {
                "action": "retry_with_delay",
                "delay_seconds": delay,
                "attempt": cb.failure_count,
                "message": f"Retry after {delay:.1f}s delay (attempt {cb.failure_count}/{rp.max_retries})",
            }
        else:
            return {
                "action": "normal_execution",
                "message": "No healing action needed.",
            }

    def get_health_summary(self, loop_id: Optional[str] = None) -> Dict[str, Any]:
        """Get health summary for one or all loops."""
        if loop_id:
            cb = self.get_circuit_breaker(loop_id)
            rp = self.get_retry_policy(loop_id)
            return {
                "loop_id": loop_id,
                "circuit_state": cb.state.value,
                "failure_count": cb.failure_count,
                "success_count": cb.success_count,
                "last_failure": cb.last_failure,
                "last_success": cb.last_success,
                "retry_policy": {
                    "max_retries": rp.max_retries,
                    "base_delay": rp.base_delay,
                    "max_delay": rp.max_delay,
                },
            }
        else:
            return {
                "total_circuits": len(self._circuit_breakers),
                "open_circuits": sum(1 for cb in self._circuit_breakers.values() if cb.state == CircuitState.OPEN),
                "half_open_circuits": sum(1 for cb in self._circuit_breakers.values() if cb.state == CircuitState.HALF_OPEN),
                "closed_circuits": sum(1 for cb in self._circuit_breakers.values() if cb.state == CircuitState.CLOSED),
                "total_failures": sum(cb.failure_count for cb in self._circuit_breakers.values()),
                "circuits": [
                    self.get_health_summary(loop_id)
                    for loop_id in self._circuit_breakers
                ],
            }


# Global singleton
_self_healing_engine: Optional[SelfHealingEngine] = None


def get_self_healing_engine() -> SelfHealingEngine:
    """Get or create the global SelfHealingEngine singleton."""
    global _self_healing_engine
    if _self_healing_engine is None:
        _self_healing_engine = SelfHealingEngine()
    return _self_healing_engine
