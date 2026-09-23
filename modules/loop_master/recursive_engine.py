"""
Loop Master — Recursive Improvement Engine

The AI reviews execution results between runs and suggests improvements
to the loop's params, entry_point, or workflow steps. The improvement
is ALWAYS a suggestion — it must be applied deterministically.

The key principle: the AI can suggest changes, but the structure of the
loop (handler, interval, priority) is fixed. Only the content of what
the handler does can be refined.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pathlib import Path

from modules.loop_master.executor import LoopExecutor


IMPROVEMENT_PROMPT = """You are a Loop Improvement Engine. Your job is to review the execution history of a loop and suggest improvements.

## Rules

1. **Deterministic improvements only**: You can only suggest changes to:
   - `params` (adjusting values, adding/removing keys)
   - `entry_point` (refining the instruction, making it more specific)
   - `workflow.steps` (adding/removing/reordering steps within the 20-step limit)
   
2. **NO structural changes**: You CANNOT change:
   - `interval` (how often it runs)
   - `priority` (how important it is)
   - `name` (what it's called)
   - The handler/executor (how it runs)

3. **Evidence-based**: Only suggest improvements based on actual execution results. If the loop is succeeding, say so.

4. **No hallucination**: If you don't have enough data to suggest an improvement, return "no_change".

5. **Conservative**: Suggest at most 3 improvements per review. Quality over quantity.

## Output Format

Return JSON with this structure:

```json
{
  "improvements": [
    {
      "type": "param_change",
      "field": "params.sector",
      "old_value": "healthcare",
      "new_value": "healthcare, fintech",
      "reason": "Execution history shows healthcare alone returns too few results. Expanding to fintech based on QLA methodology section 4.2."
    },
    {
      "type": "entry_point_refinement",
      "old": "Find 3 potential M&A targets",
      "new": "Find 5 potential M&A targets with focus on companies showing 20%+ YoY revenue growth",
      "reason": "Past runs consistently returned exactly 3 targets, indicating the cap was limiting discovery."
    }
  ],
  "summary": "Brief summary of what was reviewed and why these improvements are suggested"
}
```

If no improvements are needed:

```json
{
  "improvements": [],
  "summary": "Loop is performing well. No changes suggested."
}
```

## Execution History

"""

IMPROVEMENT_APPLY_PROMPT = """Apply the following improvements to the loop configuration. Output the COMPLETE updated config as JSON.

## Current Config

```json
{current_config}
```

## Improvements to Apply

```json
{improvements}
```

## Rules

1. Apply ALL improvements exactly as specified
2. Keep all other fields unchanged
3. Output ONLY the complete updated JSON config
4. Do not add any fields not in the original config or improvements

## Output

"""


@dataclass
class ImprovementResult:
    """Result of an improvement review."""
    success: bool
    improvements: List[Dict[str, Any]] = field(default_factory=list)
    summary: str = ""
    applied_config: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "improvements": self.improvements,
            "summary": self.summary,
            "applied_config": self.applied_config,
            "error": self.error,
            "timestamp": self.timestamp,
        }


class RecursiveImprovementEngine:
    """
    Reviews loop execution history and suggests/applies improvements.
    
    The AI acts as a reviewer — it can suggest changes but the actual
    application is deterministic (JSON merge).
    """

    def __init__(self, executor: Optional[LoopExecutor] = None):
        self.executor = executor or LoopExecutor()

    def review(
        self,
        loop_config: Dict[str, Any],
        execution_history: List[Dict[str, Any]],
    ) -> ImprovementResult:
        """
        Review execution history and suggest improvements.
        
        Args:
            loop_config: The current loop configuration
            execution_history: Recent execution results (last N iterations)
            
        Returns:
            ImprovementResult with suggested improvements
        """
        if not execution_history:
            return ImprovementResult(
                success=True,
                improvements=[],
                summary="No execution history available for review.",
            )

        # Build the review prompt
        history_text = json.dumps(execution_history[-10:], indent=2, default=str)
        config_text = json.dumps(loop_config, indent=2, default=str)
        
        full_prompt = (
            IMPROVEMENT_PROMPT
            + f"## Loop Configuration\n\n```json\n{config_text}\n```\n\n"
            + f"## Execution History (last {min(10, len(execution_history))} runs)\n\n"
            + f"```json\n{history_text}\n```\n\n"
            + "## Your Review\n\n"
        )

        # Call LLM
        result = self.executor.execute(
            loop_id="improvement_reviewer",
            entry_point=full_prompt,
            params={"history_count": len(execution_history)},
            iteration=0,
        )

        if not result.success:
            return ImprovementResult(
                success=False,
                error=f"LLM call failed: {result.error}",
            )

        # Parse improvements
        improvements_data = self._extract_json(result.response)
        if improvements_data is None:
            return ImprovementResult(
                success=False,
                error="Could not parse improvements from LLM response",
            )

        improvements = improvements_data.get("improvements", [])
        summary = improvements_data.get("summary", "No summary provided.")

        return ImprovementResult(
            success=True,
            improvements=improvements,
            summary=summary,
        )

    def apply_improvements(
        self,
        loop_config: Dict[str, Any],
        improvements: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Apply improvements to a loop config deterministically.
        
        This is a pure JSON merge — no LLM involved.
        """
        updated = json.loads(json.dumps(loop_config))  # deep copy

        for imp in improvements:
            imp_type = imp.get("type", "")

            if imp_type == "param_change":
                field_path = imp.get("field", "")
                new_value = imp.get("new_value")
                self._set_nested(updated, field_path, new_value)

            elif imp_type == "entry_point_refinement":
                updated["entry_point"] = imp.get("new", updated.get("entry_point", ""))

            elif imp_type == "workflow_step_add":
                step = imp.get("step")
                if step and "workflow" in updated and "steps" in updated["workflow"]:
                    updated["workflow"]["steps"].append(step)
                    # Re-sort by order
                    updated["workflow"]["steps"].sort(key=lambda s: s.get("order", 0))

            elif imp_type == "workflow_step_remove":
                step_order = imp.get("step_order")
                if step_order and "workflow" in updated and "steps" in updated["workflow"]:
                    updated["workflow"]["steps"] = [
                        s for s in updated["workflow"]["steps"]
                        if s.get("order") != step_order
                    ]

            elif imp_type == "workflow_step_modify":
                step_order = imp.get("step_order")
                new_step = imp.get("step")
                if step_order and new_step and "workflow" in updated and "steps" in updated["workflow"]:
                    for i, s in enumerate(updated["workflow"]["steps"]):
                        if s.get("order") == step_order:
                            updated["workflow"]["steps"][i] = new_step
                            break

        return updated

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from LLM response."""
        import re
        # Try code blocks (```json ... ``` or ``` ... ```)
        code_block_pattern = r'```(?:json)?\s*\n?(.*?)\n?```'
        matches = re.findall(code_block_pattern, text, re.DOTALL)
        for match in matches:
            try:
                return json.loads(match.strip())
            except json.JSONDecodeError:
                continue
        # Try to find the first { and last } — handles text before/after JSON
        first_brace = text.find('{')
        last_brace = text.rfind('}')
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            try:
                return json.loads(text[first_brace:last_brace + 1])
            except json.JSONDecodeError:
                pass
        # Try the whole response
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            return None

    def _set_nested(self, obj: dict, field_path: str, value: Any):
        """Set a nested field using dot notation (e.g., 'params.sector')."""
        keys = field_path.split(".")
        current = obj
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value


def review_loop(
    loop_config: Dict[str, Any],
    execution_history: List[Dict[str, Any]],
) -> ImprovementResult:
    """Convenience function to review a loop."""
    engine = RecursiveImprovementEngine()
    return engine.review(loop_config, execution_history)


def apply_improvements(
    loop_config: Dict[str, Any],
    improvements: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Convenience function to apply improvements."""
    engine = RecursiveImprovementEngine()
    return engine.apply_improvements(loop_config, improvements)
