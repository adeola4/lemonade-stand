#!/usr/bin/env python3
"""
Loop Master — Discord Integration + Recursive Loop Generator
Handles prompt-to-loop generation directly from Discord with recursive capabilities.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


HOME = os.path.expanduser("~")
STORAGE_PATH = os.path.join(HOME, "tan-executive/loop_master/loops.json")
CONTEXT_PATH = "/tmp/loop_prompt_bible_context.txt"
CUSTOM_LOOP_PATH = "/tmp/loop_prompt_bible_custom_loop.json"


# Handler registry — maps keywords to loop entry points
HANDLERS = {
    "deal-sourcing": {
        "description": "Scan for acquisition targets using QLA methodology",
        "default_interval": 3600,
        "keywords": ["deal", "sourcing", "target", "acquire", "acquisition", "buy", "business for sale"],
        "params": ["company", "vertical", "geo"],
    },
    "outreach": {
        "description": "Generate and send outreach to business owners/sellers",
        "default_interval": 1800,
        "keywords": ["outreach", "email", "contact", "reach out", "message", "inbound"],
        "params": ["company", "target", "channel"],
    },
    "pipeline": {
        "description": "Track deal pipeline stages and health",
        "default_interval": 7200,
        "keywords": ["pipeline", "status", "deal flow", "progress", "stage"],
        "params": ["company"],
    },
    "mission-sync": {
        "description": "Sync missions from Discord and QLA systems",
        "default_interval": 3600,
        "keywords": ["mission", "scroll", "task", "assignment", "squad"],
        "params": ["company"],
    },
    "brain-ingest": {
        "description": "Ingest content into Knowledge Brain",
        "default_interval": 86400,
        "keywords": ["brain", "ingest", "url", "article", "learn", "research"],
        "params": ["url", "company"],
    },
    "qla-coach": {
        "description": "Run QLA deal coaching and methodology guidance",
        "default_interval": 86400,
        "keywords": ["qla", "coach", "deal cycle", "methodology", "pena", "quantum leap"],
        "params": ["company", "vertical", "geo"],
    },
    "paperworkman": {
        "description": "Generate founding documents and business plans",
        "default_interval": 86400,
        "keywords": ["paperwork", "intake", "founding", "business plan", "document"],
        "params": ["company", "vertical"],
    },
    "daily-status": {
        "description": "Generate daily status report across all systems",
        "default_interval": 86400,
        "keywords": ["daily", "report", "status", "morning brief", "evening review"],
        "params": ["company"],
    },
    "discord-monitor": {
        "description": "Monitor Discord channels for mentions and opportunities",
        "default_interval": 300,
        "keywords": ["discord", "monitor", "mention", "channel", "server"],
        "params": ["channel_id", "keywords"],
    },
    "custom": {
        "description": "Run custom CLI command or script",
        "default_interval": 300,
        "keywords": ["custom", "script", "command", "cli"],
        "params": ["script"],
    },
}

PRIORITY_MAP = {"low": 1, "normal": 2, "high": 3, "critical": 4}


def detect_handler(prompt: str) -> str:
    """Detect the best handler for a prompt using keyword matching."""
    prompt_lower = prompt.lower()
    scores: Dict[str, int] = {}
    
    for handler_name, handler_info in HANDLERS.items():
        for keyword in handler_info["keywords"]:
            if keyword in prompt_lower:
                scores[handler_name] = scores.get(handler_name, 0) + 1
    
    if scores:
        return max(scores, key=scores.get)
    return "custom"


def detect_interval(prompt: str, handler: str) -> int:
    """Detect the desired interval from time expressions in the prompt."""
    prompt_lower = prompt.lower()
    
    patterns = [
        (r'every\s+(1\s+)?min(ute)?', 60),
        (r'every?\s+5\s+min', 300),
        (r'every?\s+10\s+min', 600),
        (r'every?\s+15\s+min', 900),
        (r'every?\s+30\s+min|half\s+hour', 1800),
        (r'hourly|every?\s+hour', 3600),
        (r'every?\s+2\s+hours', 7200),
        (r'every?\s+4\s+hours', 14400),
        (r'every?\s+6\s+hours', 21600),
        (r'every?\s+12\s+hours', 43200),
        (r'daily|every?\s+day', 86400),
        (r'weekly|every?\s+week', 604800),
    ]
    
    for pattern, seconds in patterns:
        if re.search(pattern, prompt_lower):
            return seconds
    
    return HANDLERS[handler]["default_interval"]


def detect_priority(prompt: str) -> int:
    """Detect priority from urgency keywords."""
    prompt_lower = prompt.lower()
    if "critical" in prompt_lower or "urgent" in prompt_lower or "asap" in prompt_lower:
        return 4
    elif "high" in prompt_lower or "important" in prompt_lower:
        return 3
    elif "low" in prompt_lower or "background" in prompt_lower or "nice to have" in prompt_lower:
        return 1
    return 2


def extract_param(prompt: str, param_name: str) -> Optional[str]:
    """Extract a parameter value from the prompt using word-boundary matching."""
    prompt_lower = prompt.lower()
    
    patterns = {
        "company": [
            r'(?:for|at)\s+([A-Z][a-zA-Z\s&]+?)(?:\s+(?:in|every|hourly|daily|weekly|$)|\.{1,3}$)',
            r'(?:company|business|corp)\s+["\']?([A-Z][a-zA-Z\s&]+?)["\']?(?:\s|$)',
        ],
        "vertical": [
            r'(?:vertical|industry|sector|category|niche)\s+["\']?([a-zA-Z\s/]+?)["\']?(?:\s+(?:in|every|hourly|daily|$)|\.{1,3}$)',
            r'(?:for|about)\s+([A-Z][a-zA-Z\s]+?)(?:\s+(?:in|every|hourly|daily|$)|\.{1,3}$)',
        ],
        "geo": [
            r'(?:in|around|near|across)\s+([A-Z][a-zA-Z\s]+?)(?:\s+(?:every|hourly|daily|$)|\.{1,3}$)',
            r'(?:geo|location|region|area)\s+["\']?([A-Z][a-zA-Z\s]+?)["\']?(?:\s|$)',
        ],
        "channel_id": [
            r'(?:channel|#)\s*(\d{17,19})',
        ],
        "url": [
            r'(https?://[^\s]+)',
        ],
    }
    
    for pattern in patterns.get(param_name, []):
        # Only use IGNORECASE for non-first-character matches
        match = re.search(pattern, prompt)
        if match:
            result = match.group(1).strip()
            result = re.sub(r'\.{1,3}$', '', result).strip()
            if len(result) > 2:
                return result
    
    return None


def generate_loop_config(prompt: str, company: str = "tan") -> Dict[str, Any]:
    """Generate a complete loop configuration from a prompt."""
    handler = detect_handler(prompt)
    interval = detect_interval(prompt, handler)
    priority = detect_priority(prompt)
    
    # Extract params
    params: Dict[str, Any] = {"company": company}
    for param_name in HANDLERS[handler].get("params", []):
        if param_name == "company":
            extracted = extract_param(prompt, "company")
            if extracted:
                params["company"] = extracted
        else:
            extracted = extract_param(prompt, param_name)
            if extracted:
                params[param_name] = extracted
    
    # Generate name
    words = prompt.split()
    if len(words) <= 6:
        name = prompt.strip().title()
    else:
        name = " ".join(words[:5]).strip().title() + "..."
    
    return {
        "name": name,
        "description": f"Generated from prompt: {prompt}",
        "entry_point": handler,
        "interval": interval,
        "priority": priority,
        "params": params,
    }


def create_loop(config: Dict[str, Any], auto_start: bool = False) -> str:
    """Create a loop in the Loop Master storage."""
    os.makedirs(os.path.dirname(STORAGE_PATH), exist_ok=True)
    
    if os.path.exists(STORAGE_PATH):
        with open(STORAGE_PATH, "r") as f:
            storage = json.load(f)
    else:
        storage = {"loops": [], "saved_at": datetime.now(timezone.utc).isoformat()}
    
    loop_id = str(uuid.uuid4())[:12]
    loop = {
        "id": loop_id,
        "name": config.get("name", "Untitled Loop"),
        "description": config.get("description", ""),
        "status": "running" if auto_start else "stopped",
        "entry_point": config["entry_point"],
        "interval": config["interval"],
        "priority": config.get("priority", 2),
        "params": config.get("params", {}),
        "max_retries": 3,
        "retry_count": 0,
        "timeout": 300,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "last_run": None,
        "last_error": None,
        "run_count": 0,
        "success_count": 0,
        "error_count": 0,
        "metadata": {},
    }
    
    storage["loops"].append(loop)
    storage["saved_at"] = datetime.now(timezone.utc).isoformat()
    
    with open(STORAGE_PATH, "w") as f:
        json.dump(storage, f, indent=2)
    
    return loop_id


def list_loops(filter_status: Optional[str] = None) -> List[Dict]:
    """List all loops, optionally filtered by status."""
    if not os.path.exists(STORAGE_PATH):
        return []
    
    with open(STORAGE_PATH, "r") as f:
        storage = json.load(f)
    
    loops = storage.get("loops", [])
    if filter_status:
        loops = [l for l in loops if l["status"] == filter_status]
    return loops


def control_loop(loop_id: str, action: str) -> bool:
    """Start/stop/pause/freeze/resume/delete a loop."""
    if not os.path.exists(STORAGE_PATH):
        return False
    
    with open(STORAGE_PATH, "r") as f:
        storage = json.load(f)
    
    for i, loop in enumerate(storage["loops"]):
        if loop["id"] == loop_id:
            if action in ("start", "resume"):
                loop["status"] = "running"
            elif action == "stop":
                loop["status"] = "stopped"
            elif action == "pause":
                loop["status"] = "paused"
            elif action == "freeze":
                loop["status"] = "frozen"
            elif action == "delete":
                del storage["loops"][i]
            
            loop["updated_at"] = datetime.now(timezone.utc).isoformat()
            with open(STORAGE_PATH, "w") as f:
                json.dump(storage, f, indent=2)
            return True
    
    return False


def get_status_summary() -> Dict[str, Any]:
    """Get summary statistics of all loops."""
    loops = list_loops()
    total = len(loops)
    by_status = {}
    for status in ["running", "stopped", "paused", "frozen", "error", "completed"]:
        by_status[status] = sum(1 for l in loops if l["status"] == status)
    
    return {
        "total": total,
        "by_status": by_status,
        "total_runs": sum(l.get("run_count", 0) for l in loops),
        "total_errors": sum(l.get("error_count", 0) for l in loops),
    }


# ---------------------------------------------------------------------------
# Recursive Loop Generation — loops that create other loops
# ---------------------------------------------------------------------------

def recursive_generate(prompt: str, company: str = "tan") -> Dict[str, Any]:
    """
    Generate a recursive loop that can spawn additional loops.
    
    This is for loops like:
    - "Find 10 new deal sources every day and create outreach loops for each"
    - "Monitor Discord for new business ideas and auto-create QLA coaching loops"
    - "Generate a new research loop for every URL posted in #deals"
    """
    config = generate_loop_config(prompt, company)
    config["metadata"]["recursive"] = True
    config["metadata"]["generates_loops"] = True
    
    # Extract the "spawn condition" from the prompt
    prompt_lower = prompt.lower()
    
    # Detect what kind of loops this should spawn
    if "outreach" in prompt_lower or "contact" in prompt_lower:
        config["metadata"]["spawns"] = "outreach"
    elif "deal" in prompt_lower:
        config["metadata"]["spawns"] = "deal-sourcing"
    elif "qla" in prompt_lower or "coach" in prompt_lower:
        config["metadata"]["spawns"] = "qla-coach"
    else:
        config["metadata"]["spawns"] = "custom"
    
    # Detect the quantity (e.g., "10 new" or "5 loops")
    qty_match = re.search(r'(\d+)\s*(new|loops|deals|targets)', prompt_lower)
    if qty_match:
        config["metadata"]["spawn_count"] = int(qty_match.group(1))
    else:
        config["metadata"]["spawn_count"] = 1
    
    return config


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: discord_integration.py <command> [args]")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "generate":
        prompt = " ".join(sys.argv[2:])
        config = generate_loop_config(prompt)
        print(json.dumps(config, indent=2))
    
    elif cmd == "create":
        prompt = " ".join(sys.argv[2:])
        config = generate_loop_config(prompt)
        loop_id = create_loop(config)
        print(f"OK: Loop {loop_id} created")
    
    elif cmd == "create-start":
        prompt = " ".join(sys.argv[2:])
        config = generate_loop_config(prompt)
        loop_id = create_loop(config, auto_start=True)
        print(f"OK: Loop {loop_id} created and started")
    
    elif cmd == "recursive":
        prompt = " ".join(sys.argv[2:])
        config = recursive_generate(prompt)
        loop_id = create_loop(config, auto_start=True)
        print(f"OK: Recursive loop {loop_id} created")
    
    elif cmd == "list":
        status_filter = sys.argv[2] if len(sys.argv) > 2 else None
        loops = list_loops(status_filter)
        print(json.dumps(loops, indent=2))
    
    elif cmd == "control":
        # control <loop_id> <action>
        loop_id = sys.argv[2]
        action = sys.argv[3]
        if control_loop(loop_id, action):
            print(f"OK: Loop {loop_id} {action}")
        else:
            print(f"FAIL: Could not {action} loop {loop_id}")
    
    elif cmd == "status":
        summary = get_status_summary()
        print(json.dumps(summary, indent=2))
    
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
