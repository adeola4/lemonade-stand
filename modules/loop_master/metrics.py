#!/usr/bin/env python3
"""
Loop Master — Metrics & Analytics Module

Comprehensive metrics collection and analytics for loop performance:
- Execution counts, durations, success rates
- Throughput tracking (runs per hour/day)
- Error pattern detection
- Performance trend analysis
- Aggregated dashboards data
- Export for external analytics
"""

from __future__ import annotations

import json
import os
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

METRICS_PATH = os.path.expanduser("~/tan-executive/loop_master/metrics_store.jsonl")
METRICS_SUMMARY_PATH = os.path.expanduser("~/tan-executive/loop_master/metrics_summary.json")


@dataclass
class LoopExecutionRecord:
    """A single execution record for a loop."""
    loop_id: str
    loop_name: str
    timestamp: str
    duration_seconds: float
    success: bool
    error_message: Optional[str] = None
    entry_point: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "loop_id": self.loop_id,
            "loop_name": self.loop_name,
            "timestamp": self.timestamp,
            "duration_seconds": self.duration_seconds,
            "success": self.success,
            "error_message": self.error_message,
            "entry_point": self.entry_point,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LoopExecutionRecord":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class MetricsEngine:
    """
    Collects, stores, and analyzes loop execution metrics.
    
    Metrics are stored in two ways:
    - Append-only JSONL for raw execution records (for replay/audit)
    - Summary JSON for aggregated statistics (for dashboard/real-time)
    """

    # Retention policy
    RAW_RETENTION_DAYS = 30
    MAX_RAW_RECORDS = 100000

    def __init__(self):
        self._ensure_dirs()

    def _ensure_dirs(self):
        """Ensure metric storage directories exist."""
        os.makedirs(os.path.dirname(METRICS_PATH), exist_ok=True)

    def record_execution(self, record: LoopExecutionRecord):
        """Record a single loop execution."""
        with open(METRICS_PATH, "a") as f:
            f.write(json.dumps(record.to_dict()) + "\n")
        self._update_summary(record)

    def _update_summary(self, record: LoopExecutionRecord):
        """Update the rolling summary metrics."""
        summary = self._load_summary()

        loop_summary = summary["loops"].setdefault(record.loop_id, {
            "loop_name": record.loop_name,
            "entry_point": record.entry_point,
            "total_runs": 0,
            "successful_runs": 0,
            "failed_runs": 0,
            "total_duration": 0.0,
            "durations": [],
            "first_run": record.timestamp,
            "last_run": record.timestamp,
            "errors": [],
        })

        loop_summary["total_runs"] += 1
        loop_summary["total_duration"] += record.duration_seconds
        loop_summary["last_run"] = record.timestamp
        loop_summary["entry_point"] = record.entry_point

        # Keep last 100 duration samples
        loop_summary["durations"].append(record.duration_seconds)
        if len(loop_summary["durations"]) > 100:
            loop_summary["durations"] = loop_summary["durations"][-100:]

        if record.success:
            loop_summary["successful_runs"] += 1
        else:
            loop_summary["failed_runs"] += 1
            if record.error_message:
                loop_summary["errors"].append({
                    "timestamp": record.timestamp,
                    "message": record.error_message[:200],
                })
                # Keep last 10 errors
                if len(loop_summary["errors"]) > 10:
                    loop_summary["errors"] = loop_summary["errors"][-10:]

        summary["last_updated"] = datetime.now(timezone.utc).isoformat()
        self._save_summary(summary)

    def _load_summary(self) -> Dict[str, Any]:
        """Load summary from disk."""
        if os.path.exists(METRICS_SUMMARY_PATH):
            try:
                with open(METRICS_SUMMARY_PATH, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, KeyError):
                pass
        return {"loops": {}, "last_updated": None}

    def _save_summary(self, summary: Dict[str, Any]):
        """Save summary to disk."""
        with open(METRICS_SUMMARY_PATH, "w") as f:
            json.dump(summary, f, indent=2)

    def get_loop_metrics(self, loop_id: str) -> Dict[str, Any]:
        """Get detailed metrics for a specific loop."""
        summary = self._load_summary()
        loop_summary = summary["loops"].get(loop_id)

        if not loop_summary:
            return {"loop_id": loop_id, "status": "no_data"}

        durations = loop_summary.get("durations", [])
        total_runs = loop_summary["total_runs"]
        successful_runs = loop_summary["successful_runs"]

        return {
            "loop_id": loop_id,
            "loop_name": loop_summary["loop_name"],
            "entry_point": loop_summary.get("entry_point", ""),
            "total_runs": total_runs,
            "successful_runs": successful_runs,
            "failed_runs": loop_summary["failed_runs"],
            "success_rate": f"{successful_runs / total_runs:.1%}" if total_runs > 0 else "N/A",
            "total_duration": f"{loop_summary['total_duration']:.1f}s",
            "avg_duration": f"{statistics.mean(durations):.2f}s" if durations else "N/A",
            "median_duration": f"{statistics.median(durations):.2f}s" if durations else "N/A",
            "min_duration": f"{min(durations):.2f}s" if durations else "N/A",
            "max_duration": f"{max(durations):.2f}s" if durations else "N/A",
            "std_dev_duration": f"{statistics.stdev(durations):.2f}s" if len(durations) > 1 else "N/A",
            "first_run": loop_summary["first_run"],
            "last_run": loop_summary["last_run"],
            "recent_errors": loop_summary.get("errors", []),
        }

    def get_throughput_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """Calculate throughput metrics over a time window."""
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

        loop_counts: Dict[str, int] = defaultdict(int)
        total_runs = 0
        total_successes = 0

        # Scan raw records
        if os.path.exists(METRICS_PATH):
            with open(METRICS_PATH, "r") as f:
                for line in f:
                    try:
                        record = json.loads(line.strip())
                        if record["timestamp"] >= cutoff:
                            loop_counts[record["loop_id"]] += 1
                            total_runs += 1
                            if record["success"]:
                                total_successes += 1
                    except (json.JSONDecodeError, KeyError):
                        continue

        runs_per_hour = total_runs / hours if hours > 0 else 0

        return {
            "window_hours": hours,
            "total_runs": total_runs,
            "total_successes": total_successes,
            "total_failures": total_runs - total_successes,
            "overall_success_rate": f"{total_successes / total_runs:.1%}" if total_runs > 0 else "N/A",
            "runs_per_hour": f"{runs_per_hour:.1f}",
            "runs_per_minute": f"{runs_per_hour / 60:.2f}",
            "by_loop": dict(sorted(loop_counts.items(), key=lambda x: x[1], reverse=True)),
        }

    def get_error_analysis(self, loop_id: Optional[str] = None) -> Dict[str, Any]:
        """Analyze error patterns across loops."""
        error_counts: Dict[str, int] = defaultdict(int)
        error_messages: Dict[str, List[str]] = defaultdict(list)

        # Analyze raw records
        if os.path.exists(METRICS_PATH):
            with open(METRICS_PATH, "r") as f:
                for line in f:
                    try:
                        record = json.loads(line.strip())
                        if not record.get("success", True):
                            lid = record["loop_id"]
                            if loop_id is None or lid == loop_id:
                                error_counts[lid] += 1
                                msg = record.get("error_message", "Unknown")
                                error_messages[lid].append(msg[:100])
                    except (json.JSONDecodeError, KeyError):
                        continue

        # Find most common errors
        all_errors = []
        for lid, count in error_counts.items():
            all_errors.append({
                "loop_id": lid,
                "error_count": count,
                "recent_messages": error_messages[lid][-5:],
            })

        all_errors.sort(key=lambda x: x["error_count"], reverse=True)

        return {
            "total_errors": sum(error_counts.values()),
            "affected_loops": len(error_counts),
            "error_ranking": all_errors[:20],
        }

    def get_performance_trends(self, loop_id: str, data_points: int = 50) -> Dict[str, Any]:
        """Get performance trends for a loop."""
        durations = []
        timestamps = []

        # Read recent records for this loop
        if os.path.exists(METRICS_PATH):
            with open(METRICS_PATH, "r") as f:
                for line in f:
                    try:
                        record = json.loads(line.strip())
                        if record["loop_id"] == loop_id:
                            durations.append(record["duration_seconds"])
                            timestamps.append(record["timestamp"])
                    except (json.JSONDecodeError, KeyError):
                        continue

        if not durations:
            return {"loop_id": loop_id, "status": "no_data"}

        # Take last N points
        durations = durations[-data_points:]
        timestamps = timestamps[-data_points:]

        # Detect trend (simple linear regression)
        if len(durations) >= 3:
            n = len(durations)
            x_vals = list(range(n))
            x_mean = statistics.mean(x_vals)
            y_mean = statistics.mean(durations)

            numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_vals, durations))
            denominator = sum((x - x_mean) ** 2 for x in x_vals)

            if denominator > 0:
                slope = numerator / denominator
                trend = "improving" if slope < -0.01 else "degrading" if slope > 0.01 else "stable"
            else:
                trend = "stable"
                slope = 0
        else:
            trend = "insufficient_data"
            slope = 0

        return {
            "loop_id": loop_id,
            "data_points": len(durations),
            "trend": trend,
            "slope": slope,
            "current_avg": statistics.mean(durations),
            "recent_avg": statistics.mean(durations[-10:]) if len(durations) >= 10 else statistics.mean(durations),
            "peak": max(durations),
            "min": min(durations),
            "timestamps": timestamps[-10:],
            "durations": durations[-10:],
        }

    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Get aggregated metrics suitable for dashboard display."""
        summary = self._load_summary()

        total_runs = sum(ls["total_runs"] for ls in summary["loops"].values())
        total_successes = sum(ls["successful_runs"] for ls in summary["loops"].values())
        total_failures = sum(ls["failed_runs"] for ls in summary["loops"].values())

        loop_summaries = []
        for loop_id, ls in summary["loops"].items():
            loop_summaries.append({
                "loop_id": loop_id,
                "loop_name": ls["loop_name"],
                "total_runs": ls["total_runs"],
                "success_rate": f"{ls['successful_runs'] / ls['total_runs']:.1%}" if ls["total_runs"] > 0 else "N/A",
                "avg_duration": f"{statistics.mean(ls['durations']):.2f}s" if ls["durations"] else "N/A",
                "last_run": ls["last_run"],
            })

        loop_summaries.sort(key=lambda x: x["total_runs"], reverse=True)

        return {
            "total_loops_tracked": len(summary["loops"]),
            "total_runs": total_runs,
            "total_successes": total_successes,
            "total_failures": total_failures,
            "overall_success_rate": f"{total_successes / total_runs:.1%}" if total_runs > 0 else "N/A",
            "loops": loop_summaries[:50],
            "last_updated": summary.get("last_updated"),
        }

    def export_metrics(self, format: str = "json", hours: Optional[int] = None) -> Dict[str, Any]:
        """Export metrics in various formats for external analysis."""
        if format == "json":
            if hours:
                cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
            else:
                cutoff = "1970-01-01T00:00:00+00:00"

            records = []
            if os.path.exists(METRICS_PATH):
                with open(METRICS_PATH, "r") as f:
                    for line in f:
                        try:
                            record = json.loads(line.strip())
                            if record["timestamp"] >= cutoff:
                                records.append(record)
                        except (json.JSONDecodeError, KeyError):
                            continue

            return {"format": "json", "record_count": len(records), "records": records}

        elif format == "csv":
            import io
            import csv

            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["timestamp", "loop_id", "loop_name", "duration_seconds", "success", "error_message"])

            if os.path.exists(METRICS_PATH):
                with open(METRICS_PATH, "r") as f:
                    for line in f:
                        try:
                            record = json.loads(line.strip())
                            writer.writerow([
                                record["timestamp"],
                                record["loop_id"],
                                record["loop_name"],
                                record["duration_seconds"],
                                record["success"],
                                record.get("error_message", ""),
                            ])
                        except (json.JSONDecodeError, KeyError):
                            continue

            return {"format": "csv", "data": output.getvalue()}

        return {"format": format, "status": "unsupported_format"}


# Global singleton
_metrics_engine: Optional[MetricsEngine] = None


def get_metrics_engine() -> MetricsEngine:
    """Get or create the global MetricsEngine singleton."""
    global _metrics_engine
    if _metrics_engine is None:
        _metrics_engine = MetricsEngine()
    return _metrics_engine
