"""
Loop Master — Document-to-Loop Parser (Prompt Bible)

Accepts any document describing a loop and produces a structured loop config.
The LLM acts as a configurator ONLY — it cannot change the workflow structure,
only define what the fixed handler should do.

The output schema is strict and deterministic. The LLM's output is validated
against the schema before a loop is created.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pathlib import Path

from modules.loop_master.executor import LoopExecutor


# ---------------------------------------------------------------------------
# Schema Definition — the ONLY valid loop config structure
# ---------------------------------------------------------------------------

LOOP_CONFIG_SCHEMA = {
    "type": "object",
    "required": ["name", "description", "entry_point", "interval", "priority", "params", "workflow"],
    "properties": {
        "name": {"type": "string", "minLength": 3, "maxLength": 100},
        "description": {"type": "string", "maxLength": 500},
        "entry_point": {"type": "string", "minLength": 10},
        "interval": {"type": "integer", "minimum": 60, "maximum": 604800},
        "priority": {"type": "integer", "minimum": 1, "maximum": 4},
        "params": {"type": "object"},
        "workflow": {
            "type": "object",
            "required": ["steps"],
            "properties": {
                "steps": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 20,
                    "items": {
                        "type": "object",
                        "required": ["order", "action", "description"],
                        "properties": {
                            "order": {"type": "integer"},
                            "action": {"type": "string"},
                            "description": {"type": "string"},
                            "input_map": {"type": "object"},
                            "output_key": {"type": "string"},
                        }
                    }
                },
                "completion_criteria": {"type": "string"},
                "error_handling": {"type": "string"},
            }
        }
    }
}


# ---------------------------------------------------------------------------
# System Prompt — encodes the "highest agent tech" standards
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a Loop Configuration Engine. Your job is to convert a document describing an autonomous loop into a strict, deterministic loop configuration.

## Rules

1. **Fixed structure**: You define WHAT the loop does, not HOW it executes. The execution is handled by a deterministic Python handler. You cannot change the workflow steps after creation.
2. **No hallucination**: Only use information present in the document. If the document doesn't specify something, use sensible defaults and note them in the description.
3. **Deterministic output**: Your output must be valid JSON matching the schema exactly. No extra fields, no missing fields.
4. **Workflow steps**: Break the loop's work into discrete, ordered steps. Each step should be a single, clear action.
5. **Completion criteria**: Define what "done" means for one iteration. This must be objectively verifiable.
6. **Error handling**: Define what happens when a step fails. Be specific.

## Output Schema

```json
{
  "name": "Loop name (3-100 chars)",
  "description": "What this loop does (max 500 chars)",
  "entry_point": "Natural language instruction for what each iteration should accomplish (min 10 chars)",
  "interval": 3600,
  "priority": 2,
  "params": {
    "key": "value"
  },
  "workflow": {
    "steps": [
      {
        "order": 1,
        "action": "action_name",
        "description": "What this step does",
        "input_map": {"param_name": "source_field"},
        "output_key": "result_field_name"
      }
    ],
    "completion_criteria": "How to verify one iteration succeeded",
    "error_handling": "What to do when a step fails"
  }
}
```

## Priority Levels

1 = LOW (background tasks, nice-to-have)
2 = NORMAL (regular business operations)
3 = HIGH (time-sensitive, important)
4 = CRITICAL (must not fail, immediate attention)

## Interval Guidelines

- 60-300: High-frequency monitoring (seconds)
- 300-3600: Regular operations (minutes)
- 3600-86400: Periodic tasks (hours)
- 86400-604800: Long-running cycles (days/weeks)

## Examples

### Document: "Scan for new M&A targets in healthcare every hour"
```json
{
  "name": "Healthcare M&A Target Scan",
  "description": "Scans for new M&A targets in the healthcare sector, filters by revenue range, and outputs qualified leads.",
  "entry_point": "Find 3 potential M&A targets in the healthcare sector with revenue between $1M-$50M. Return company name, estimated revenue, and one-line thesis.",
  "interval": 3600,
  "priority": 2,
  "params": {
    "sector": "healthcare",
    "revenue_min": 1000000,
    "revenue_max": 50000000,
    "max_results": 3
  },
  "workflow": {
    "steps": [
      {"order": 1, "action": "search", "description": "Search for companies in target sector", "input_map": {"sector": "sector"}, "output_key": "raw_results"},
      {"order": 2, "action": "filter", "description": "Filter by revenue range", "input_map": {"results": "raw_results", "min": "revenue_min", "max": "revenue_max"}, "output_key": "filtered"},
      {"order": 3, "action": "rank", "description": "Rank by strategic fit", "input_map": {"candidates": "filtered"}, "output_key": "ranked"},
      {"order": 4, "action": "format", "description": "Format output as structured leads", "input_map": {"ranked": "ranked"}, "output_key": "output"}
    ],
    "completion_criteria": "At least 1 qualified lead returned with company name, revenue estimate, and thesis",
    "error_handling": "If search returns 0 results, log and retry next interval. If filter removes all, expand revenue range by 20%."
  }
}
```

Now convert the following document into a loop configuration. Output ONLY the JSON, no other text.

"""


