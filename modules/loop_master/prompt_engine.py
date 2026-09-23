"""
Loop Master — Prompt-to-Loop Generator + Background Runner Daemon

Converts natural language prompts into executable loop configurations,
runs them 24/7 with full lifecycle management.
"""

from __future__ import annotations

import asyncio
import importlib
import json
import os
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from modules.loop_master.engine import LoopMaster, Loop, LoopStatus, LoopPriority


# ---------------------------------------------------------------------------
# Built-in loop handlers (registered by default)
# ---------------------------------------------------------------------------

def _handler_deal_sourcing(params: dict) -> dict:
    """Run QLA deal sourcing scan."""
    from modules.loop_master.utils import run_cli
    company = params.get("company", "tan")
    vertical = params.get("vertical", "")
    geo = params.get("geo", "")
    result = run_cli(f"python main.py deal-sourcing --company {company} --vertical '{vertical}' --geo '{geo}'")
    return {"status": "ok", "output": result[:500]}


def _handler_outreach(params: dict) -> dict:
    """Generate outreach plan."""
    from modules.loop_master.utils import run_cli
    target = params.get("target", "")
    company = params.get("company", "tan")
    result = run_cli(f"python main.py outreach --target '{target}' --company {company}")
    return {"status": "ok", "output": result[:500]}


def _handler_pipeline(params: dict) -> dict:
    """Check pipeline status."""
    from modules.loop_master.utils import run_cli
    company = params.get("company", "")
    cmd = f"python main.py pipeline"
    if company:
        cmd += f" --company {company}"
    result = run_cli(cmd)
    return {"status": "ok", "output": result[:500]}


def _handler_mission_sync(params: dict) -> dict:
    """Sync mission center."""
    from modules.loop_master.utils import run_cli
    result = run_cli("python main.py mission-stats")
    return {"status": "ok", "output": result[:500]}


def _handler_brain_ingest(params: dict) -> dict:
    """Ingest URL into brain."""
    from modules.loop_master.utils import run_cli
    url = params.get("url", "")
    if not url:
        return {"status": "error", "message": "No URL provided"}
    result = run_cli(f"python main.py brain --url '{url}'")
    return {"status": "ok", "output": result[:500]}


def _handler_qla_coach(params: dict) -> dict:
    """Run QLA deal coaching."""
    from modules.loop_master.utils import run_cli
    company = params.get("company", "tan")
    vertical = params.get("vertical", "")
    geo = params.get("geo", "")
    result = run_cli(f"python main.py qla-cycle --company {company} --vertical '{vertical}' --geo '{geo}'")
    return {"status": "ok", "output": result[:500]}


def _handler_paperworkman(params: dict) -> dict:
    """Run Paperworkman intake."""
    from modules.loop_master.utils import run_cli
    company = params.get("company", "")
    result = run_cli(f"python main.py start --prompt 'Run Paperworkman intake for {company}'")
    return {"status": "ok", "output": result[:500]}


def _handler_daily_status(params: dict) -> dict:
    """Generate daily status report."""
    from modules.loop_master.utils import run_cli
    result = run_cli("python main.py status")
    return {"status": "ok", "output": result[:500]}


def _handler_custom(params: dict) -> dict:
    """Run custom script."""
    script = params.get("script", "")
    if not script:
        return {"status": "error", "message": "No script provided"}
    from modules.loop_master.utils import run_cli
    result = run_cli(script)
    return {"status": "ok", "output": result[:500]}


# Registry of built-in handlers
BUILTIN_HANDLERS: Dict[str, Callable] = {
    "deal-sourcing": _handler_deal_sourcing,
    "outreach": _handler_outreach,
    "pipeline": _handler_pipeline,
    "mission-sync": _handler_mission_sync,
    "brain-ingest": _handler_brain_ingest,
    "qla-coach": _handler_qla_coach,
    "paperworkman": _handler_paperworkman,
    "daily-status": _handler_daily_status,
    "custom": _handler_custom,
}


# ---------------------------------------------------------------------------
# Prompt Interpreter — converts natural language to loop config
# ---------------------------------------------------------------------------

# Keywords that map to handler types
HINT_MAP = {
    "deal": "deal-sourcing",
    "sourcing": "deal-sourcing",
    "target": "deal-sourcing",
    "acquire": "deal-sourcing",
    "outreach": "outreach",
    "email": "outreach",
    "contact": "outreach",
    "pipeline": "pipeline",
    "status": "pipeline",
    "mission": "mission-sync",
    "brain": "brain-ingest",
    "ingest": "brain-ingest",
    "qla": "qla-coach",
    "coach": "qla-coach",
    "paperwork": "paperworkman",
    "intake": "paperworkman",
    "daily": "daily-status",
    "report": "daily-status",
    "script": "custom",
    "custom": "custom",
}

