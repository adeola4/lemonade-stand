#!/usr/bin/env python3
"""
Loop Master CLI — Commands for all 7 loop engineering upgrade modules.

Module 1: Adaptive Interval — `loop-adaptive`
Module 2: Dependency Graph — `loop-deps`
Module 3: Notifications — `loop-notify`
Module 4: Self-Healing — `loop-heal`
Module 5: Metrics — `loop-metrics`
Module 6: Template Library — `loop-templates`
Module 7: Scheduler — `loop-scheduler`
Module 8: Resource Monitor — `loop-resources`
"""

import json
from typing import Any, Dict, List, Optional


def cmd_loop_adaptive(args):
    """Manage adaptive interval engine."""
    from modules.loop_master.adaptive_interval import get_adaptive_engine

    engine = get_adaptive_engine()
    action = args.action or "report"

    if action == "report":
        loop_id = getattr(args, "loop_id", None)
        if loop_id:
            return {"status": "ok", "data": engine.get_interval_report(loop_id)}
        return {"status": "ok", "data": engine.get_all_reports()}

    elif action == "suggest":
        loop_id = args.loop_id
        current = args.current_interval
        target = getattr(args, "target_interval", None)
        suggested, reason = engine.suggest_interval(loop_id, current, target)
        return {
            "status": "ok",
            "loop_id": loop_id,
            "current_interval": current,
            "suggested_interval": suggested,
            "reason": reason,
        }

    elif action == "record":
        engine.record_execution(
            args.loop_id,
            args.duration,
            args.success.lower() == "true",
        )
        return {"status": "ok", "message": "Execution recorded"}

    return {"status": "error", "message": f"Unknown action: {action}"}


def cmd_loop_deps(args):
    """Manage loop dependency graph."""
    from modules.loop_master.dependency_graph import (
        get_dependency_engine,
        DependencyType,
    )

    engine = get_dependency_engine()
    action = args.action or "report"

    if action == "add":
        dep_type = DependencyType(getattr(args, "type", "hard"))
        success, msg = engine.add_dependency(
            args.upstream,
            args.downstream,
            dep_type,
            getattr(args, "description", ""),
        )
        return {"status": "ok" if success else "error", "message": msg}

    elif action == "remove":
        success = engine.remove_dependency(args.upstream, args.downstream)
        return {"status": "ok" if success else "error", "message": "Dependency removed"}

    elif action == "blocked":
        blocked = engine.get_blocked_loops(args.loop_id)
        return {"status": "ok", "blocked_loops": blocked}

    elif action == "order":
        order = engine.get_execution_order()
        return {"status": "ok", "execution_order": order}

    elif action == "batches":
        batches = engine.get_parallel_batches()
        return {
            "status": "ok",
            "batches": [
                {
                    "batch": b.batch_number,
                    "loops": b.loop_ids,
                    "depends_on": b.depends_on_batch,
                }
                for b in batches
            ],
        }

    elif action == "report":
        return {"status": "ok", "data": engine.get_dependency_report()}

    return {"status": "error", "message": f"Unknown action: {action}"}


def cmd_loop_notify(args):
    """Send/manage notifications."""
    from modules.loop_master.notifications import (
        get_notification_engine,
        NotificationConfig,
        NotificationChannel,
        NotificationSeverity,
    )

    engine = get_notification_engine()
    action = args.action or "log"

    if action == "send":
        results = engine.notify_loop_event(
            args.loop_id,
            getattr(args, "loop_name", "Unknown"),
            args.event,
            args.message,
            NotificationSeverity(getattr(args, "severity", "info")),
        )
        return {"status": "ok", "results": results}

    elif action == "log":
        limit = getattr(args, "limit", 50)
        return {"status": "ok", "notifications": engine.get_notification_log(limit)}

    elif action == "configure":
        config = NotificationConfig(
            channel=NotificationChannel(args.channel),
            enabled=True,
            min_severity=NotificationSeverity(getattr(args, "min_severity", "warning")),
            webhook_url=getattr(args, "webhook_url", None),
        )
        engine.configure_channel(config)
        return {"status": "ok", "message": f"Channel {args.channel} configured"}

    return {"status": "error", "message": f"Unknown action: {action}"}


def cmd_loop_heal(args):
    """Manage self-healing."""
    from modules.loop_master.self_healing import get_self_healing_engine

    engine = get_self_healing_engine()
    action = args.action or "status"

    if action == "status":
        loop_id = getattr(args, "loop_id", None)
        return {"status": "ok", "data": engine.get_health_summary(loop_id)}

    elif action == "check":
        can_exec, reason = engine.can_execute(args.loop_id)
        recommendation = engine.get_recommended_action(args.loop_id)
        return {
            "status": "ok",
            "loop_id": args.loop_id,
            "can_execute": can_exec,
            "reason": reason,
            "recommendation": recommendation,
        }

    elif action == "record":
        success = args.success.lower() == "true"
        error_msg = getattr(args, "error", "")
        result = engine.record_execution_result(args.loop_id, success, error_msg)
        return {"status": "ok", "result": result}

    return {"status": "error", "message": f"Unknown action: {action}"}