@dataclass
class ParsedLoopConfig:
    """Result of parsing a document into a loop config."""
    success: bool
    config: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    raw_response: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "config": self.config,
            "error": self.error,
            "raw_response": self.raw_response,
            "timestamp": self.timestamp,
        }


class DocumentParser:
    """
    Parses a document describing a loop into a structured config.
    
    Uses the Hermes LLM to interpret the document, then validates
    the output against the strict schema.
    """

    def __init__(self, executor: Optional[LoopExecutor] = None):
        self.executor = executor or LoopExecutor()

    def parse(self, document: str, company: str = "tan") -> ParsedLoopConfig:
        """
        Parse a document into a loop config.
        
        Args:
            document: The document describing the loop (any format, any length)
            company: Default company name
            
        Returns:
            ParsedLoopConfig with the validated config or error details
        """
        if not document or len(document.strip()) < 10:
            return ParsedLoopConfig(
                success=False,
                error="Document too short (minimum 10 characters)"
            )

        # Build the full prompt
        full_prompt = f"{SYSTEM_PROMPT}\n\n## Document\n\n{document}\n\n## Company\n\n{company}\n\n## Output\n\n"

        # Call Hermes LLM
        result = self.executor.execute(
            loop_id="document_parser",
            entry_point=full_prompt,
            params={"document_length": len(document)},
            iteration=0,
        )

        if not result.success:
            return ParsedLoopConfig(
                success=False,
                error=f"LLM call failed: {result.error}",
                raw_response=result.response,
            )

        # Extract JSON from response
        config = self._extract_json(result.response)
        if config is None:
            return ParsedLoopConfig(
                success=False,
                error="Could not extract valid JSON from LLM response",
                raw_response=result.response,
            )

        # Validate against schema
        validation_error = self._validate_config(config)
        if validation_error:
            return ParsedLoopConfig(
                success=False,
                error=f"Schema validation failed: {validation_error}",
                raw_response=result.response,
            )

        return ParsedLoopConfig(
            success=True,
            config=config,
            raw_response=result.response,
        )

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from LLM response (handles markdown code blocks and surrounding text)."""
        # Try to find JSON in code blocks first
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

    def _validate_config(self, config: Dict[str, Any]) -> Optional[str]:
        """Validate config against schema. Returns error message or None."""
        # Check required fields
        for field_name in LOOP_CONFIG_SCHEMA["required"]:
            if field_name not in config:
                return f"Missing required field: {field_name}"

        # Check types
        if not isinstance(config.get("name"), str):
            return "name must be a string"
        if not isinstance(config.get("description"), str):
            return "description must be a string"
        if not isinstance(config.get("entry_point"), str):
            return "entry_point must be a string"
        if not isinstance(config.get("interval"), int):
            return "interval must be an integer"
        if not isinstance(config.get("priority"), int):
            return "priority must be an integer"
        if not isinstance(config.get("params"), dict):
            return "params must be an object"

        # Check value constraints
        if len(config["name"]) < 3 or len(config["name"]) > 100:
            return "name must be 3-100 characters"
        if len(config.get("description", "")) > 500:
            return "description must be max 500 characters"
        if len(config["entry_point"]) < 10:
            return "entry_point must be min 10 characters"
        if config["interval"] < 60 or config["interval"] > 604800:
            return "interval must be 60-604800 seconds"
        if config["priority"] < 1 or config["priority"] > 4:
            return "priority must be 1-4"

        # Check workflow
        workflow = config.get("workflow")
        if not isinstance(workflow, dict):
            return "workflow must be an object"
        if "steps" not in workflow:
            return "workflow must have steps"
        steps = workflow["steps"]
        if not isinstance(steps, list) or len(steps) < 1:
            return "workflow.steps must be a non-empty array"
        if len(steps) > 20:
            return "workflow.steps must have max 20 items"

        for i, step in enumerate(steps):
            if not isinstance(step, dict):
                return f"step {i} must be an object"
            if "order" not in step:
                return f"step {i} missing order"
            if "action" not in step:
                return f"step {i} missing action"
            if "description" not in step:
                return f"step {i} missing description"

        return None


def parse_document(document: str, company: str = "tan") -> ParsedLoopConfig:
    """Convenience function to parse a document."""
    parser = DocumentParser()
    return parser.parse(document, company)