# Stop words to skip when extracting parameters
_STOP_WORDS = {
    "a", "an", "the", "in", "on", "at", "to", "for", "of", "with",
    "and", "or", "but", "not", "is", "are", "was", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might", "can",
    "every", "each", "all", "any", "some", "no", "this", "that",
    "these", "those", "it", "its", "they", "them", "their", "we",
    "our", "you", "your", "my", "me", "mine", "i", "he", "she",
    "him", "her", "his", "hers", "from", "by", "as", "into",
}

# Default intervals per handler type (seconds)
DEFAULT_INTERVALS = {
    "deal-sourcing": 3600,     # hourly
    "outreach": 1800,          # every 30 min
    "pipeline": 7200,          # every 2 hours
    "mission-sync": 3600,      # hourly
    "brain-ingest": 86400,     # daily
    "qla-coach": 86400,        # daily
    "paperworkman": 86400,     # daily
    "daily-status": 86400,     # daily
    "custom": 300,             # every 5 min default
}


def interpret_prompt(prompt: str, company: str = "tan") -> dict:
    """
    Convert a natural language prompt into a loop configuration.
    
    Args:
        prompt: Natural language description of what the loop should do
        company: Default company name to use
        
    Returns:
        dict with keys: name, description, entry_point, interval, priority, params
    """
    prompt_lower = prompt.lower()
    
    # Detect handler type from keywords
    entry_point = "custom"
    score_map: Dict[str, int] = {}
    
    for keyword, handler_type in HINT_MAP.items():
        if keyword in prompt_lower:
            score_map[handler_type] = score_map.get(handler_type, 0) + 1
    
    if score_map:
        entry_point = max(score_map, key=score_map.get)
    
    # Detect interval from prompt
    interval = DEFAULT_INTERVALS.get(entry_point, 300)
    if "every minute" in prompt_lower or "every 1 minute" in prompt_lower:
        interval = 60
    elif "every 5 minute" in prompt_lower or "5 min" in prompt_lower:
        interval = 300
    elif "every 10 minute" in prompt_lower or "10 min" in prompt_lower:
        interval = 600
    elif "every 30 minute" in prompt_lower or "30 min" in prompt_lower:
        interval = 1800
    elif "hourly" in prompt_lower or "every hour" in prompt_lower:
        interval = 3600
    elif "daily" in prompt_lower or "every day" in prompt_lower:
        interval = 86400
    elif "weekly" in prompt_lower:
        interval = 604800
    
    # Detect priority
    priority = LoopPriority.NORMAL
    if "critical" in prompt_lower or "urgent" in prompt_lower:
        priority = LoopPriority.CRITICAL
    elif "high" in prompt_lower:
        priority = LoopPriority.HIGH
    elif "low" in prompt_lower:
        priority = LoopPriority.LOW
    
    # Generate name from prompt
    words = prompt.split()
    if len(words) <= 6:
        name = prompt.strip().title()
    else:
        name = " ".join(words[:5]).strip().title() + "..."
    
    # Build params based on handler type
    params: Dict[str, Any] = {"company": company}
    
    if entry_point == "deal-sourcing":
        # Try to extract vertical and geo from prompt
        vertical = _extract_after(prompt_lower, ["vertical", "industry", "sector", "in"])
        geo = _extract_after(prompt_lower, ["geo", "geography", "region", "in", "around"])
        if vertical:
            params["vertical"] = vertical
        if geo:
            params["geo"] = geo
            
    elif entry_point == "outreach":
        target = _extract_after(prompt_lower, ["target", "to", "with"])
        if target:
            params["target"] = target
            
    elif entry_point == "brain-ingest":
        url = _extract_url(prompt)
        if url:
            params["url"] = url
            
    elif entry_point == "qla-coach":
        vertical = _extract_after(prompt_lower, ["vertical", "industry"])
        geo = _extract_after(prompt_lower, ["geo", "region"])
        if vertical:
            params["vertical"] = vertical
        if geo:
            params["geo"] = geo
            
    elif entry_point == "custom":
        # Check if it's a CLI command
        if prompt.strip().startswith("python") or prompt.strip().startswith("bash"):
            params["script"] = prompt.strip()
        else:
            params["script"] = f"python main.py start --prompt '{prompt}'"
    
    return {
        "name": name,
        "description": f"Auto-generated from prompt: {prompt}",
        "entry_point": entry_point,
        "interval": interval,
        "priority": priority.value,
        "params": params,
    }


def _extract_after(text: str, keywords: list) -> str:
    """Extract text after a keyword, skipping stop words. Uses word-boundary matching."""
    import re
    for kw in keywords:
        # Use word boundary to avoid matching inside words (e.g., "in" in "plumbing")
        pattern = r'\b' + re.escape(kw) + r'\b'
        match = re.search(pattern, text)
        if match:
            after = text[match.end():].strip()
            words = after.split()
            meaningful = []
            for w in words:
                w_clean = w.strip(".,;:!?").lower()
                if w_clean and w_clean not in _STOP_WORDS:
                    meaningful.append(w.strip(".,;:!?"))
                elif meaningful:
                    break
                if len(meaningful) >= 2:
                    break
            result = " ".join(meaningful)
            if result and len(result) > 2:
                return result
    return ""


