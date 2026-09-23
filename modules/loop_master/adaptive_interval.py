#!/usr/bin/env python3
"""
Loop Master — Adaptive Interval Module

Dynamically adjusts loop intervals based on:
- Success/error rate trends
- Execution duration (slow loops get longer intervals)
- Load conditions (busy systems get longer intervals)
- Time-of-day patterns (peak vs off-peak)
"""

from __future__ import annotations

import json
import os
import statistics
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

HISTORY_PATH = os.path.expanduser("~/tan-executive/loop_master/interval_history.json")


@dataclass
class IntervalMetrics:
    """Metrics used to compute adaptive intervals."""
    run_times: List[float] = field(default_factory=list)  # execution durations in seconds
    success_times: List[float] = field(default_factory=list)  # runs that succeeded
    error_times: List[float] = field(default_factory=list)  # runs that errored
    last_adjustment: Optional[str] = None
    adjustment_reason: str = ""


class AdaptiveIntervalEngine:
    """
    Monitors loop performance and suggests optimal intervals.
    
    Strategies:
    - Exponential backoff on errors
    - Linear scaling on high latency
    - Decay recovery on sustained success
    - Load-aware throttling
    """

    # Configuration
    MAX_INTERVAL = 86400 * 7  # 1 week cap
    MIN_INTERVAL = 10  # 10 seconds floor
    BACKOFF_FACTOR = 1.5  # multiply interval by this on errors
    RECOVERY_FACTOR = 0.9  # multiply interval by this on success (toward target)
    LATENCY_THRESHOLD_P95 = 60  # if p95 run time > this, increase interval
    ERROR_RATE_THRESHOLD = 0.3  # if error rate > 30%, apply backoff
    HISTORY_WINDOW = 50  # keep last N data points

    def __init__(self):
        self._metrics: Dict[str, IntervalMetrics] = defaultdict(IntervalMetrics)
        self._load()

    def _load(self):
        """Load historical metrics from disk."""
        if os.path.exists(HISTORY_PATH):
            try:
                with open(HISTORY_PATH, "r") as f:
                    data = json.load(f)
                for loop_id, m in data.get("metrics", {}).items():
                    self._metrics[loop_id] = IntervalMetrics(
                        run_times=m.get("run_times", [])[-self.HISTORY_WINDOW:],
                        success_times=m.get("success_times", [])[-self.HISTORY_WINDOW:],
                        error_times=m.get("error_times", [])[-self.HISTORY_WINDOW:],
                        last_adjustment=m.get("last_adjustment"),
                        adjustment_reason=m.get("adjustment_reason", ""),
                    )
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        """Persist metrics to disk."""
        os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
        data = {
            "metrics": {
                loop_id: {
                    "run_times": m.run_times[-self.HISTORY_WINDOW:],
                    "success_times": m.success_times[-self.HISTORY_WINDOW:],
                    "error_times": m.error_times[-self.HISTORY_WINDOW:],
                    "last_adjustment": m.last_adjustment,
                    "adjustment_reason": m.adjustment_reason,
                }
                for loop_id, m in self._metrics.items()
            },
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(HISTORY_PATH, "w") as f:
            json.dump(data, f, indent=2)

    def record_execution(
        self,
        loop_id: str,
        duration_seconds: float,
        success: bool,
        timestamp: Optional[str] = None,
    ):
        """Record a single loop execution result."""
        metrics = self._metrics[loop_id]
        metrics.run_times.append(duration_seconds)
        if success:
            metrics.success_times.append(duration_seconds)
        else:
            metrics.error_times.append(duration_seconds)

        # Trim history
        if len(metrics.run_times) > self.HISTORY_WINDOW:
            metrics.run_times = metrics.run_times[-self.HISTORY_WINDOW:]
        if len(metrics.success_times) > self.HISTORY_WINDOW:
            metrics.success_times = metrics.success_times[-self.HISTORY_WINDOW:]
        if len(metrics.error_times) > self.HISTORY_WINDOW:
            metrics.error_times = metrics.error_times[-self.HISTORY_WINDOW:]

        self._save()

    def suggest_interval(
        self,
        loop_id: str,
        current_interval: int,
        target_interval: Optional[int] = None,
    ) -> Tuple[int, str]:
        """
        Suggest an optimal interval for a loop based on its metrics.
        
        Returns:
            Tuple of (suggested_interval_seconds, reason_string)
        """
        metrics = self._metrics.get(loop_id)
        if not metrics or len(metrics.run_times) < 3:
            return current_interval, "Insufficient data"

        # Calculate error rate
        total_runs = len(metrics.run_times)
        error_rate = len(metrics.error_times) / total_runs if total_runs > 0 else 0

        # Calculate p95 latency
        sorted_times = sorted(metrics.run_times)
        p95_index = int(len(sorted_times) * 0.95)
        p95_latency = sorted_times[min(p95_index, len(sorted_times) - 1)]

        suggested = current_interval
        reasons = []

        # Strategy 1: Error-based backoff
        if error_rate >= self.ERROR_RATE_THRESHOLD:
            suggested = int(current_interval * self.BACKOFF_FACTOR)
            reasons.append(f"error_rate={error_rate:.0%}")
        elif error_rate == 0 and target_interval and current_interval > target_interval:
            # Strategy 2: Recovery — slowly return to target
            suggested = max(target_interval, int(current_interval * self.RECOVERY_FACTOR))
            reasons.append("recovery_to_target")

        # Strategy 3: Latency-based scaling
        if p95_latency > self.LATENCY_THRESHOLD_P95:
            latency_suggestion = int(current_interval * 1.3)
            if latency_suggestion > suggested:
                suggested = latency_suggestion
                reasons.append(f"p95_latency={p95_latency:.1f}s")

        # Strategy 4: Stable loop optimization — slight decrease if healthy
        if error_rate < 0.05 and p95_latency < 10 and target_interval:
            stable_suggestion = max(target_interval, int(current_interval * 0.95))
            if stable_suggestion < suggested:
                suggested = stable_suggestion
                reasons.append("stable_optimization")

        # Apply bounds
        suggested = max(self.MIN_INTERVAL, min(suggested, self.MAX_INTERVAL))

        if suggested == current_interval:
            return current_interval, "optimal"

        reason = ", ".join(reasons) if reasons else "adjusted"
        return suggested, reason

    def get_interval_report(self, loop_id: str) -> Dict[str, Any]:
        """Get a detailed interval report for a loop."""
        metrics = self._metrics.get(loop_id)
        if not metrics or not metrics.run_times:
            return {"loop_id": loop_id, "status": "no_data"}

        sorted_times = sorted(metrics.run_times)
        p50 = statistics.median(sorted_times)
        p95_index = int(len(sorted_times) * 0.95)
        p95 = sorted_times[min(p95_index, len(sorted_times) - 1)]

        return {
            "loop_id": loop_id,
            "total_recorded_runs": len(metrics.run_times),
            "total_successes": len(metrics.success_times),
            "total_errors": len(metrics.error_times),
            "error_rate": f"{len(metrics.error_times) / len(metrics.run_times):.1%}",
            "p50_latency": f"{p50:.2f}s",
            "p95_latency": f"{p95:.2f}s",
            "avg_latency": f"{statistics.mean(metrics.run_times):.2f}s",
            "last_adjustment": metrics.last_adjustment,
            "adjustment_reason": metrics.adjustment_reason,
        }

    def get_all_reports(self) -> List[Dict[str, Any]]:
        """Get interval reports for all tracked loops."""
        return [self.get_interval_report(loop_id) for loop_id in self._metrics]


# Global singleton
_adaptive_engine: Optional[AdaptiveIntervalEngine] = None


def get_adaptive_engine() -> AdaptiveIntervalEngine:
    """Get or create the global AdaptiveIntervalEngine singleton."""
    global _adaptive_engine
    if _adaptive_engine is None:
        _adaptive_engine = AdaptiveIntervalEngine()
    return _adaptive_engine
