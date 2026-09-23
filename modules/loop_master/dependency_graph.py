#!/usr/bin/env python3
"""
Loop Master — Dependency Graph Module

Manages loop dependencies and execution ordering:
- Define loops that depend on other loops' completion
- Topological sort for execution ordering
- Parallel execution of independent loops
- Dependency health propagation (upstream failures block downstream)
"""

from __future__ import annotations

import json
import os
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

DEPENDENCY_PATH = os.path.expanduser("~/tan-executive/loop_master/dependency_graph.json")


class DependencyType(str, Enum):
    """Types of loop dependencies."""
    HARD = "hard"        # Downstream cannot run without upstream success
    SOFT = "soft"        # Downstream runs but may have degraded data
    TRIGGER = "trigger"  # Upstream completion triggers downstream execution


@dataclass
class LoopDependency:
    """A dependency relationship between two loops."""
    upstream_loop_id: str
    downstream_loop_id: str
    dependency_type: DependencyType = DependencyType.HARD
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    # Optional: data to pass from upstream to downstream
    data_mapping: Dict[str, str] = field(default_factory=dict)


@dataclass
class ExecutionBatch:
    """A batch of loops that can execute in parallel."""
    batch_number: int
    loop_ids: List[str]
    depends_on_batch: Optional[int] = None


