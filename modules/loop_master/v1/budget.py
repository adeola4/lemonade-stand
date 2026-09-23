"""
Loop Master V1 — Budget Guardrails

Per-loop and global budget tracking.
Inspired by agent-orchestrator's BudgetGuard.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class BudgetGuard:
    """
    Tracks cumulative spend per-loop and globally.
    
    Spend is cumulative for the lifetime of the guard.
    Consult can_spend() BEFORE admitting a run.
    Call record() AFTER it finishes.
    """

    STORAGE_PATH = os.path.expanduser("~/tan-executive/loop_master/v1/budget.json")

    def __init__(self, global_cap_cents: Optional[float] = None):
        self._global_cap = global_cap_cents
        self._global_spent = 0.0
        self._by_loop: Dict[str, float] = {}
        self._history: List[Dict[str, Any]] = []
        self._load()

    def _load(self):
        if os.path.exists(self.STORAGE_PATH):
            try:
                with open(self.STORAGE_PATH, "r") as f:
                    data = json.load(f)
                self._global_spent = data.get("global_spent", 0.0)
                self._by_loop = data.get("by_loop", {})
                self._history = data.get("history", [])
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        os.makedirs(os.path.dirname(self.STORAGE_PATH), exist_ok=True)
        with open(self.STORAGE_PATH, "w") as f:
            json.dump({
                "global_cap": self._global_cap,
                "global_spent": self._global_spent,
                "by_loop": self._by_loop,
                "history": self._history[-100:],  # Keep last 100 records
                "saved_at": datetime.now(timezone.utc).isoformat()
            }, f, indent=2)

    def can_spend(
        self,
        loop_id: str,
        estimate_cents: float,
        loop_cap_cents: Optional[float] = None,
    ) -> bool:
        """
        Return True if spending estimate_cents keeps both caps satisfied.
        Call BEFORE admitting a run.
        """
        # Check global cap
        if self._global_cap is not None:
            if self._global_spent + estimate_cents > self._global_cap:
                return False
        
        # Check per-loop cap
        if loop_cap_cents is not None:
            loop_spent = self._by_loop.get(loop_id, 0.0)
            if loop_spent + estimate_cents > loop_cap_cents:
                return False
        
        return True

    def record(self, loop_id: str, cost_cents: float, run_id: str = "") -> None:
        """
        Add actual spend to the loop and global ledgers.
        Call AFTER a run finishes.
        """
        # Update ledgers
        self._by_loop[loop_id] = self._by_loop.get(loop_id, 0.0) + cost_cents
        self._global_spent += cost_cents
        
        # Record history
        self._history.append({
            "loop_id": loop_id,
            "run_id": run_id,
            "cost_cents": cost_cents,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        
        self._save()

    def spent_by(self, loop_id: str) -> float:
        """Cumulative spend for one loop."""
        return self._by_loop.get(loop_id, 0.0)

    def remaining_for(self, loop_id: str, loop_cap_cents: Optional[float]) -> Optional[float]:
        """Remaining budget for a loop. Returns None if no cap."""
        if loop_cap_cents is None:
            return None
        return max(0.0, loop_cap_cents - self.spent_by(loop_id))

    @property
    def total_spent(self) -> float:
        """Cumulative spend across all loops."""
        return self._global_spent

    @property
    def global_remaining(self) -> Optional[float]:
        """Remaining global budget. Returns None if no cap."""
        if self._global_cap is None:
            return None
        return max(0.0, self._global_cap - self._global_spent)

    def get_loop_ids(self) -> List[str]:
        """Get all loop IDs that have spent budget."""
        return list(self._by_loop.keys())

    def get_history(self, loop_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get spending history."""
        history = self._history
        if loop_id:
            history = [h for h in history if h["loop_id"] == loop_id]
        return history[-limit:]

    def get_status(self) -> Dict[str, Any]:
        """Get budget status."""
        return {
            "global_cap_cents": self._global_cap,
            "global_spent_cents": self._global_spent,
            "global_remaining_cents": self.global_remaining,
            "loops_tracked": len(self._by_loop),
            "loop_spend": self._by_loop,
        }

    def reset_loop(self, loop_id: str) -> bool:
        """Reset spend for a loop (e.g., new billing period)."""
        if loop_id in self._by_loop:
            del self._by_loop[loop_id]
            self._save()
            return True
        return False

    def reset_all(self) -> None:
        """Reset all spend (e.g., new billing period)."""
        self._global_spent = 0.0
        self._by_loop = {}
        self._save()


def get_budget_guard(global_cap_cents: Optional[float] = None) -> BudgetGuard:
    """Get the global budget guard instance."""
    if not hasattr(get_budget_guard, "_instance"):
        get_budget_guard._instance = BudgetGuard(global_cap_cents=global_cap_cents)
    return get_budget_guard._instance