def _extract_url(text: str) -> str:
    """Extract URL from text."""
    import re
    urls = re.findall(r'https?://[^\s]+', text)
    return urls[0] if urls else ""


# ---------------------------------------------------------------------------
# Background Runner Daemon — runs loops on schedule
# ---------------------------------------------------------------------------

class LoopRunnerDaemon:
    """
    Background daemon that executes loops on their configured intervals.
    Runs continuously until stopped.
    """
    
    def __init__(self, loop_master: LoopLoopMaster):
        self.master = loop_master
        self._running = False
        self._tasks: Dict[str, asyncio.Task] = {}
        self._register_builtin_handlers()
    
    def _register_builtin_handlers(self):
        """Register all built-in handler functions."""
        for name, handler in BUILTIN_HANDLERS.items():
            self.master.register_handler(name, handler)
    
    async def start(self):
        """Start the daemon — begin executing all running loops."""
        self._running = True
        for loop in self.master.list_loops(status=LoopStatus.RUNNING):
            self._spawn(loop)
        # Keep running
        while self._running:
            await asyncio.sleep(1)
    
    def stop(self):
        """Stop the daemon and cancel all running tasks."""
        self._running = False
        for task in self._tasks.values():
            task.cancel()
        self._tasks.clear()
    
    def _spawn(self, loop: Loop):
        """Spawn an async task for a loop."""
        if loop.id in self._tasks:
            self._tasks[loop.id].cancel()
        self._tasks[loop.id] = asyncio.create_task(self._run_loop(loop))
    
    async def _run_loop(self, loop: Loop):
        """Execute a single loop on its interval."""
        while self._running and loop.status == LoopStatus.RUNNING:
            try:
                loop.last_run = datetime.now(timezone.utc).isoformat()
                loop.run_count += 1
                
                # Execute handler
                handler = self.master._handlers.get(loop.entry_point)
                if handler:
                    result = await asyncio.wait_for(
                        asyncio.to_thread(handler, loop.params),
                        timeout=loop.timeout,
                    )
                    loop.success_count += 1
                    loop.last_error = None
                else:
                    loop.error_count += 1
                    loop.last_error = f"No handler for entry_point: {loop.entry_point}"
                
            except asyncio.TimeoutError:
                loop.error_count += 1
                loop.last_error = f"Timeout after {loop.timeout}s"
                loop.retry_count += 1
            except Exception as e:
                loop.error_count += 1
                loop.last_error = str(e)[:200]
                loop.retry_count += 1
                
                # Auto-freeze if too many retries
                if loop.retry_count >= loop.max_retries:
                    loop.status = LoopStatus.ERROR
                    break
            
            self.master._save()
            
            # Wait for next interval (but check status periodically)
            for _ in range(loop.interval):
                if not self._running or loop.status != LoopStatus.RUNNING:
                    break
                await asyncio.sleep(1)
        
        # Remove from tasks when done
        if loop.id in self._tasks:
            del self._tasks[loop.id]
    
    def notify_loop_change(self, loop_id: str, action: str):
        """React to a loop being started/stopped/paused/etc."""
        loop = self.master.get_loop(loop_id)
        if not loop:
            return
        
        if action in ("start", "resume") and loop.status == LoopStatus.RUNNING:
            self._spawn(loop)
        elif action in ("stop", "pause", "freeze", "delete"):
            if loop_id in self._tasks:
                self._tasks[loop_id].cancel()
                del self._tasks[loop_id]


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------

def create_loop_from_prompt(prompt: str, company: str = "tan", auto_start: bool = False) -> Loop:
    """
    Interpret a prompt and create a loop in one step.
    
    Usage:
        loop = create_loop_from_prompt("Scan for plumbing deals in Texas every hour")
    """
    master = LoopMaster()
    config = interpret_prompt(prompt, company)
    loop = master.create_loop(**config)
    if auto_start:
        master.start_loop(loop.id)
    return loop


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "daemon":
        # Run as background daemon
        master = LoopMaster()
        daemon = LoopRunnerDaemon(master)
        print("🚀 Loop Master daemon started — press Ctrl+C to stop")
        try:
            asyncio.run(daemon.start())
        except KeyboardInterrupt:
            daemon.stop()
            print("\nDaemon stopped.")
    else:
        # Interactive test
        test_prompts = [
            "Scan for plumbing deals in Texas every hour",
            "Check pipeline status every 2 hours",
            "Generate outreach to sellers every 30 minutes",
            "Run QLA coaching daily",
        ]
        for p in test_prompts:
            config = interpret_prompt(p)
            print(f"\nPrompt: {p}")
            print(f"  → Name: {config['name']}")
            print(f"  → Handler: {config['entry_point']}")
            print(f"  → Interval: {config['interval']}s")
            print(f"  → Priority: {config['priority']}")
