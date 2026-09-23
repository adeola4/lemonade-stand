"""
QLA Loop Master — Autonomous 24/7 Business Loop Engine
Manages hundreds of concurrent loops with full lifecycle control.

Modules:
- engine: Core loop management
- adaptive_interval: Dynamic interval adjustment based on performance
- dependency_graph: Loop dependency management and execution ordering
- notifications: Multi-channel alerting system
- self_healing: Automatic error recovery with circuit breakers
- metrics: Performance tracking and analytics
- template_library: Pre-built loop configuration templates
- scheduler: Advanced cron-based scheduling with time windows
- resource_monitor: System resource monitoring and throttling
"""

from .engine import LoopMaster, Loop, LoopStatus, LoopPriority

# Upgrade modules
from .adaptive_interval import AdaptiveIntervalEngine, get_adaptive_engine
from .dependency_graph import DependencyGraphEngine, get_dependency_engine, DependencyType
from .notifications import NotificationEngine, get_notification_engine, NotificationChannel, NotificationSeverity
from .self_healing import SelfHealingEngine, get_self_healing_engine, CircuitState
from .metrics import MetricsEngine, get_metrics_engine, LoopExecutionRecord
from .template_library import TemplateLibrary, get_template_library, LoopTemplate
from .scheduler import SchedulingEngine, get_scheduling_engine, ScheduleRule, CronParser, TimeWindow
from .resource_monitor import ResourceMonitor, get_resource_monitor, ThrottleLevel
from .executor import LoopExecutor, ExecutionResult, get_executor
from .daemon import LoopDaemon, get_daemon

__all__ = [
    # Core
    "LoopMaster", "Loop", "LoopStatus", "LoopPriority",
    # Adaptive Interval
    "AdaptiveIntervalEngine", "get_adaptive_engine",
    # Dependency Graph
    "DependencyGraphEngine", "get_dependency_engine", "DependencyType",
    # Notifications
    "NotificationEngine", "get_notification_engine", "NotificationChannel", "NotificationSeverity",
    # Self Healing
    "SelfHealingEngine", "get_self_healing_engine", "CircuitState",
    # Metrics
    "MetricsEngine", "get_metrics_engine", "LoopExecutionRecord",
    # Template Library
    "TemplateLibrary", "get_template_library", "LoopTemplate",
    # Scheduler
    "SchedulingEngine", "get_scheduling_engine", "ScheduleRule", "CronParser", "TimeWindow",
    # Resource Monitor
    "ResourceMonitor", "get_resource_monitor", "ThrottleLevel",
    # Executor
    "LoopExecutor", "ExecutionResult", "get_executor",
    # Daemon
    "LoopDaemon", "get_daemon",
]
