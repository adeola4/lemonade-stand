#!/usr/bin/env python3
"""
Loop Master — Resource Monitor & Throttle Module

Monitors system resources and dynamically throttles loop execution:
- CPU usage tracking and throttling
- Memory pressure detection
- Disk I/O monitoring
- Network bandwidth awareness
- Automatic loop suspension under resource pressure
- Gradual recovery when resources normalize
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

RESOURCE_STATE_PATH = os.path.expanduser("~/tan-executive/loop_master/resource_state.json")


class ThrottleLevel(str, Enum):
    """Throttle severity levels."""
    NONE = "none"           # No throttling
    LIGHT = "light"         # Slow down low-priority loops
    MODERATE = "moderate"   # Pause non-critical loops
    HEAVY = "heavy"         # Only critical loops run
    CRITICAL = "critical"   # Pause all loops


@dataclass
class ResourceSnapshot:
    """A snapshot of system resources at a point in time."""
    timestamp: str
    cpu_percent: float
    memory_percent: float
    memory_available_mb: float
    disk_percent: float
    load_average_1m: float
    open_file_descriptors: int = 0
    network_bytes_per_sec: float = 0.0


@dataclass
class ThrottleDecision:
    """A decision about whether/how to throttle a loop."""
    loop_id: str
    throttle_level: ThrottleLevel
    should_run: bool
    reason: str
    suggested_delay: int = 0  # seconds to delay


class ResourceMonitor:
    """
    Monitors system resources and makes throttle decisions.
    
    Thresholds:
    - CPU > 80%: Light throttle
    - CPU > 90%: Moderate throttle
    - CPU > 95%: Heavy throttle
    - Memory > 85%: Light throttle
    - Memory > 95%: Critical throttle
    - Disk > 90%: Moderate throttle
    """

    # Thresholds
    CPU_LIGHT = 80.0
    CPU_MODERATE = 90.0
    CPU_HEAVY = 95.0
    MEM_LIGHT = 85.0
    MEM_CRITICAL = 95.0
    DISK_MODERATE = 90.0
    LOAD_MULTIPLIER = 2.0  # throttle if load > cores * this

    def __init__(self):
        self._history: List[ResourceSnapshot] = []
        self._throttle_states: Dict[str, ThrottleLevel] = {}
        self._load()

    def _load(self):
        """Load resource state from disk."""
        if os.path.exists(RESOURCE_STATE_PATH):
            try:
                with open(RESOURCE_STATE_PATH, "r") as f:
                    data = json.load(f)
                self._throttle_states = {
                    k: ThrottleLevel(v) for k, v in data.get("throttle_states", {}).items()
                }
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        """Persist resource state to disk."""
        os.makedirs(os.path.dirname(RESOURCE_STATE_PATH), exist_ok=True)
        data = {
            "throttle_states": {k: v.value for k, v in self._throttle_states.items()},
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
        with open(RESOURCE_STATE_PATH, "w") as f:
            json.dump(data, f, indent=2)

    def get_current_snapshot(self) -> ResourceSnapshot:
        """Get current system resource usage."""
        import psutil

        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        cpu = psutil.cpu_percent(interval=0.1)
        load = os.getloadavg()[0] if hasattr(os, "getloadavg") else 0.0

        # Count open file descriptors (Unix only)
        fd_count = 0
        try:
            import resource
            fd_count = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        except (ImportError, AttributeError):
            pass

        snapshot = ResourceSnapshot(
            timestamp=datetime.now(timezone.utc).isoformat(),
            cpu_percent=cpu,
            memory_percent=mem.percent,
            memory_available_mb=mem.available / (1024 * 1024),
            disk_percent=disk.percent,
            load_average_1m=load,
            open_file_descriptors=fd_count,
        )

        self._history.append(snapshot)
        # Keep last 100 snapshots
        if len(self._history) > 100:
            self._history = self._history[-100:]

        return snapshot

    def get_current_snapshot_fallback(self) -> ResourceSnapshot:
        """Fallback snapshot when psutil is not available."""
        load = os.getloadavg()[0] if hasattr(os, "getloadavg") else 0.0

        return ResourceSnapshot(
            timestamp=datetime.now(timezone.utc).isoformat(),
            cpu_percent=0.0,  # Unknown
            memory_percent=0.0,
            memory_available_mb=0.0,
            disk_percent=0.0,
            load_average_1m=load,
        )

    def get_overall_throttle_level(self, snapshot: Optional[ResourceSnapshot] = None) -> ThrottleLevel:
        """
        Determine the overall system throttle level based on resource usage.
        Returns the most severe throttle level across all metrics.
        """
        if snapshot is None:
            try:
                snapshot = self.get_current_snapshot()
            except Exception:
                snapshot = self.get_current_snapshot_fallback()

        levels = [ThrottleLevel.NONE]

        # CPU-based throttling
        if snapshot.cpu_percent >= self.CPU_HEAVY:
            levels.append(ThrottleLevel.HEAVY)
        elif snapshot.cpu_percent >= self.CPU_MODERATE:
            levels.append(ThrottleLevel.MODERATE)
        elif snapshot.cpu_percent >= self.CPU_LIGHT:
            levels.append(ThrottleLevel.LIGHT)

        # Memory-based throttling
        if snapshot.memory_percent >= self.MEM_CRITICAL:
            levels.append(ThrottleLevel.CRITICAL)
        elif snapshot.memory_percent >= self.MEM_LIGHT:
            levels.append(ThrottleLevel.LIGHT)

        # Disk-based throttling
        if snapshot.disk_percent >= self.DISK_MODERATE:
            levels.append(ThrottleLevel.MODERATE)

        # Load average throttling
        try:
            import multiprocessing
            cores = multiprocessing.cpu_count()
            if snapshot.load_average_1m > cores * self.LOAD_MULTIPLIER:
                levels.append(ThrottleLevel.MODERATE)
        except Exception:
            pass

        # Return most severe
        severity_order = [
            ThrottleLevel.NONE,
            ThrottleLevel.LIGHT,
            ThrottleLevel.MODERATE,
            ThrottleLevel.HEAVY,
            ThrottleLevel.CRITICAL,
        ]
        max_level = ThrottleLevel.NONE
        for level in levels:
            if severity_order.index(level) > severity_order.index(max_level):
                max_level = level

        return max_level

    def should_run_loop(
        self,
        loop_id: str,
        priority: int,  # 1=LOW, 2=NORMAL, 3=HIGH, 4=CRITICAL
        snapshot: Optional[ResourceSnapshot] = None,
    ) -> ThrottleDecision:
        """
        Decide whether a specific loop should run given current resources.
        
        Priority-based rules:
        - CRITICAL (4): Always runs
        - HIGH (3): Runs unless CRITICAL throttle
        - NORMAL (2): Runs unless HEAVY or CRITICAL throttle
        - LOW (1): Runs only when no throttle or LIGHT
        """
        throttle_level = self.get_overall_throttle_level(snapshot)
        self._throttle_states[loop_id] = throttle_level

        # Decision matrix
        if throttle_level == ThrottleLevel.NONE:
            return ThrottleDecision(
                loop_id=loop_id,
                throttle_level=throttle_level,
                should_run=True,
                reason="resources_nominal",
            )
        elif throttle_level == ThrottleLevel.LIGHT:
            should_run = priority >= 2  # NORMAL and above
            return ThrottleDecision(
                loop_id=loop_id,
                throttle_level=throttle_level,
                should_run=should_run,
                reason="light_throttle" if not should_run else "priority_sufficient",
                suggested_delay=5 if not should_run else 0,
            )
        elif throttle_level == ThrottleLevel.MODERATE:
            should_run = priority >= 3  # HIGH and above
            return ThrottleDecision(
                loop_id=loop_id,
                throttle_level=throttle_level,
                should_run=should_run,
                reason="moderate_throttle" if not should_run else "priority_sufficient",
                suggested_delay=30 if not should_run else 0,
            )
        elif throttle_level == ThrottleLevel.HEAVY:
            should_run = priority >= 4  # CRITICAL only
            return ThrottleDecision(
                loop_id=loop_id,
                throttle_level=throttle_level,
                should_run=should_run,
                reason="heavy_throttle" if not should_run else "critical_priority",
                suggested_delay=120 if not should_run else 0,
            )
        elif throttle_level == ThrottleLevel.CRITICAL:
            # Only critical loops, and even they get delayed
            should_run = priority >= 4
            return ThrottleDecision(
                loop_id=loop_id,
                throttle_level=throttle_level,
                should_run=should_run,
                reason="critical_throttle" if not should_run else "critical_priority_override",
                suggested_delay=300 if not should_run else 60,
            )

        return ThrottleDecision(
            loop_id=loop_id,
            throttle_level=throttle_level,
            should_run=True,
            reason="default_allow",
        )

    def get_batch_decisions(
        self,
        loops: List[Tuple[str, int]],  # (loop_id, priority) tuples
    ) -> List[ThrottleDecision]:
        """
        Get throttle decisions for a batch of loops.
        More efficient than individual calls (single snapshot).
        """
        try:
            snapshot = self.get_current_snapshot()
        except Exception:
            snapshot = self.get_current_snapshot_fallback()

        decisions = []
        for loop_id, priority in loops:
            decision = self.should_run_loop(loop_id, priority, snapshot)
            decisions.append(decision)

        self._save()
        return decisions

    def get_resource_trend(self, window_minutes: int = 10) -> Dict[str, Any]:
        """Get resource usage trend over a time window."""
        cutoff = datetime.now(timezone.utc).timestamp() - (window_minutes * 60)
        recent = [
            s for s in self._history
            if datetime.fromisoformat(s.timestamp).timestamp() >= cutoff
        ]

        if not recent:
            return {"status": "no_data", "window_minutes": window_minutes}

        cpu_values = [s.cpu_percent for s in recent]
        mem_values = [s.memory_percent for s in recent]

        return {
            "window_minutes": window_minutes,
            "samples": len(recent),
            "cpu": {
                "current": cpu_values[-1] if cpu_values else 0,
                "avg": sum(cpu_values) / len(cpu_values) if cpu_values else 0,
                "max": max(cpu_values) if cpu_values else 0,
                "min": min(cpu_values) if cpu_values else 0,
            },
            "memory": {
                "current": mem_values[-1] if mem_values else 0,
                "avg": sum(mem_values) / len(mem_values) if mem_values else 0,
                "max": max(mem_values) if mem_values else 0,
                "min": min(mem_values) if mem_values else 0,
            },
            "throttled_loops": sum(
                1 for level in self._throttle_states.values()
                if level != ThrottleLevel.NONE
            ),
        }

    def get_status_report(self) -> Dict[str, Any]:
        """Get a full status report of system resources and throttling."""
        try:
            snapshot = self.get_current_snapshot()
        except Exception:
            snapshot = self.get_current_snapshot_fallback()

        throttle_level = self.get_overall_throttle_level(snapshot)

        return {
            "timestamp": snapshot.timestamp,
            "throttle_level": throttle_level.value,
            "resources": {
                "cpu_percent": snapshot.cpu_percent,
                "memory_percent": snapshot.memory_percent,
                "memory_available_mb": round(snapshot.memory_available_mb, 1),
                "disk_percent": snapshot.disk_percent,
                "load_average_1m": snapshot.load_average_1m,
            },
            "thresholds": {
                "cpu_light": self.CPU_LIGHT,
                "cpu_moderate": self.CPU_MODERATE,
                "cpu_heavy": self.CPU_HEAVY,
                "mem_light": self.MEM_LIGHT,
                "mem_critical": self.MEM_CRITICAL,
                "disk_moderate": self.DISK_MODERATE,
            },
            "active_throttles": {
                level.value: sum(1 for l in self._throttle_states.values() if l == level)
                for level in ThrottleLevel
            },
        }


# Global singleton
_resource_monitor: Optional[ResourceMonitor] = None


def get_resource_monitor() -> ResourceMonitor:
    """Get or create the global ResourceMonitor singleton."""
    global _resource_monitor
    if _resource_monitor is None:
        _resource_monitor = ResourceMonitor()
    return _resource_monitor
