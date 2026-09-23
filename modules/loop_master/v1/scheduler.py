"""
Loop Master V1 — Scheduler + Concurrency Control

Cron-based scheduling with concurrency caps, retry/backoff.
Inspired by agent-orchestrator's scheduler and DeepCode's automation scheduler.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# Cron field bounds: (min, max)
_FIELD_BOUNDS = [
    (0, 59),   # minute
    (0, 23),   # hour
    (1, 31),   # day of month
    (1, 12),   # month
    (0, 7),    # day of week (0 and 7 both Sunday)
]


class CronError(ValueError):
    """Raised when a cron expression cannot be parsed."""


def _parse_field(spec: str, lo: int, hi: int) -> frozenset[int]:
    """Expand one cron field into the explicit set of values it matches."""
    values: set[int] = set()
    for part in spec.split(","):
        step = 1
        body = part
        if "/" in part:
            body, _, step_s = part.partition("/")
            if not step_s.isdigit() or int(step_s) < 1:
                raise CronError(f"invalid step in {part!r}")
            step = int(step_s)
        if body == "*":
            start, end = lo, hi
        elif "-" in body:
            a, _, b = body.partition("-")
            if not (a.isdigit() and b.isdigit()):
                raise CronError(f"invalid range in {part!r}")
            start, end = int(a), int(b)
        elif body.isdigit():
            start = end = int(body)
        else:
            raise CronError(f"invalid field component {part!r}")
        if start < lo or end > hi or start > end:
            raise CronError(f"value out of bounds in {part!r} (allowed {lo}-{hi})")
        values.update(range(start, end + 1, step))
    return frozenset(values)


@dataclass(frozen=True, slots=True)
class CronExpression:
    """A parsed cron expression."""
    minutes: frozenset[int]
    hours: frozenset[int]
    days_of_month: frozenset[int]
    months: frozenset[int]
    days_of_week: frozenset[int]
    dom_restricted: bool
    dow_restricted: bool

    @classmethod
    def parse(cls, expression: str) -> "CronExpression":
        """Parse a 5-field cron expression."""
        fields = expression.split()
        if len(fields) != 5:
            raise CronError(f"expected 5 fields (min hour dom month dow), got {len(fields)}: {expression!r}")
        
        sets = [
            _parse_field(f, lo, hi)
            for f, (lo, hi) in zip(fields, _FIELD_BOUNDS, strict=True)
        ]
        
        # Normalize day-of-week: 7 -> 0 (Sunday)
        dow = frozenset(0 if d == 7 else d for d in sets[4])
        
        return cls(
            minutes=sets[0],
            hours=sets[1],
            days_of_month=sets[2],
            months=sets[3],
            days_of_week=dow,
            dom_restricted=fields[2] != "*",
            dow_restricted=fields[4] != "*",
        )

    def matches(self, dt: datetime) -> bool:
        """Check if a datetime matches this cron expression."""
        minute_ok = dt.minute in self.minutes
        hour_ok = dt.hour in self.hours
        month_ok = dt.month in self.months
        
        # POSIX dom/dow rule:
        # When both restricted, match if EITHER matches
        # When one is *, both must match
        if self.dom_restricted and self.dow_restricted:
            date_ok = dt.day in self.days_of_month or dt.weekday() in self.days_of_week
        elif self.dom_restricted:
            date_ok = dt.day in self.days_of_month
        elif self.dow_restricted:
            date_ok = dt.weekday() in self.days_of_week
        else:
            date_ok = True
        
        return minute_ok and hour_ok and month_ok and date_ok

    def next_after(self, dt: datetime) -> datetime:
        """Return the next datetime that matches after dt."""
        # Simple increment: try next 4 years in 1-minute steps
        candidate = dt + timedelta(minutes=1)
        candidate = candidate.replace(second=0, microsecond=0)
        
        max_attempts = 365 * 24 * 60 * 4  # 4 years
        for _ in range(max_attempts):
            if self.matches(candidate):
                return candidate
            candidate += timedelta(minutes=1)
        
        return candidate  # Should not reach here for valid cron


@dataclass
class ScheduleEntry:
    """A loop's schedule configuration."""
    loop_id: str
    cron: str
    timezone: str = "UTC"
    enabled: bool = True
    last_run_at: Optional[float] = None  # epoch seconds
    
    def to_dict(self) -> dict:
        return {
            "loop_id": self.loop_id,
            "cron": self.cron,
            "timezone": self.timezone,
            "enabled": self.enabled,
            "last_run_at": self.last_run_at,
        }


