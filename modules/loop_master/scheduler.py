#!/usr/bin/env python3
"""
Loop Master — Orchestration Scheduler Module

Advanced scheduling for loop execution:
- Cron-style scheduling (specific times/days)
- Priority-based resource allocation
- Load balancing across time windows
- Execution window constraints (business hours, off-peak)
- Queue management for concurrent loop limits
- Preemption rules for high-priority loops
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

SCHEDULER_CONFIG_PATH = os.path.expanduser("~/tan-executive/loop_master/scheduler_config.json")


@dataclass
class ScheduleRule:
    """A scheduling rule for a loop."""
    loop_id: str
    # Cron-style fields
    minute: Optional[str] = None       # 0-59, */5, etc.
    hour: Optional[str] = None         # 0-23, */2, etc.
    day_of_month: Optional[str] = None # 1-31
    month: Optional[str] = None        # 1-12
    day_of_week: Optional[str] = None  # 0-6 (0=Monday)
    # Window constraints
    earliest_time: Optional[str] = None  # HH:MM (24h format)
    latest_time: Optional[str] = None    # HH:MM (24h format)
    timezone: str = "UTC"
    # Resource allocation
    max_concurrent: int = 1
    preempt_lower_priority: bool = False
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TimeWindow:
    """A time window constraint."""
    name: str
    earliest: str  # HH:MM
    latest: str    # HH:MM
    timezone: str = "UTC"
    days_of_week: Optional[Set[int]] = None  # None = all days


# Pre-defined time windows
BUSINESS_HOURS_ET = TimeWindow(
    name="business_hours_et",
    earliest="09:00",
    latest="17:00",
    timezone="America/New_York",
    days_of_week={0, 1, 2, 3, 4},  # Mon-Fri
)

OFF_PEAK_HOURS = TimeWindow(
    name="off_peak",
    earliest="22:00",
    latest="06:00",
    timezone="UTC",
)

WEEKEND = TimeWindow(
    name="weekend",
    earliest="00:00",
    latest="23:59",
    timezone="UTC",
    days_of_week={5, 6},  # Sat-Sun
)


class CronParser:
    """
    Simple cron expression parser.
    Supports: exact values, ranges (*/5), lists (1,3,5), steps (*/n).
    """

    @staticmethod
    def matches(field_expr: Optional[str], value: int) -> bool:
        """Check if a value matches a cron field expression."""
        if field_expr is None:
            return True  # Wildcard
        if field_expr == "*":
            return True

        # Handle list: "1,3,5"
        if "," in field_expr:
            return any(CronParser.matches(part.strip(), value) for part in field_expr.split(","))

        # Handle step: "*/5" or "1-10/2"
        if "/" in field_expr:
            range_part, step = field_expr.split("/", 1)
            step = int(step)
            if range_part == "*":
                return value % step == 0
            elif "-" in range_part:
                start, end = range_part.split("-", 1)
                return int(start) <= value <= int(end) and (value - int(start)) % step == 0
            else:
                base = int(range_part)
                return value >= base and (value - base) % step == 0

        # Handle range: "1-5"
        if "-" in field_expr:
            start, end = field_expr.split("-", 1)
            return int(start) <= value <= int(end)

        # Exact value
        return int(field_expr) == value

    @staticmethod
    def matches_datetime(cron_fields: Dict[str, Optional[str]], dt: datetime) -> bool:
        """Check if a datetime matches all cron fields."""
        return (
            CronParser.matches(cron_fields.get("minute"), dt.minute) and
            CronParser.matches(cron_fields.get("hour"), dt.hour) and
            CronParser.matches(cron_fields.get("day_of_month"), dt.day) and
            CronParser.matches(cron_fields.get("month"), dt.month) and
            CronParser.matches(cron_fields.get("day_of_week"), dt.weekday())
        )


class SchedulingEngine:
    """
    Advanced scheduling engine for loop execution.
    Manages cron-style schedules, time windows, and resource allocation.
    """

    # Default concurrent loop limit
    DEFAULT_MAX_CONCURRENT = 10

    def __init__(self):
        self._rules: Dict[str, ScheduleRule] = {}
        self._windows: Dict[str, TimeWindow] = {
            "business_hours_et": BUSINESS_HOURS_ET,
            "off_peak": OFF_PEAK_HOURS,
            "weekend": WEEKEND,
        }
        self._load()

    def _load(self):
        """Load scheduler configuration from disk."""
        if os.path.exists(SCHEDULER_CONFIG_PATH):
            try:
                with open(SCHEDULER_CONFIG_PATH, "r") as f:
                    data = json.load(f)

                for rule_data in data.get("rules", []):
                    rule = ScheduleRule(
                        loop_id=rule_data["loop_id"],
                        minute=rule_data.get("minute"),
                        hour=rule_data.get("hour"),
                        day_of_month=rule_data.get("day_of_month"),
                        month=rule_data.get("month"),
                        day_of_week=rule_data.get("day_of_week"),
                        earliest_time=rule_data.get("earliest_time"),
                        latest_time=rule_data.get("latest_time"),
                        timezone=rule_data.get("timezone", "UTC"),
                        max_concurrent=rule_data.get("max_concurrent", 1),
                        preempt_lower_priority=rule_data.get("preempt_lower_priority", False),
                        enabled=rule_data.get("enabled", True),
                        metadata=rule_data.get("metadata", {}),
                    )
                    self._rules[rule.loop_id] = rule

                for win_name, win_data in data.get("windows", {}).items():
                    self._windows[win_name] = TimeWindow(
                        name=win_name,
                        earliest=win_data["earliest"],
                        latest=win_data["latest"],
                        timezone=win_data.get("timezone", "UTC"),
                        days_of_week=set(win_data["days_of_week"]) if "days_of_week" in win_data else None,
                    )
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        """Persist scheduler configuration to disk."""
        os.makedirs(os.path.dirname(SCHEDULER_CONFIG_PATH), exist_ok=True)
        data = {
            "rules": [
                {
                    "loop_id": rule.loop_id,
                    "minute": rule.minute,
                    "hour": rule.hour,
                    "day_of_month": rule.day_of_month,
                    "month": rule.month,
                    "day_of_week": rule.day_of_week,
                    "earliest_time": rule.earliest_time,
                    "latest_time": rule.latest_time,
                    "timezone": rule.timezone,
                    "max_concurrent": rule.max_concurrent,
                    "preempt_lower_priority": rule.preempt_lower_priority,
                    "enabled": rule.enabled,
                    "metadata": rule.metadata,
                }
                for rule in self._rules.values()
            ],
            "windows": {
                name: {
                    "earliest": w.earliest,
                    "latest": w.latest,
                    "timezone": w.timezone,
                    "days_of_week": list(w.days_of_week) if w.days_of_week else None,
                }
                for name, w in self._windows.items()
            },
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(SCHEDULER_CONFIG_PATH, "w") as f:
            json.dump(data, f, indent=2)

    def set_schedule(self, rule: ScheduleRule):
        """Set a schedule rule for a loop."""
        self._rules[rule.loop_id] = rule
        self._save()

    def remove_schedule(self, loop_id: str) -> bool:
        """Remove a schedule rule."""
        if loop_id in self._rules:
            del self._rules[loop_id]
            self._save()
            return True
        return False

    def get_schedule(self, loop_id: str) -> Optional[ScheduleRule]:
        """Get the schedule rule for a loop."""
        return self._rules.get(loop_id)

    def is_scheduled_now(self, loop_id: str, dt: Optional[datetime] = None) -> Tuple[bool, str]:
        """
        Check if a loop should execute at the given time.
        
        Returns:
            Tuple of (should_execute, reason)
        """
        if dt is None:
            dt = datetime.now(timezone.utc)

        rule = self._rules.get(loop_id)
        if not rule:
            # No schedule rule — always allowed
            return True, "no_schedule"

        if not rule.enabled:
            return False, "schedule_disabled"

        # Check cron fields
        cron_fields = {
            "minute": rule.minute,
            "hour": rule.hour,
            "day_of_month": rule.day_of_month,
            "month": rule.month,
            "day_of_week": rule.day_of_week,
        }
        if not CronParser.matches_datetime(cron_fields, dt):
            return False, "cron_mismatch"

        # Check time window
        if rule.earliest_time and rule.latest_time:
            current_time = dt.strftime("%H:%M")
            if rule.earliest_time <= rule.latest_time:
                # Normal range (e.g., 09:00-17:00)
                if not (rule.earliest_time <= current_time <= rule.latest_time):
                    return False, "outside_time_window"
            else:
                # Inverted range (e.g., 22:00-06:00 — overnight)
                if rule.latest_time < current_time < rule.earliest_time:
                    return False, "outside_time_window"

        return True, "scheduled"

    def get_next_execution(self, loop_id: str, after: Optional[datetime] = None) -> Optional[datetime]:
        """
        Calculate the next execution time for a loop.
        
        Searches forward up to 7 days.
        """
        rule = self._rules.get(loop_id)
        if not rule or not rule.enabled:
            return None

        if after is None:
            after = datetime.now(timezone.utc)

        # Search minute-by-minute for next valid time (up to 7 days)
        check_time = after + timedelta(minutes=1)
        max_search = after + timedelta(days=7)

        while check_time <= max_search:
            should_exec, _ = self.is_scheduled_now(loop_id, check_time)
            if should_exec:
                return check_time
            check_time += timedelta(minutes=1)

        return None

    def get_execution_queue(
        self,
        loop_ids: List[str],
        max_concurrent: int = DEFAULT_MAX_CONCURRENT,
    ) -> List[Dict[str, Any]]:
        """
        Build a prioritized execution queue.
        
        Returns loops ordered by priority, respecting concurrent limits.
        """
        queue = []
        for loop_id in loop_ids:
            rule = self._rules.get(loop_id)
            if not rule:
                queue.append({
                    "loop_id": loop_id,
                    "priority": 2,  # NORMAL default
                    "can_execute": True,
                    "reason": "no_schedule",
                })
                continue

            should_exec, reason = self.is_scheduled_now(loop_id)
            queue.append({
                "loop_id": loop_id,
                "priority": rule.metadata.get("priority", 2),
                "can_execute": should_exec,
                "reason": reason,
                "preempt": rule.preempt_lower_priority,
            })

        # Sort: executable first, then by priority (high to low)
        queue.sort(key=lambda x: (not x["can_execute"], -x.get("priority", 2)))

        # Apply concurrency limit
        executable = [q for q in queue if q["can_execute"]]
        non_executable = [q for q in queue if not q["can_execute"]]

        # Limit executable batch
        if len(executable) > max_concurrent:
            executable = executable[:max_concurrent]

        return executable + non_executable

    def create_cron_rule(
        self,
        loop_id: str,
        cron_expression: str,
        earliest_time: Optional[str] = None,
        latest_time: Optional[str] = None,
    ) -> ScheduleRule:
        """
        Create a schedule rule from a cron expression.
        
        Supports standard 5-field cron: minute hour day-of-month month day-of-week
        """
        parts = cron_expression.split()
        if len(parts) != 5:
            raise ValueError(f"Invalid cron expression: {cron_expression}. Expected 5 fields.")

        rule = ScheduleRule(
            loop_id=loop_id,
            minute=parts[0] if parts[0] != "*" else None,
            hour=parts[1] if parts[1] != "*" else None,
            day_of_month=parts[2] if parts[2] != "*" else None,
            month=parts[3] if parts[3] != "*" else None,
            day_of_week=parts[4] if parts[4] != "*" else None,
            earliest_time=earliest_time,
            latest_time=latest_time,
        )
        self.set_schedule(rule)
        return rule

    def get_scheduler_summary(self) -> Dict[str, Any]:
        """Get summary of all schedule rules."""
        return {
            "total_scheduled_loops": len(self._rules),
            "enabled_rules": sum(1 for r in self._rules.values() if r.enabled),
            "disabled_rules": sum(1 for r in self._rules.values() if not r.enabled),
            "preemptive_rules": sum(1 for r in self._rules.values() if r.preempt_lower_priority),
            "custom_windows": len(self._windows) - 3,  # Subtract built-in windows
            "rules": [
                {
                    "loop_id": r.loop_id,
                    "enabled": r.enabled,
                    "cron": f"{r.minute or '*'} {r.hour or '*'} {r.day_of_month or '*'} {r.month or '*'} {r.day_of_week or '*'}",
                    "time_window": f"{r.earliest_time}-{r.latest_time}" if r.earliest_time else "any",
                    "preempt": r.preempt_lower_priority,
                }
                for r in self._rules.values()
            ],
        }


# Global singleton
_scheduling_engine: Optional[SchedulingEngine] = None


def get_scheduling_engine() -> SchedulingEngine:
    """Get or create the global SchedulingEngine singleton."""
    global _scheduling_engine
    if _scheduling_engine is None:
        _scheduling_engine = SchedulingEngine()
    return _scheduling_engine
