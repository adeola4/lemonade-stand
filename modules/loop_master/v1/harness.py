"""
Loop Master V1 — Harness Layer

Per-loop scoping, budget guardrails, and isolated context.
Inspired by DeepCode's execution security policy and token meter.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class AccessPreset(StrEnum):
    """User-facing access choices."""
    ASK = "ask"
    READ_ONLY = "read_only"
    FULL_ACCESS = "full_access"


class FilesystemScope(StrEnum):
    """Filesystem boundary for execution."""
    WORKSPACE = "workspace"
    UNRESTRICTED = "unrestricted"


@dataclass
class HarnessConfig:
    """Configuration for a loop execution harness."""
    # Access control
    access_preset: AccessPreset = AccessPreset.READ_ONLY
    filesystem_scope: FilesystemScope = FilesystemScope.WORKSPACE

    # Budget limits
    max_tokens_per_run: int = 100000
    max_turns_per_run: int = 50
    max_wall_time_seconds: int = 3600
    monthly_budget_cents: Optional[float] = None
    est_run_cost_cents: float = 5.0

    # Context management
    auto_compact: bool = True
    compact_threshold: float = 0.9
    compact_keep_chars: int = 60000

    # Network scope
    allowed_domains: Set[str] = field(default_factory=set)
    blocked_domains: Set[str] = field(default_factory=lambda: {"localhost", "127.0.0.1"})

    # Tool scope
    allowed_tools: Set[str] = field(default_factory=set)  # empty = all
    blocked_tools: Set[str] = field(default_factory=set)

    # Approval
    requires_approval: bool = False
    approval_timeout_seconds: int = 300

    # Workspace
    workspace_path: str = os.path.expanduser("~/tan-executive")

    # Compaction settings
    compaction_strategy: str = "tail_retaining"  # or "summarization"
    prune_threshold_chars: int = 8192
    prune_head_chars: int = 4096
    prune_tail_chars: int = 1024


class Harness:
    """
    Isolated execution harness for a single loop.
    
    Manages:
    - Token budget tracking
    - Turn counting
    - Context window monitoring
    - Compaction triggers
    - Tool result pruning
    """

    def __init__(self, config: HarnessConfig, loop_id: str):
        self.config = config
        self.loop_id = loop_id
        self._tokens_used: int = 0
        self._turns_used: int = 0
        self._context_chars: int = 0
        self._tool_results: List[Dict[str, Any]] = []
        self._compaction_count: int = 0
        self._is_active: bool = False
        self._start_time: Optional[float] = None

    @property
    def tokens_remaining(self) -> int:
        return max(0, self.config.max_tokens_per_run - self._tokens_used)

    @property
    def turns_remaining(self) -> int:
        return max(0, self.config.max_turns_per_run - self._turns_used)

    @property
    def context_usage_fraction(self) -> float:
        """Fraction of context window used."""
        if self.config.max_tokens_per_run == 0:
            return 0.0
        return self._context_chars / (self.config.max_tokens_per_run * 4)

    @property
    def needs_compaction(self) -> bool:
        if not self.config.auto_compact:
            return False
        return self.context_usage_fraction >= self.config.compact_threshold

    @property
    def is_within_budget(self) -> bool:
        return self._tokens_used < self.config.max_tokens_per_run

    @property
    def is_within_turn_limit(self) -> bool:
        return self._turns_used < self.config.max_turns_per_run

    def can_execute(self) -> tuple[bool, str]:
        """Check if loop can continue executing."""
        if not self.is_within_budget:
            return False, f"Token budget exhausted: {self._tokens_used}/{self.config.max_tokens_per_run}"
        if not self.is_within_turn_limit:
            return False, f"Turn limit reached: {self._turns_used}/{self.config.max_turns_per_run}"
        return True, "OK"

    def record_turn(self, tokens_used: int = 0, context_chars_added: int = 0) -> None:
        """Record a turn execution."""
        self._turns_used += 1
        self._tokens_used += tokens_used
        self._context_chars += context_chars_added

    def record_tool_result(self, tool_name: str, result: str) -> str:
        """Record and potentially prune a tool result."""
        pruned_result = result
        
        if len(result) > self.config.prune_threshold_chars:
            # Middle-pruning: keep head and tail
            head = result[:self.config.prune_head_chars]
            tail = result[-self.config.prune_tail_chars:] if self.config.prune_tail_chars > 0 else ""
            marker = f"\n\n[... tool result middle pruned ({len(result)} chars -> {len(head) + len(tail) + 30} chars) ...]\n\n"
            pruned_result = head + marker + tail
        
        self._tool_results.append({
            "tool_name": tool_name,
            "original_length": len(result),
            "pruned_length": len(pruned_result),
            "was_pruned": len(result) != len(pruned_result)
        })
        
        return pruned_result

    def check_tool_allowed(self, tool_name: str) -> bool:
        """Check if a tool is allowed in this harness."""
        if tool_name in self.config.blocked_tools:
            return False
        if self.config.allowed_tools and tool_name not in self.config.allowed_tools:
            return False
        return True

    def check_network_allowed(self, domain: str) -> bool:
        """Check if a network domain is allowed."""
        if domain in self.config.blocked_domains:
            return False
        if self.config.allowed_domains and domain not in self.config.allowed_domains:
            return False
        return True

    def get_status(self) -> Dict[str, Any]:
        """Get current harness status."""
        can_execute, reason = self.can_execute()
        return {
            "loop_id": self.loop_id,
            "tokens_used": self._tokens_used,
            "tokens_remaining": self.tokens_remaining,
            "tokens_max": self.config.max_tokens_per_run,
            "turns_used": self._turns_used,
            "turns_remaining": self.turns_remaining,
            "turns_max": self.config.max_turns_per_run,
            "context_usage_fraction": round(self.context_usage_fraction, 3),
            "compaction_count": self._compaction_count,
            "needs_compaction": self.needs_compaction,
            "can_execute": can_execute,
            "reason": reason,
            "tool_results_count": len(self._tool_results),
            "tool_results_pruned": sum(1 for r in self._tool_results if r["was_pruned"]),
        }

    def get_compaction_checkpoint(self) -> Dict[str, Any]:
        """Generate a compaction checkpoint for context management."""
        return {
            "loop_id": self.loop_id,
            "compaction_number": self._compaction_count + 1,
            "tokens_used": self._tokens_used,
            "turns_used": self._turns_used,
            "tool_results_summary": self._tool_results[-10:],  # Last 10
            "workspace": self.config.workspace_path,
            "access_preset": self.config.access_preset.value,
        }


def get_harness_config(loop: "LoopV1") -> HarnessConfig:
    """Create harness config from a LoopV1 definition."""
    preset_map = {
        "ask": AccessPreset.ASK,
        "read_only": AccessPreset.READ_ONLY,
        "full_access": AccessPreset.FULL_ACCESS,
    }
    return HarnessConfig(
        access_preset=preset_map.get(loop.metadata.get("access_preset", "read_only"), AccessPreset.READ_ONLY),
        max_tokens_per_run=loop.max_tokens_per_run,
        max_turns_per_run=loop.max_turns_per_run,
        max_wall_time_seconds=loop.max_wall_time_seconds,
        monthly_budget_cents=loop.monthly_budget_cents,
        est_run_cost_cents=loop.est_run_cost_cents,
        requires_approval=loop.requires_approval,
        workspace_path=os.path.expanduser("~/tan-executive"),
    )