def cmd_loop_metrics(args):
    """Access loop metrics and analytics."""
    from modules.loop_master.metrics import get_metrics_engine

    engine = get_metrics_engine()
    action = args.action or "dashboard"

    if action == "dashboard":
        return {"status": "ok", "data": engine.get_dashboard_summary()}

    elif action == "loop":
        return {"status": "ok", "data": engine.get_loop_metrics(args.loop_id)}

    elif action == "throughput":
        hours = getattr(args, "hours", 24)
        return {"status": "ok", "data": engine.get_throughput_metrics(hours)}

    elif action == "errors":
        loop_id = getattr(args, "loop_id", None)
        return {"status": "ok", "data": engine.get_error_analysis(loop_id)}

    elif action == "trend":
        return {"status": "ok", "data": engine.get_performance_trends(args.loop_id)}

    elif action == "export":
        fmt = getattr(args, "format", "json")
        hours = getattr(args, "hours", None)
        return {"status": "ok", "data": engine.export_metrics(fmt, hours)}

    return {"status": "error", "message": f"Unknown action: {action}"}


def cmd_loop_templates(args):
    """Manage loop templates."""
    from modules.loop_master.template_library import get_template_library

    engine = get_template_library()
    action = args.action or "list"

    if action == "list":
        category = getattr(args, "category", None)
        tag = getattr(args, "tag", None)
        templates = engine.list_templates(category, tag)
        return {
            "status": "ok",
            "templates": [t.to_dict() for t in templates],
            "count": len(templates),
        }

    elif action == "catalog":
        return {"status": "ok", "data": engine.get_catalog()}

    elif action == "get":
        tmpl = engine.get_template(args.template_id)
        if tmpl:
            return {"status": "ok", "template": tmpl.to_dict()}
        return {"status": "error", "message": "Template not found"}

    elif action == "instantiate":
        config = engine.instantiate_template(
            args.template_id,
            param_overrides=json.loads(args.params) if hasattr(args, "params") else None,
        )
        if config:
            return {"status": "ok", "config": config}
        return {"status": "error", "message": "Template not found"}

    elif action == "create":
        template = engine.create_custom_template(
            name=args.name,
            description=getattr(args, "description", ""),
            category=args.category,
            entry_point=args.entry_point,
            default_interval=getattr(args, "interval", 3600),
            default_priority=getattr(args, "priority", 2),
            tags=getattr(args, "tags", []),
        )
        return {"status": "ok", "template": template.to_dict()}

    elif action == "delete":
        success = engine.delete_custom_template(args.template_id)
        return {"status": "ok" if success else "error", "message": "Template deleted"}

    return {"status": "error", "message": f"Unknown action: {action}"}


def cmd_loop_scheduler(args):
    """Manage loop scheduling."""
    from modules.loop_master.scheduler import get_scheduling_engine, ScheduleRule

    engine = get_scheduling_engine()
    action = args.action or "summary"

    if action == "summary":
        return {"status": "ok", "data": engine.get_scheduler_summary()}

    elif action == "set":
        rule = ScheduleRule(
            loop_id=args.loop_id,
            minute=getattr(args, "minute", None),
            hour=getattr(args, "hour", None),
            day_of_week=getattr(args, "day_of_week", None),
            earliest_time=getattr(args, "earliest", None),
            latest_time=getattr(args, "latest", None),
        )
        engine.set_schedule(rule)
        return {"status": "ok", "message": f"Schedule set for {args.loop_id}"}

    elif action == "cron":
        rule = engine.create_cron_rule(
            args.loop_id,
            args.expression,
            getattr(args, "earliest", None),
            getattr(args, "latest", None),
        )
        return {"status": "ok", "rule": rule.loop_id, "cron": args.expression}

    elif action == "check":
        should_run, reason = engine.is_scheduled_now(args.loop_id)
        return {"status": "ok", "should_run": should_run, "reason": reason}

    elif action == "next":
        next_exec = engine.get_next_execution(args.loop_id)
        return {"status": "ok", "next_execution": next_exec.isoformat() if next_exec else None}

    elif action == "remove":
        success = engine.remove_schedule(args.loop_id)
        return {"status": "ok" if success else "error", "message": "Schedule removed"}

    return {"status": "error", "message": f"Unknown action: {action}"}


def cmd_loop_resources(args):
    """Monitor system resources and throttling."""
    from modules.loop_master.resource_monitor import get_resource_monitor

    engine = get_resource_monitor()
    action = args.action or "status"

    if action == "status":
        return {"status": "ok", "data": engine.get_status_report()}

    elif action == "check":
        priority = getattr(args, "priority", 2)
        decision = engine.should_run_loop(args.loop_id, priority)
        return {
            "status": "ok",
            "loop_id": args.loop_id,
            "should_run": decision.should_run,
            "throttle_level": decision.throttle_level.value,
            "reason": decision.reason,
            "suggested_delay": decision.suggested_delay,
        }

    elif action == "trend":
        minutes = getattr(args, "minutes", 10)
        return {"status": "ok", "data": engine.get_resource_trend(minutes)}

    return {"status": "error", "message": f"Unknown action: {action}"}