class DependencyGraphEngine:
    """
    Manages loop dependencies, resolves execution order,
    and identifies parallelizable batches.
    """

    def __init__(self):
        self._dependencies: List[LoopDependency] = []
        self._adjacency: Dict[str, Set[str]] = defaultdict(set)  # upstream -> downstream
        self._reverse_adjacency: Dict[str, Set[str]] = defaultdict(set)  # downstream -> upstream
        self._load()

    def _load(self):
        """Load dependency graph from disk."""
        if os.path.exists(DEPENDENCY_PATH):
            try:
                with open(DEPENDENCY_PATH, "r") as f:
                    data = json.load(f)
                for dep_data in data.get("dependencies", []):
                    dep = LoopDependency(
                        upstream_loop_id=dep_data["upstream"],
                        downstream_loop_id=dep_data["downstream"],
                        dependency_type=DependencyType(dep_data.get("type", "hard")),
                        description=dep_data.get("description", ""),
                        created_at=dep_data.get("created_at", datetime.now(timezone.utc).isoformat()),
                        data_mapping=dep_data.get("data_mapping", {}),
                    )
                    self._dependencies.append(dep)
                    self._adjacency[dep.upstream_loop_id].add(dep.downstream_loop_id)
                    self._reverse_adjacency[dep.downstream_loop_id].add(dep.upstream_loop_id)
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        """Persist dependency graph to disk."""
        os.makedirs(os.path.dirname(DEPENDENCY_PATH), exist_ok=True)
        data = {
            "dependencies": [
                {
                    "upstream": dep.upstream_loop_id,
                    "downstream": dep.downstream_loop_id,
                    "type": dep.dependency_type.value,
                    "description": dep.description,
                    "created_at": dep.created_at,
                    "data_mapping": dep.data_mapping,
                }
                for dep in self._dependencies
            ],
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(DEPENDENCY_PATH, "w") as f:
            json.dump(data, f, indent=2)

    def add_dependency(
        self,
        upstream_loop_id: str,
        downstream_loop_id: str,
        dependency_type: DependencyType = DependencyType.HARD,
        description: str = "",
        data_mapping: Optional[Dict[str, str]] = None,
    ) -> Tuple[bool, str]:
        """
        Add a dependency relationship.
        
        Returns:
            Tuple of (success, message)
        """
        # Check for circular dependency
        if self._would_create_cycle(upstream_loop_id, downstream_loop_id):
            return False, f"Adding dependency would create a cycle: {upstream_loop_id} -> {downstream_loop_id}"

        # Check if dependency already exists
        for dep in self._dependencies:
            if dep.upstream_loop_id == upstream_loop_id and dep.downstream_loop_id == downstream_loop_id:
                dep.dependency_type = dependency_type
                dep.description = description
                if data_mapping:
                    dep.data_mapping = data_mapping
                self._save()
                return True, "Dependency updated"

        dep = LoopDependency(
            upstream_loop_id=upstream_loop_id,
            downstream_loop_id=downstream_loop_id,
            dependency_type=dependency_type,
            description=description,
            data_mapping=data_mapping or {},
        )
        self._dependencies.append(dep)
        self._adjacency[upstream_loop_id].add(downstream_loop_id)
        self._reverse_adjacency[downstream_loop_id].add(upstream_loop_id)
        self._save()
        return True, "Dependency added"

    def remove_dependency(self, upstream_loop_id: str, downstream_loop_id: str) -> bool:
        """Remove a dependency relationship."""
        for i, dep in enumerate(self._dependencies):
            if dep.upstream_loop_id == upstream_loop_id and dep.downstream_loop_id == downstream_loop_id:
                del self._dependencies[i]
                self._adjacency[upstream_loop_id].discard(downstream_loop_id)
                self._reverse_adjacency[downstream_loop_id].discard(upstream_loop_id)
                self._save()
                return True
        return False

    def _would_create_cycle(self, upstream: str, downstream: str) -> bool:
        """Check if adding upstream -> downstream would create a cycle."""
        # If there's already a path from downstream to upstream, adding the edge creates a cycle
        visited = set()
        queue = deque([upstream])
        while queue:
            current = queue.popleft()
            if current == downstream:
                return True
            if current in visited:
                continue
            visited.add(current)
            for neighbor in self._adjacency.get(current, set()):
                queue.append(neighbor)
        return False

    def get_dependencies(self, loop_id: str) -> List[LoopDependency]:
        """Get all dependencies where loop_id is the downstream."""
        return [dep for dep in self._dependencies if dep.downstream_loop_id == loop_id]

    def get_dependents(self, loop_id: str) -> List[LoopDependency]:
        """Get all dependencies where loop_id is the upstream."""
        return [dep for dep in self._dependencies if dep.upstream_loop_id == loop_id]

    def get_execution_order(self, loop_ids: Optional[List[str]] = None) -> List[str]:
        """
        Compute topological execution order for loops.
        Returns loops in dependency order (upstream first).
        """
        if loop_ids is None:
            # Include all loops that appear in any dependency
            all_ids = set()
            for dep in self._dependencies:
                all_ids.add(dep.upstream_loop_id)
                all_ids.add(dep.downstream_loop_id)
            loop_ids = list(all_ids)

        # Build in-degree map for the subset
        in_degree: Dict[str, int] = {lid: 0 for lid in loop_ids}
        for dep in self._dependencies:
            if dep.upstream_loop_id in in_degree and dep.downstream_loop_id in in_degree:
                if dep.dependency_type == DependencyType.HARD:
                    in_degree[dep.downstream_loop_id] += 1

        # Kahn's algorithm
        queue = deque([lid for lid, deg in in_degree.items() if deg == 0])
        result = []

        while queue:
            current = queue.popleft()
            result.append(current)
            for dep in self._dependencies:
                if dep.upstream_loop_id == current and dep.downstream_loop_id in in_degree:
                    if dep.dependency_type == DependencyType.HARD:
                        in_degree[dep.downstream_loop_id] -= 1
                        if in_degree[dep.downstream_loop_id] == 0:
                            queue.append(dep.downstream_loop_id)

        if len(result) != len(loop_ids):
            # Cycle detected — return remaining after the ordered ones
            remaining = [lid for lid in loop_ids if lid not in result]
            result.extend(remaining)

        return result

    def get_parallel_batches(self) -> List[ExecutionBatch]:
        """
        Group loops into batches that can execute in parallel.
        Each batch depends only on previous batches.
        """
        # Build full in-degree map
        all_ids = set()
        for dep in self._dependencies:
            all_ids.add(dep.upstream_loop_id)
            all_ids.add(dep.downstream_loop_id)

        if not all_ids:
            return []

        in_degree: Dict[str, int] = {lid: 0 for lid in all_ids}
        for dep in self._dependencies:
            if dep.dependency_type == DependencyType.HARD:
                in_degree[dep.downstream_loop_id] += 1

        batches = []
        batch_number = 0
        remaining = set(all_ids)

        while remaining:
            # Find all loops with no unsatisfied dependencies
            ready = {lid for lid in remaining if in_degree[lid] == 0}
            if not ready:
                # Cycle: put remaining in final batch
                batches.append(ExecutionBatch(
                    batch_number=batch_number,
                    loop_ids=list(remaining),
                    depends_on_batch=batch_number - 1 if batch_number > 0 else None,
                ))
                break

            batches.append(ExecutionBatch(
                batch_number=batch_number,
                loop_ids=list(ready),
                depends_on_batch=batch_number - 1 if batch_number > 0 else None,
            ))

            # Remove ready nodes and update in-degrees
            for lid in ready:
                remaining.discard(lid)
                for dep in self._dependencies:
                    if dep.upstream_loop_id == lid and dep.dependency_type == DependencyType.HARD:
                        if dep.downstream_loop_id in in_degree:
                            in_degree[dep.downstream_loop_id] -= 1

            batch_number += 1

        return batches

    def get_blocked_loops(self, failed_loop_id: str) -> List[str]:
        """Get all loops that would be blocked by a failed upstream loop."""
        blocked = []
        visited = set()
        queue = deque([failed_loop_id])

        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)

            for dep in self._dependencies:
                if dep.upstream_loop_id == current and dep.dependency_type == DependencyType.HARD:
                    if dep.downstream_loop_id not in visited:
                        blocked.append(dep.downstream_loop_id)
                        queue.append(dep.downstream_loop_id)

        return blocked

    def get_dependency_report(self) -> Dict[str, Any]:
        """Get a full report of the dependency graph."""
        all_ids = set()
        for dep in self._dependencies:
            all_ids.add(dep.upstream_loop_id)
            all_ids.add(dep.downstream_loop_id)

        return {
            "total_dependencies": len(self._dependencies),
            "total_loops_in_graph": len(all_ids),
            "hard_dependencies": sum(1 for d in self._dependencies if d.dependency_type == DependencyType.HARD),
            "soft_dependencies": sum(1 for d in self._dependencies if d.dependency_type == DependencyType.SOFT),
            "trigger_dependencies": sum(1 for d in self._dependencies if d.dependency_type == DependencyType.TRIGGER),
            "parallel_batches": len(self.get_parallel_batches()),
            "execution_order": self.get_execution_order(),
            "loops": list(all_ids),
        }


# Global singleton
_dependency_engine: Optional[DependencyGraphEngine] = None


def get_dependency_engine() -> DependencyGraphEngine:
    """Get or create the global DependencyGraphEngine singleton."""
    global _dependency_engine
    if _dependency_engine is None:
        _dependency_engine = DependencyGraphEngine()
    return _dependency_engine
