#!/usr/bin/env python3
"""
Loop Master — Template Library Module

Pre-built loop templates for common business patterns:
- Deal sourcing templates
- Outreach sequences
- Content pipelines
- Monitoring loops
- Report generators
- Custom composite templates
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

TEMPLATES_PATH = os.path.expanduser("~/tan-executive/loop_master/templates.json")


@dataclass
class LoopTemplate:
    """A pre-configured loop template."""
    id: str
    name: str
    description: str
    category: str  # e.g., "deal-sourcing", "outreach", "monitoring", "content"
    entry_point: str
    default_interval: int
    default_priority: int  # 1=LOW, 2=NORMAL, 3=HIGH, 4=CRITICAL
    default_params: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "entry_point": self.entry_point,
            "default_interval": self.default_interval,
            "default_priority": self.default_priority,
            "default_params": self.default_params,
            "metadata": self.metadata,
            "tags": self.tags,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LoopTemplate":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# Built-in templates
BUILTIN_TEMPLATES: List[LoopTemplate] = [
    # Deal Sourcing Templates
    LoopTemplate(
        id="tmpl-deal-sourcing-hourly",
        name="Hourly Deal Sourcing Scan",
        description="Scan for new acquisition targets every hour across configured verticals and geos",
        category="deal-sourcing",
        entry_point="deal-sourcing",
        default_interval=3600,
        default_priority=3,
        default_params={"company": "tan", "vertical": "", "geo": ""},
        tags=["deal", "sourcing", "acquisition", "hourly"],
        metadata={"author": "system", "version": "1.0"},
    ),
    LoopTemplate(
        id="tmpl-deal-sourcing-deep",
        name="Deep Deal Sourcing Scan",
        description="Comprehensive deal sourcing scan with extended search criteria (daily)",
        category="deal-sourcing",
        entry_point="deal-sourcing",
        default_interval=86400,
        default_priority=2,
        default_params={"company": "tan", "vertical": "", "geo": "", "deep_scan": True},
        tags=["deal", "sourcing", "acquisition", "daily", "deep"],
        metadata={"author": "system", "version": "1.0"},
    ),

    # Outreach Templates
    LoopTemplate(
        id="tmpl-outreach-followup",
        name="Outreach Follow-up Sequence",
        description="Automated follow-up emails to sellers who haven't responded within 72 hours",
        category="outreach",
        entry_point="outreach",
        default_interval=259200,  # 72 hours
        default_priority=3,
        default_params={"company": "tan", "target": "", "channel": "email", "sequence": "followup"},
        tags=["outreach", "followup", "email", "sequence"],
        metadata={"author": "system", "version": "1.0"},
    ),
    LoopTemplate(
        id="tmpl-outreach-initial",
        name="Initial Outreach Blasts",
        description="Send initial outreach messages to new deal targets (every 6 hours)",
        category="outreach",
        entry_point="outreach",
        default_interval=21600,  # 6 hours
        default_priority=2,
        default_params={"company": "tan", "target": "", "channel": "email", "sequence": "initial"},
        tags=["outreach", "initial", "email", "sequence"],
        metadata={"author": "system", "version": "1.0"},
    ),

    # Pipeline Templates
    LoopTemplate(
        id="tmpl-pipeline-health",
        name="Pipeline Health Check",
        description="Check deal pipeline health and flag stalled deals (every 4 hours)",
        category="pipeline",
        entry_point="pipeline",
        default_interval=14400,
        default_priority=2,
        default_params={"company": "tan"},
        tags=["pipeline", "health", "monitoring", "deals"],
        metadata={"author": "system", "version": "1.0"},
    ),
    LoopTemplate(
        id="tmpl-pipeline-stage-advance",
        name="Pipeline Stage Advancement",
        description="Check for deals ready to advance to next stage (every 2 hours)",
        category="pipeline",
        entry_point="pipeline",
        default_interval=7200,
        default_priority=3,
        default_params={"company": "tan", "action": "check_advancement"},
        tags=["pipeline", "advancement", "automation"],
        metadata={"author": "system", "version": "1.0"},
    ),

    # Monitoring Templates
    LoopTemplate(
        id="tmpl-monitor-discord",
        name="Discord Channel Monitor",
        description="Monitor Discord channels for mentions, opportunities, and leads (every 5 min)",
        category="monitoring",
        entry_point="discord-monitor",
        default_interval=300,
        default_priority=3,
        default_params={"channel_id": "", "keywords": []},
        tags=["discord", "monitor", "mentions", "opportunities"],
        metadata={"author": "system", "version": "1.0"},
    ),
    LoopTemplate(
        id="tmpl-monitor-competitor",
        name="Competitor Activity Monitor",
        description="Monitor competitor websites and news for material changes (every 6 hours)",
        category="monitoring",
        entry_point="custom",
        default_interval=21600,
        default_priority=2,
        default_params={"script": "python main.py competitor-monitor --all"},
        tags=["competitor", "monitor", "intelligence"],
        metadata={"author": "system", "version": "1.0"},
    ),

    # Content Templates
    LoopTemplate(
        id="tmpl-content-publish",
        name="Content Publishing Pipeline",
        description="Generate and publish content across platforms (daily)",
        category="content",
        entry_point="custom",
        default_interval=86400,
        default_priority=2,
        default_params={"script": "python main.py content-pipeline --publish"},
        tags=["content", "publishing", "daily", "social"],
        metadata={"author": "system", "version": "1.0"},
    ),
    LoopTemplate(
        id="tmpl-content-curate",
        name="Content Curation",
        description="Curate and ingest relevant content for Knowledge Brain (hourly)",
        category="content",
        entry_point="brain-ingest",
        default_interval=3600,
        default_priority=1,
        default_params={"company": "tan", "url": ""},
        tags=["content", "curation", "brain", "ingest"],
        metadata={"author": "system", "version": "1.0"},
    ),

    # Report Templates
    LoopTemplate(
        id="tmpl-report-daily",
        name="Daily Status Report",
        description="Generate daily status report across all systems",
        category="reporting",
        entry_point="daily-status",
        default_interval=86400,
        default_priority=2,
        default_params={"company": "tan", "format": "full"},
        tags=["report", "daily", "status"],
        metadata={"author": "system", "version": "1.0"},
    ),
    LoopTemplate(
        id="tmpl-report-weekly",
        name="Weekly Performance Report",
        description="Generate weekly performance summary with metrics and trends",
        category="reporting",
        entry_point="daily-status",
        default_interval=604800,
        default_priority=2,
        default_params={"company": "tan", "format": "weekly_summary"},
        tags=["report", "weekly", "performance"],
        metadata={"author": "system", "version": "1.0"},
    ),

    # Brain/Knowledge Templates
    LoopTemplate(
        id="tmpl-brain-digest",
        name="Knowledge Brain Digest",
        description="Process and digest new URLs into Knowledge Brain (every 4 hours)",
        category="knowledge",
        entry_point="brain-ingest",
        default_interval=14400,
        default_priority=1,
        default_params={"company": "tan", "url": ""},
        tags=["brain", "knowledge", "digest", "ingest"],
        metadata={"author": "system", "version": "1.0"},
    ),

    # QLA Templates
    LoopTemplate(
        id="tmpl-qla-coaching",
        name="QLA Deal Coaching",
        description="Run QLA methodology coaching sessions for active deals (daily)",
        category="qla",
        entry_point="qla-coach",
        default_interval=86400,
        default_priority=2,
        default_params={"company": "tan", "vertical": "", "geo": ""},
        tags=["qla", "coaching", "deal-cycle", "methodology"],
        metadata={"author": "system", "version": "1.0"},
    ),
    LoopTemplate(
        id="tmpl-qla-review",
        name="QLA Weekly Review",
        description="Weekly review of QLA deal cycle progress and methodology adherence",
        category="qla",
        entry_point="qla-coach",
        default_interval=604800,
        default_priority=3,
        default_params={"company": "tan", "vertical": "", "geo": "", "mode": "review"},
        tags=["qla", "review", "weekly", "methodology"],
        metadata={"author": "system", "version": "1.0"},
    ),

    # Paperwork Templates
    LoopTemplate(
        id="tmpl-paperwork-intake",
        name="Paperwork Intake Processing",
        description="Process new intake documents and generate founding paperwork",
        category="paperwork",
        entry_point="paperworkman",
        default_interval=86400,
        default_priority=2,
        default_params={"company": "tan"},
        tags=["paperwork", "intake", "founding", "documents"],
        metadata={"author": "system", "version": "1.0"},
    ),
]


class TemplateLibrary:
    """
    Manages loop templates - built-in and custom.
    Allows instant loop creation from templates.
    """

    def __init__(self):
        self._templates: Dict[str, LoopTemplate] = {}
        self._load()

    def _load(self):
        """Load templates from disk (built-in + custom)."""
        # Start with built-in templates
        for tmpl in BUILTIN_TEMPLATES:
            self._templates[tmpl.id] = tmpl

        # Load custom overrides/additions
        if os.path.exists(TEMPLATES_PATH):
            try:
                with open(TEMPLATES_PATH, "r") as f:
                    data = json.load(f)
                for tmpl_data in data.get("custom_templates", []):
                    tmpl = LoopTemplate.from_dict(tmpl_data)
                    self._templates[tmpl.id] = tmpl
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        """Save custom templates to disk."""
        os.makedirs(os.path.dirname(TEMPLATES_PATH), exist_ok=True)
        custom = [
            tmpl.to_dict() for tmpl in self._templates.values()
            if not tmpl.id.startswith("tmpl-") or tmpl.id not in {t.id for t in BUILTIN_TEMPLATES}
        ]
        with open(TEMPLATES_PATH, "w") as f:
            json.dump({"custom_templates": custom}, f, indent=2)

    def get_template(self, template_id: str) -> Optional[LoopTemplate]:
        """Get a template by ID."""
        return self._templates.get(template_id)

    def list_templates(
        self,
        category: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> List[LoopTemplate]:
        """List templates with optional filtering."""
        results = list(self._templates.values())
        if category:
            results = [t for t in results if t.category == category]
        if tag:
            results = [t for t in results if tag in t.tags]
        return results

    def get_categories(self) -> List[str]:
        """Get all unique categories."""
        return sorted(set(t.category for t in self._templates.values()))

    def get_tags(self) -> List[str]:
        """Get all unique tags."""
        all_tags = set()
        for tmpl in self._templates.values():
            all_tags.update(tmpl.tags)
        return sorted(all_tags)

    def create_custom_template(
        self,
        name: str,
        description: str,
        category: str,
        entry_point: str,
        default_interval: int = 3600,
        default_priority: int = 2,
        default_params: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LoopTemplate:
        """Create and store a custom template."""
        template = LoopTemplate(
            id=f"tmpl-custom-{str(uuid.uuid4())[:8]}",
            name=name,
            description=description,
            category=category,
            entry_point=entry_point,
            default_interval=default_interval,
            default_priority=default_priority,
            default_params=default_params or {},
            tags=tags or [],
            metadata=metadata or {},
        )
        self._templates[template.id] = template
        self._save()
        return template

    def delete_custom_template(self, template_id: str) -> bool:
        """Delete a custom template (built-in templates cannot be deleted)."""
        if template_id in {t.id for t in BUILTIN_TEMPLATES}:
            return False
        if template_id in self._templates:
            del self._templates[template_id]
            self._save()
            return True
        return False

    def instantiate_template(
        self,
        template_id: str,
        param_overrides: Optional[Dict[str, Any]] = None,
        interval_override: Optional[int] = None,
        priority_override: Optional[int] = None,
        name_override: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Create a loop configuration from a template.
        
        Returns a dict ready to be passed to LoopMaster.create_loop()
        """
        template = self._templates.get(template_id)
        if not template:
            return None

        # Merge params (overrides take precedence)
        params = {**template.default_params, **(param_overrides or {})}

        return {
            "name": name_override or template.name,
            "description": template.description,
            "entry_point": template.entry_point,
            "params": params,
            "interval": interval_override or template.default_interval,
            "priority": priority_override or template.default_priority,
            "metadata": {
                **template.metadata,
                "template_id": template.id,
                "template_category": template.category,
            },
        }

    def get_catalog(self) -> Dict[str, Any]:
        """Get full template catalog organized by category."""
        catalog: Dict[str, List[Dict]] = {}
        for tmpl in self._templates.values():
            category = tmpl.category
            if category not in catalog:
                catalog[category] = []
            catalog[category].append(tmpl.to_dict())

        return {
            "total_templates": len(self._templates),
            "categories": list(catalog.keys()),
            "by_category": catalog,
        }


# Global singleton
_template_library: Optional[TemplateLibrary] = None


def get_template_library() -> TemplateLibrary:
    """Get or create the global TemplateLibrary singleton."""
    global _template_library
    if _template_library is None:
        _template_library = TemplateLibrary()
    return _template_library