class V1Scheduler:
    """
    Cron scheduler with concurrency control.
    
    Fires due loops at most once per minute (minute-level dedup).
    Enforces global and per-loop concurrency caps.
    """

    def __init__(self, max_concurrent_runs: int = 10, retry_base_delay_seconds: float = 2.0):
        self._schedules: Dict[str, ScheduleEntry] = {}
        self._max_concurrent = max_concurrent_runs
        self._retry_base_delay = retry_base_delay_seconds
        self._active_runs: Dict[str, float] = {}  # loop_id -> start_time

    def add_schedule(self, entry: ScheduleEntry) -> None:
        """Register a loop's schedule."""
        self._schedules[entry.loop_id] = entry

    def remove_schedule(self, loop_id: str) -> bool:
        """Remove a loop's schedule."""
        if loop_id in self._schedules:
            del self._schedules[loop_id]
            return True
        return False

    def tick(self, now: Optional[datetime] = None) -> List[str]:
        """
        Fire every due routine at `now`.
        Returns list of loop_ids that should be scheduled.
        """
        if now is None:
            now = datetime.now(timezone.utc)
        
        fired: List[str] = []
        
        for loop_id, entry in self._schedules.items():
            if not entry.enabled:
                continue
            
            # Parse cron
            try:
                expr = CronExpression.parse(entry.cron)
            except CronError:
                continue
            
            # Check if it's time to fire
            if not expr.matches(now):
                continue
            
            # Minute-level dedup
            minute_ts = now.replace(second=0, microsecond=0).timestamp()
            if entry.last_run_at is not None and entry.last_run_at >= minute_ts:
                continue
            
            # Check concurrency
            if len(self._active_runs) >= self._max_concurrent:
                continue
            
            if loop_id in self._active_runs:
                continue
            
            # Fire!
            entry.last_run_at = minute_ts
            self._active_runs[loop_id] = now.timestamp()
            fired.append(loop_id)
        
        return fired

    def complete_run(self, loop_id: str, success: bool, attempts: int = 0) -> Optional[datetime]:
        """
        Mark a loop run as complete.
        Returns next scheduled run time if applicable.
        """
        if loop_id in self._active_runs:
            del self._active_runs[loop_id]
        
        entry = self._schedules.get(loop_id)
        if entry is None:
            return None
        
        if not success:
            # Exponential backoff for retry
            delay = self._retry_base_delay * (2 ** attempts)
            return datetime.now(timezone.utc) + timedelta(seconds=delay)
        
        # Calculate next fire time
        try:
            expr = CronExpression.parse(entry.cron)
            return expr.next_after(datetime.now(timezone.utc))
        except CronError:
            return None

    def next_fire(self, loop_id: str, after: Optional[datetime] = None) -> Optional[datetime]:
        """Return the next time a routine will fire after `after`."""
        entry = self._schedules.get(loop_id)
        if entry is None or not entry.enabled:
            return None
        
        if after is None:
            after = datetime.now(timezone.utc)
        
        try:
            expr = CronExpression.parse(entry.cron)
            return expr.next_after(after)
        except CronError:
            return None

    def get_active_count(self) -> int:
        """Get number of currently active runs."""
        return len(self._active_runs)

    def get_active_runs(self) -> List[str]:
        """Get list of currently active loop IDs."""
        return list(self._active_runs.keys())

    def get_all_schedules(self) -> List[Dict[str, Any]]:
        """Get all schedule entries."""
        return [
            {
                **entry.to_dict(),
                "next_fire": self.next_fire(entry.loop_id),
                "is_active": entry.loop_id in self._active_runs,
            }
            for entry in self._schedules.values()
        ]

    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        return {
            "total_scheduled": len(self._schedules),
            "active_runs": len(self._active_runs),
            "max_concurrent": self._max_concurrent,
            "retry_base_delay": self._retry_base_delay,
            "active_loop_ids": list(self._active_runs.keys()),
        }


def get_scheduler(max_concurrent: int = 10) -> V1Scheduler:
    """Get the global scheduler instance."""
    if not hasattr(get_scheduler, "_instance"):
        get_scheduler._instance = V1Scheduler(max_concurrent_runs=max_concurrent)
    return get_scheduler._instance


# Convenience functions for cron validation
def validate_cron(expression: str) -> Tuple[bool, Optional[str]]:
    """Validate a cron expression. Returns (is_valid, error_message)."""
    try:
        CronExpression.parse(expression)
        return True, None
    except CronError as e:
        return False, str(e)


def cron_to_human(expression: str) -> str:
    """Convert a cron expression to human-readable format."""
    # Simple conversion for common patterns
    parts = expression.split()
    if len(parts) != 5:
        return expression
    
    minute, hour, dom, month, dow = parts
    
    # Every N minutes
    if minute.startswith("*/") and dom == "*" and month == "*" and dow == "*":
        return f"Every {minute[2:]} minutes"
    
    # Every N hours
    if minute == "0" and hour.startswith("*/") and dom == "*" and month == "*" and dow == "*":
        return f"Every {hour[2:]} hours"
    
    # Daily at specific time
    if minute.isdigit() and hour.isdigit() and dom == "*" and month == "*" and dow == "*":
        return f"Daily at {hour}:{minute.zfill(2)} UTC"
    
    # Weekday at specific time
    if minute.isdigit() and hour.isdigit() and dom == "*" and month == "*" and dow == "1-5":
        return f"Weekdays at {hour}:{minute.zfill(2)} UTC"
    
    return f"Cron: {expression}"
