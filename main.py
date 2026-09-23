"""CLI entry point for the Executive Agent."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add modules to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from modules.executive_loop import (
    parse_idea,
    create_company_state,
    save_company_state,
    load_company_state,
    run_executive_loop,
    load_all_states,
    save_dashboard,
    build_company_scaffold,
)
from modules.research import generate_research_bundle
from modules.checkpoint_tracker import (
    log_checkpoint,
    complete_company,
    format_checkpoint_message,
    notify_user_request,
)
from modules.storage import ensure_dirs, sync_to_drive
from modules import run_qla_deal_sourcing, generate_outreach, run_qla_full_cycle, get_pipeline_summary
from modules.loop_master.cli_handler import cmd_loop_master
from modules.loop_master.gen_handler import cmd_loop_gen
from modules.loop_master.v1.cli import (
    cmd_loop_v1_create,
    cmd_loop_v1_start,
    cmd_loop_v1_status,
    cmd_loop_v1_approve,
    cmd_loop_v1_verify,
    cmd_loop_v1_sessions,
    cmd_loop_v1_compact,
    cmd_loop_v1_budget,
    cmd_loop_v1_evidence,
)
from modules.loop_master.module_commands import (
    cmd_loop_adaptive,
    cmd_loop_deps,
    cmd_loop_notify,
    cmd_loop_heal,
    cmd_loop_metrics,
    cmd_loop_templates,
    cmd_loop_scheduler,
    cmd_loop_resources,
)
from modules.folder_factory import parse_business_doc, generate_folder
from modules.versioning.version import (
    list_versions,
    list_snapshots,
    rollback,
    rollback_to_snapshot,
    get_version,
    create_snapshot,
)


def cmd_new(idea: str, company: str | None = None) -> dict:
    """Create a new company from an idea and run the first iteration."""
    ensure_dirs()
    
    parsed = parse_idea(idea)
    if company:
        parsed["company"] = company
    
    state = create_company_state(
        company=parsed["company"],
        vertical=parsed["vertical"],
        idea=parsed["concept"],
    )
    
    # Build the upgraded scaffold
    slug = parsed["company"].lower().replace(" ", "-")
    root = Path.home() / "tan-executive" / "companies" / slug
    print(f"📁 Building company scaffold at {root}...")
    build_company_scaffold(root, parsed["vertical"], parsed["company"])
    
    # Run Paperworkman intake + document generation
    print(f"📝 Running Paperworkman intake for {parsed['company']}...")
    from modules.paperworkman_integration import run_paperworkman_intake, generate_documents_from_ledger
    
    ledger = run_paperworkman_intake(parsed["company"], parsed["vertical"], parsed["concept"])
    
    # Save ledger
    ledger_path = root / "PAPERWORKMAN" / "readiness_ledger.json"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with open(ledger_path, 'w') as f:
        json.dump(ledger, f, indent=2)
    print(f"✓ Readiness ledger saved to {ledger_path}")
    
    # Generate documents from templates
    docs_dir = root / "PAPERWORKMAN" / "documents"
    generated_docs = generate_documents_from_ledger(ledger, docs_dir)
    for doc_path in generated_docs:
        print(f"✓ Generated: {doc_path.name}")
    

    
    # Check status
    if state.get("status") == "complete":
        complete_company(parsed["company"])
        print(f"✅ {parsed['company']} — Complete!")
    elif state.get("status") == "blocked_on_user":
        blocked = state.get("blocked_on_user", [])
        msg = notify_user_request(parsed["company"], blocked)
        print(msg)
    
    return state


def _collect_web_research(vertical: str) -> dict:
    """Collect web research via agent layer for richer data."""
    results = {}
    try:
        from hermes_tools import web_search
        
        # Market size
        try:
            r = web_search(f"{vertical} market size 2024 2025", limit=3)
            if r and r.get("data", {}).get("web"):
                results["market_size"] = " | ".join(
                    f"{item.get('title', '')}: {item.get('description', '')}"
                    for item in r["data"]["web"][:3]
                )
        except Exception:
            pass
        
        # Fragmentation
        try:
            r = web_search(f"{vertical} industry fragmentation consolidation 2024", limit=3)
            if r and r.get("data", {}).get("web"):
                results["fragmentation"] = " | ".join(
                    f"{item.get('title', '')}: {item.get('description', '')}"
                    for item in r["data"]["web"][:3]
                )
        except Exception:
            pass
        
        # EBITDA multiples
        try:
            r = web_search(f"{vertical} EBITDA multiples valuation 2024", limit=3)
            if r and r.get("data", {}).get("web"):
                results["ebitda_multiples"] = " | ".join(
                    f"{item.get('title', '')}: {item.get('description', '')}"
                    for item in r["data"]["web"][:3]
                )
        except Exception:
            pass        
        # Seller financing
        try:
            r = web_search(f"{vertical} seller financing norms", limit=3)
            if r and r.get("data", {}).get("web"):
                results["seller_financing_norms"] = " | ".join(
                    f"{item.get('title', '')}: {item.get('description', '')}"
                    for item in r["data"]["web"][:3]
                )
        except Exception:
            pass
        
        # Regulatory
        try:
            r = web_search(f"{vertical} regulatory requirements barriers", limit=3)
            if r and r.get("data", {}).get("web"):
                results["regulatory_barriers"] = " | ".join(
                    f"{item.get('title', '')}: {item.get('description', '')}"
                    for item in r["data"]["web"][:3]
                )
        except Exception:
            pass
        
        # Capital stack
        try:
            r = web_search(f"{vertical} acquisition capital stack financing", limit=3)
            if r and r.get("data", {}).get("web"):
                results["capital_stack_norms"] = " | ".join(
                    f"{item.get('title', '')}: {item.get('description', '')}"
                    for item in r["data"]["web"][:3]
                )
        except Exception:
            pass
        
        # Consolidation M&A
        try:
            r = web_search(f"{vertical} acquisition M&A 2024 2025", limit=5)
            if r and r.get("data", {}).get("web"):
                results["consolidation_map"] = [
                    {"title": item.get("title", "")[:100], "url": item.get("url", "")}
                    for item in r["data"]["web"][:5]
                ]
        except Exception:
            pass
            
    except ImportError:
        pass
    
    return results


def cmd_resume(company: str) -> dict:
    """Resume a blocked company."""
    state = load_company_state(company)
    if not state:
        print(f"❌ No state found for {company}")
        return {}
    
    if state.get("status") != "blocked_on_user":
        print(f"Company {company} is not blocked (status: {state.get('status')})")
        return state
    
    # Clear blocked state and continue
    state["status"] = "building"
    state["blocked_on_user"] = []
    save_company_state(state)
    
    print(f"▶️  Resuming {company}...")
    state = run_executive_loop(company, max_iterations=12)
    
    if state.get("status") == "complete":
        complete_company(company)
        print(f"✅ {company} — Complete!")
    elif state.get("status") == "blocked_on_user":
        blocked = state.get("blocked_on_user", [])
        msg = notify_user_request(company, blocked)
        print(msg)
    
    return state


def cmd_status(company: str | None = None) -> dict | list:
    """Get status of one or all companies."""
    if company:
        state = load_company_state(company)
        if state:
            print(json.dumps(state, indent=2))
            return state
        else:
            print(f"❌ No state found for {company}")
            return {}
    else:
        states = load_all_states()
        if states:
            for s in states:
                print(f"{s.get('company', 'unknown')}: {s.get('status', '?')} (iter {s.get('iteration', 0)})")
        else:
            print("No companies found.")
        return states


def main():
    parser = argparse.ArgumentParser(description="Executive Autonomous Business Builder")
    sub = parser.add_subparsers(dest="command")
    
    # New idea
    new_p = sub.add_parser("new", help="Create a new company from an idea")
    new_p.add_argument("idea", help="The business idea")
    new_p.add_argument("--company", "-c", help="Company name (optional)")
    
    # Resume
    resume_p = sub.add_parser("resume", help="Resume a blocked company")
    resume_p.add_argument("company", help="Company name")
    
    # Status
    status_p = sub.add_parser("status", help="Get company status")
    status_p.add_argument("company", nargs="?", help="Company name (omit for all)")
    
    # Brain ingest (single command: python main.py brain <url>)
    brain_p = sub.add_parser("brain", help="Ingest URL into second brain")
    brain_p.add_argument("url", help="URL to ingest (Twitter, GitHub, article, etc.)")
    
    # Brain search
    brain_search_p = sub.add_parser("brain-search", help="Search second brain")
    brain_search_p.add_argument("query", help="Search query")
    brain_search_p.add_argument("--limit", "-n", type=int, default=10, help="Max results")
    
    # Brain list
    brain_list_p = sub.add_parser("brain-list", help="List all brain content")
    
    # QLA Deal Sourcing
    deal_p = sub.add_parser("deal-sourcing", help="Run QLA 11-step deal sourcing workflow")
    deal_p.add_argument("--company", required=True, help="Company name")
    deal_p.add_argument("--vertical", required=True, help="Industry vertical")
    deal_p.add_argument("--geo", required=True, help="Target geography")
    
    # Send outreach email
    send_p = sub.add_parser("send", help="Send outreach email for a deal")
    send_p.add_argument("--company", required=True, help="Company name")
    send_p.add_argument("--deal", required=True, help="Deal/target name")
    send_p.add_argument("--to", required=True, help="Recipient email")
    send_p.add_argument("--owner", default="", help="Owner name")
    
    # Generate document
    doc_p = sub.add_parser("doc", help="Generate deal document")
    doc_p.add_argument("--company", required=True, help="Company name")
    doc_p.add_argument("--deal", required=True, help="Deal/target name")
    doc_p.add_argument("--type", required=True, choices=["loi","nda","offer","diligence","termsheet","purchase"], help="Document type")
    
    # Start QLA process from simple prompt
    start_p = sub.add_parser("start", help="Start QLA process from a prompt (auto-detects company/vertical/idea)")
    start_p.add_argument("prompt", help="Business idea (e.g., 'Build a home health care roll-up in Southeast US')")
    
    # Execute — deterministic deal execution (replaces generative workflow)
    exec_p = sub.add_parser("execute", help="Execute deal using deterministic QLA procedure (Peña 11-step)")
    exec_p.add_argument("--company", required=True, help="Company name")
    exec_p.add_argument("--vertical", required=True, help="Industry vertical")
    exec_p.add_argument("--geo", required=True, help="Geography")
    exec_p.add_argument("--idea", required=True, help="Business idea/prompt")
    
    # KB stats
    kbstats_p = sub.add_parser("kb-stats", help="Knowledge Brain statistics")

    # Approach Generator
    approach_p = sub.add_parser("approaches", help="Generate multiple QLA approaches for a business idea")
    approach_p.add_argument("--idea", required=True, help="Business idea/model")
    approach_p.add_argument("--vertical", required=True, help="Industry vertical")
    approach_p.add_argument("--geo", default="US", help="Geography")
    approach_p.add_argument("--detail", type=int, help="Show detail for approach number N")

    # Outreach
    outreach_p = sub.add_parser("outreach", help="Generate outreach plan for a target")
    outreach_p.add_argument("--company", required=True, help="Company name")
    outreach_p.add_argument("--target", required=True, help="Target name/title")
    outreach_p.add_argument("--owner", default="", help="Owner name (if known)")
    outreach_p.add_argument("--channel", default="", help="Force channel: email|letter|phone|in_person")
    
    # Pipeline
    pipeline_p = sub.add_parser("pipeline", help="View deal pipeline status")
    pipeline_p.add_argument("--company", required=True, help="Company name")

    # Mission Center
    mission_p = sub.add_parser("mission", help="Create/update/list missions for a company")
    mission_p.add_argument("--action", required=True, choices=["create", "list", "get", "update", "delete"], help="Mission action")
    mission_p.add_argument("--title", default="", help="Mission title")
    mission_p.add_argument("--description", default="", help="Mission description")
    mission_p.add_argument("--priority", default="standard", choices=["critical", "standard", "routine"], help="Mission priority")
    mission_p.add_argument("--company", default="", help="Company name")
    mission_p.add_argument("--source", default="agent", choices=["web", "discord", "agent"], help="Mission source")
    mission_p.add_argument("--mission-id", default="", help="Mission ID for get/update/delete")
    mission_p.add_argument("--status", default="", choices=["draft", "active", "blocked", "completed", "archived"], help="Mission status for update")
    mission_p.add_argument("--pct-complete", type=int, default=-1, help="Completion percentage for update")

    # QLA Bot — Deal Automation
    qlabot_p = sub.add_parser("qla-deal", help="QLA Deal — deal automation (board, contacts, pipeline)")
    qlabot_p.add_argument("--action", required=True, choices=["status", "next", "build-board", "build-accounting", "build-legal", "build-banks", "build-sellers", "build-experts", "build-jv", "add-contact", "create-deal", "advance-deal", "log-outreach", "link", "pipeline"], help="QA action")
    qlabot_p.add_argument("--vertical", default="", help="Vertical/industry")
    qlabot_p.add_argument("--geo", default="", help="Geography")
    qlabot_p.add_argument("--name", default="", help="Contact name")
    qlabot_p.add_argument("--company", default="", help="Contact company")
    qlabot_p.add_argument("--category", default="", help="Contact category")
    qlabot_p.add_argument("--contact-id", default="", help="Contact ID")
    qlabot_p.add_argument("--deal-id", default="", help="Deal ID")
    qlabot_p.add_argument("--deal-company", default="", help="Deal company name")
    qlabot_p.add_argument("--stage", default="", help="Deal stage to advance to")
    qlabot_p.add_argument("--notes", default="", help="Notes")
    qlabot_p.add_argument("--channel", default="email", help="Outreach channel")
    qlabot_p.add_argument("--summary", default="", help="Outreach summary")
    qlabot_p.add_argument("--max-results", type=int, default=50, help="Max results for list building")

    # Mission Stats
    mstats_p = sub.add_parser("mission-stats", help="Mission center statistics")
    
    # Loop Master
    loop_p = sub.add_parser("loop-master", help="Create, manage, and monitor autonomous 24/7 loops")
    loop_p.add_argument("--action", required=True, choices=["status", "list", "create", "get", "update", "delete", "start", "stop", "pause", "freeze", "resume", "run-now", "daemon", "execute"], help="Loop action")
    loop_p.add_argument("--loop-id", default="", help="Loop ID")
    loop_p.add_argument("--name", default="", help="Loop name")
    loop_p.add_argument("--description", default="", help="Loop description")
    loop_p.add_argument("--entry-point", default="", help="Loop entry point/handler")
    loop_p.add_argument("--params", default="", help="Loop parameters (JSON)")
    loop_p.add_argument("--interval", type=int, default=60, help="Loop interval in seconds")
    loop_p.add_argument("--priority", type=int, default=2, help="Loop priority (1=Low, 4=Critical)")
    loop_p.add_argument("--status-filter", dest="status", default="", help="Filter by status")
    loop_p.add_argument("--priority-filter", dest="priority", default="", help="Filter by priority")
    
    # Loop Generator — create loops from prompts
    loopgen_p = sub.add_parser("loop-gen", help="Generate a loop from a natural language prompt")
    loopgen_p.add_argument("--prompt", required=True, help="Natural language prompt")
    loopgen_p.add_argument("--company", default="tan", help="Company name")
    loopgen_p.add_argument("--auto-start", action="store_true", help="Auto-start the loop after creation")

    # Document Parser — parse a document into a loop config
    loopparse_p = sub.add_parser("loop-parse", help="Parse a document into a loop configuration")
    loopparse_p.add_argument("--document", required=True, help="Document describing the loop")
    loopparse_p.add_argument("--company", default="tan", help="Company name")

    # Create loop from document
    loopcreatedoc_p = sub.add_parser("loop-create-from-doc", help="Parse a document and create a loop")
    loopcreatedoc_p.add_argument("--document", required=True, help="Document describing the loop")
    loopcreatedoc_p.add_argument("--company", default="tan", help="Company name")
    loopcreatedoc_p.add_argument("--auto-start", action="store_true", help="Auto-start the loop after creation")

    # Recursive improvement — review and suggest improvements
    loopreview_p = sub.add_parser("loop-review", help="Review loop execution history and suggest improvements")
    loopreview_p.add_argument("--loop-id", required=True, help="Loop ID to review")
    loopreview_p.add_argument("--history-count", type=int, default=10, help="Number of recent executions to review")

    # Apply improvements to a loop
    loopapply_p = sub.add_parser("loop-apply", help="Apply improvements to a loop")
    loopapply_p.add_argument("--loop-id", required=True, help="Loop ID to update")
    loopapply_p.add_argument("--improvements", required=True, help="JSON array of improvements to apply")
    
    # Loop engineering modules
    adaptive_p = sub.add_parser("loop-adaptive", help="Adaptive interval engine — auto-adjusts loop timing")
    adaptive_p.add_argument("action", nargs="?", default="report", choices=["report", "suggest", "record"], help="Action to perform")
    adaptive_p.add_argument("--loop-id", help="Loop ID (omit for all)")
    adaptive_p.add_argument("--current-interval", type=int, help="Current interval in seconds")
    adaptive_p.add_argument("--target-interval", type=int, help="Target interval in seconds")
    adaptive_p.add_argument("--duration", type=float, help="Execution duration in seconds")
    adaptive_p.add_argument("--success", help="true/false whether execution succeeded")

    deps_p = sub.add_parser("loop-deps", help="Loop dependency graph — manage inter-loop dependencies")
    deps_p.add_argument("action", nargs="?", default="report", choices=["add", "remove", "blocked", "order", "batches", "report"], help="Action")
    deps_p.add_argument("--upstream", help="Upstream loop ID")
    deps_p.add_argument("--downstream", help="Downstream loop ID")
    deps_p.add_argument("--type", default="hard", choices=["hard", "soft", "data_flow"], help="Dependency type")
    deps_p.add_argument("--description", default="", help="Dependency description")
    deps_p.add_argument("--loop-id", help="Loop ID for blocked/execute-order")
    deps_p.add_argument("--max-parallel", type=int, default=3, help="Max parallel loops")

    notify_p = sub.add_parser("loop-notify", help="Notification system — multi-channel alerts")
    notify_p.add_argument("action", nargs="?", default="list", choices=["send", "log", "configure"], help="Action")
    notify_p.add_argument("--channel", help="Notification channel (discord, slack, email, log)")
    notify_p.add_argument("--severity", default="info", choices=["debug", "info", "warning", "error", "critical"], help="Severity level")
    notify_p.add_argument("--title", help="Notification title")
    notify_p.add_argument("--message", help="Notification message")
    notify_p.add_argument("--notification-id", help="Notification ID for acknowledgement")
    notify_p.add_argument("--rule-action", help="Action for rules (block/escalate/throttle)")
    notify_p.add_argument("--loop-id", help="Loop ID for rule filtering")

    heal_p = sub.add_parser("loop-heal", help="Self-healing — circuit breakers, auto-recovery")
    heal_p.add_argument("action", nargs="?", default="status", choices=["status", "check", "record"], help="Action")
    heal_p.add_argument("--loop-id", help="Loop ID")
    heal_p.add_argument("--failure-threshold", type=int, help="Failures before circuit opens")
    heal_p.add_argument("--recovery-timeout", type=int, help="Seconds before half-open test")
    heal_p.add_argument("--max-retries", type=int, help="Max retries per execution")

    metrics_p = sub.add_parser("loop-metrics", help="Metrics & analytics — execution tracking")
    metrics_p.add_argument("action", nargs="?", default="dashboard", choices=["dashboard", "loop", "throughput", "errors", "trend", "export"], help="Action")
    metrics_p.add_argument("--loop-id", help="Filter by loop ID")
    metrics_p.add_argument("--hours", type=int, default=24, help="Hours window")
    metrics_p.add_argument("--limit", type=int, default=100, help="Max records")

    templates_p = sub.add_parser("loop-templates", help="Template library — 16 pre-built loop templates")
    templates_p.add_argument("action", nargs="?", default="list", choices=["list", "catalog", "get", "instantiate", "create", "delete"], help="Action")
    templates_p.add_argument("--template-id", help="Template ID for show/create")
    templates_p.add_argument("--loop-name", help="Name for created loop")
    templates_p.add_argument("--category", help="Filter by category")
    templates_p.add_argument("--company", default="tan", help="Company slug")
    templates_p.add_argument("--auto-start", action="store_true", help="Auto-start after creation")

    scheduler_p = sub.add_parser("loop-scheduler", help="Advanced scheduler — cron, time windows, priority")
    scheduler_p.add_argument("action", nargs="?", default="summary", choices=["summary", "set", "cron", "check", "next", "remove"], help="Action")
    scheduler_p.add_argument("--loop-id", help="Loop ID for the rule")
    scheduler_p.add_argument("--cron", help="Cron expression (e.g., '0 9 * * 1-5')")
    scheduler_p.add_argument("--timezone", default="UTC", help="Timezone for the rule")
    scheduler_p.add_argument("--priority-boost", type=int, default=0, help="Priority boost amount")
    scheduler_p.add_argument("--window-start", help="Time window start (HH:MM)")
    scheduler_p.add_argument("--window-end", help="Time window end (HH:MM)")
    scheduler_p.add_argument("--window-tz", default="UTC", help="Timezone for time window")
    scheduler_p.add_argument("--rule-id", help="Rule ID for removal")
    scheduler_p.add_argument("--enabled", type=lambda x: x.lower() == 'true', default=None, help="Enable/disable rule")

    resources_p = sub.add_parser("loop-resources", help="Resource monitor — CPU/memory throttling")
    resources_p.add_argument("action", nargs="?", default="status", choices=["status", "check", "trend"], help="Action")
    resources_p.add_argument("--cpu-max", type=float, help="CPU threshold percentage")
    resources_p.add_argument("--memory-max", type=float, help="Memory threshold percentage")
    resources_p.add_argument("--disk-max", type=float, help="Disk threshold percentage")
    resources_p.add_argument("--loop-id", help="Loop ID for throttle/suspend/resume")
    resources_p.add_argument("--throttle-level", choices=["none", "reduce_interval", "suspend", "notify_only"], help="Throttle action")

    # Loop V1 — Goal-Driven Loop Engineering
    v1_create_p = sub.add_parser("loop-v1-create", help="V1: Create a goal-driven loop with completion criteria")
    v1_create_p.add_argument("--name", required=True, help="Loop name")
    v1_create_p.add_argument("--goal", default="", help="Goal statement (what success looks like)")
    v1_create_p.add_argument("--criteria", default="", help="Completion criteria (how to verify success)")
    v1_create_p.add_argument("--description", default="", help="Loop description")
    v1_create_p.add_argument("--company", default="tan", help="Company slug")
    v1_create_p.add_argument("--vertical", default="", help="Industry vertical")
    v1_create_p.add_argument("--geo", default="", help="Target geography")
    v1_create_p.add_argument("--priority", type=int, default=2, choices=[1, 2, 3, 4], help="1=LOW, 2=NORMAL, 3=HIGH, 4=CRITICAL")
    v1_create_p.add_argument("--cron", default="", help="Cron expression for scheduling")
    v1_create_p.add_argument("--timezone", default="UTC", help="Timezone for cron scheduling")
    v1_create_p.add_argument("--max-iterations", type=int, default=100, help="Max loop iterations")
    v1_create_p.add_argument("--max-turns", type=int, default=50, help="Max turns per run")
    v1_create_p.add_argument("--max-tokens", type=int, default=100000, help="Max tokens per run")
    v1_create_p.add_argument("--max-wall-time", type=int, default=3600, help="Max wall time per run (seconds)")
    v1_create_p.add_argument("--budget", type=float, default=0.0, help="Monthly budget in USD")
    v1_create_p.add_argument("--est-cost", type=float, default=5.0, help="Estimated cost per run (cents)")
    v1_create_p.add_argument("--requires-approval", action="store_true", help="Require human approval before execution")
    v1_create_p.add_argument("--tags", default="", help="Comma-separated tags")
    v1_create_p.add_argument("--auto-start", action="store_true", help="Auto-start after creation")

    v1_start_p = sub.add_parser("loop-v1-start", help="V1: Start a goal-driven loop with harness isolation")
    v1_start_p.add_argument("loop_id", help="Loop ID to start")
    v1_start_p.add_argument("--force", action="store_true", help="Force start (skip approval)")

    v1_status_p = sub.add_parser("loop-v1-status", help="V1: Show session state + evidence")
    v1_status_p.add_argument("loop_id", nargs="?", help="Loop ID (omit for all)")
    v1_status_p.add_argument("--verbose", action="store_true", help="Full session history")

    v1_approve_p = sub.add_parser("loop-v1-approve", help="V1: Approve/reject pending gates")
    v1_approve_p.add_argument("approval_id", help="Approval ID")
    v1_approve_p.add_argument("--action", required=True, choices=["approve", "reject"], help="Decision")
    v1_approve_p.add_argument("--note", default="", help="Reason for decision")

    v1_verify_p = sub.add_parser("loop-v1-verify", help="V1: Trigger manual verification")
    v1_verify_p.add_argument("loop_id", help="Loop ID to verify")
    v1_verify_p.add_argument("--evidence", default="", help="Evidence to verify against")

    v1_sessions_p = sub.add_parser("loop-v1-sessions", help="V1: List active sessions with full history")
    v1_sessions_p.add_argument("--active-only", action="store_true", help="Show only active sessions")

    v1_compact_p = sub.add_parser("loop-v1-compact", help="V1: Manually trigger context compaction")
    v1_compact_p.add_argument("loop_id", help="Loop ID")
    v1_compact_p.add_argument("--strategy", default="summarize", choices=["summarize", "truncate", "reextract"], help="Compaction strategy")

    v1_budget_p = sub.add_parser("loop-v1-budget", help="V1: Budget tracking per loop")
    v1_budget_p.add_argument("loop_id", nargs="?", help="Loop ID (omit for all)")
    v1_budget_p.add_argument("--reset", action="store_true", help="Reset budget tracking")

    v1_evidence_p = sub.add_parser("loop-v1-evidence", help="V1: Evidence and completion certificates")
    v1_evidence_p.add_argument("loop_id", nargs="?", help="Loop ID (omit for all)")
    v1_evidence_p.add_argument("--certificate", action="store_true", help="Show completion certificates")

    # Changelog
    changelog_p = sub.add_parser("changelog", help="View full change history")
    changelog_p.add_argument("--limit", "-n", type=int, default=30, help="Max entries")
    
    # Versions
    versions_p = sub.add_parser("versions", help="List all versions")
    
    # Snapshots
    snapshots_p = sub.add_parser("snapshots", help="List all snapshots")
    
    # Rollback
    rollback_p = sub.add_parser("rollback", help="Rollback to a version")
    rollback_p.add_argument("version_id", type=int, help="Version ID to rollback to")
    
    # Snapshot rollback
    snap_rollback_p = sub.add_parser("snapshot-rollback", help="Full rollback to snapshot")
    snap_rollback_p.add_argument("snapshot_id", type=int, help="Snapshot ID")
    
    # QLA Full Cycle (one command, fully autonomous)
    qlabot_p = sub.add_parser("qla-cycle", help="Run full QLA cycle: source → outreach → track")
    qlabot_p.add_argument("--company", required=True, help="Company name")
    qlabot_p.add_argument("--vertical", required=True, help="Industry vertical")
    qlabot_p.add_argument("--geo", required=True, help="Target geography")

    # Launch — create a Discord thread for a deal
    launch_p = sub.add_parser("launch", help="Launch a new deal thread in Discord")
    launch_p.add_argument("--idea", required=True, help="Business idea/model")
    launch_p.add_argument("--company", help="Company name (auto-detected from idea)")
    launch_p.add_argument("--vertical", help="Industry vertical (auto-detected)")
    launch_p.add_argument("--geo", default="", help="Geography")
    launch_p.add_argument("--approach", default="", help="Execution approach")
    launch_p.add_argument("--deal", help="Deal/target name")
    launch_p.add_argument("--parent-channel", default="1530412763166281748", help="Parent channel ID")
    launch_p.add_argument("--guild", default="1527322778615677059", help="Guild ID")

    # List active deal threads
    sub.add_parser("threads", help="List active deal threads")

    # Folder Factory — generate deal system from business doc
    folder_p = sub.add_parser("folder-factory", help="Generate QLA-powered multi-agent deal system from business documentation")
    folder_p.add_argument("doc", help="Business doc text, file path, or URL")
    folder_p.add_argument("--company", "-c", help="Company name (auto-detected if omitted)")
    folder_p.add_argument("--output", default=str(Path.home() / "tan-executive" / "companies"), help="Output directory")

    # Initialize — start QLA after manual thread creation
    init_p = sub.add_parser("initialize", help="Initialize system after Discord thread is created")
    init_p.add_argument("--company", required=True, help="Company name")
    
    args = parser.parse_args()
    
    if args.command == "new":
        result = cmd_new(args.idea, args.company)
    elif args.command == "resume":
        result = cmd_resume(args.company)
    elif args.command == "status":
        result = cmd_status(args.company)
    elif args.command == "brain":
        result = cmd_brain(args.url)
    elif args.command == "brain-search":
        result = cmd_brain_search(args.query, args.limit)
    elif args.command == "brain-list":
        result = cmd_brain_list()
    elif args.command == "qla-deal":
        result = cmd_qla_deal(args)
    elif args.command == "deal-sourcing":
        result = run_qla_deal_sourcing(args.company, args.vertical, args.geo)
    elif args.command == "pipeline":
        result = get_pipeline_summary(args.company)
    elif args.command == "mission":
        result = cmd_mission(args)
    elif args.command == "mission-stats":
        result = get_stats()
    elif args.command == "qla-cycle":
        result = cmd_qla(args)
    elif args.command == "loop-master":
        result = cmd_loop_master(args)
    elif args.command == "loop-gen":
        result = cmd_loop_gen(args)
    elif args.command == "loop-parse":
        result = cmd_loop_parse(args)
    elif args.command == "loop-create-from-doc":
        result = cmd_loop_create_from_doc(args)
    elif args.command == "loop-review":
        result = cmd_loop_review(args)
    elif args.command == "loop-apply":
        result = cmd_loop_apply(args)
    elif args.command == "loop-adaptive":
        result = cmd_loop_adaptive(args)
    elif args.command == "loop-deps":
        result = cmd_loop_deps(args)
    elif args.command == "loop-notify":
        result = cmd_loop_notify(args)
    elif args.command == "loop-heal":
        result = cmd_loop_heal(args)
    elif args.command == "loop-metrics":
        result = cmd_loop_metrics(args)
    elif args.command == "loop-templates":
        result = cmd_loop_templates(args)
    elif args.command == "loop-scheduler":
        result = cmd_loop_scheduler(args)
    elif args.command == "loop-resources":
        result = cmd_loop_resources(args)
    elif args.command == "loop-v1-create":
        result = cmd_loop_v1_create(args)
    elif args.command == "loop-v1-start":
        result = cmd_loop_v1_start(args)
    elif args.command == "loop-v1-status":
        result = cmd_loop_v1_status(args)
    elif args.command == "loop-v1-approve":
        result = cmd_loop_v1_approve(args)
    elif args.command == "loop-v1-verify":
        result = cmd_loop_v1_verify(args)
    elif args.command == "loop-v1-sessions":
        result = cmd_loop_v1_sessions(args)
    elif args.command == "loop-v1-compact":
        result = cmd_loop_v1_compact(args)
    elif args.command == "loop-v1-budget":
        result = cmd_loop_v1_budget(args)
    elif args.command == "loop-v1-evidence":
        result = cmd_loop_v1_evidence(args)
    elif args.command == "outreach":
        # Build target dict from args
        target = {"title": args.target, "name": args.target}
        plan = generate_outreach(target, owner_name=args.owner, buyer_name=args.company)
        result = plan
    elif args.command == "send":
        result = cmd_send_outreach(args.company, args.deal, args.to, args.owner)
    elif args.command == "doc":
        result = cmd_generate_doc(args.company, args.deal, args.type)
    elif args.command == "start":
        result = cmd_start(args.prompt)
    elif args.command == "execute":
        result = cmd_execute(args.company, args.vertical, args.geo, args.idea)
    elif args.command == "approaches":
        result = cmd_approaches(args.idea, args.vertical, args.geo, args.detail)
    elif args.command == "launch":
        result = cmd_launch(args.idea, args.company, args.vertical, args.geo, args.approach, args.deal, args.parent_channel, args.guild)
    elif args.command == "threads":
        result = cmd_threads()
    elif args.command == "initialize":
        result = cmd_initialize(args.company)
    elif args.command == "folder-factory":
        result = cmd_folder_factory(args)
    elif args.command == "kb-stats":
        result = cmd_kb_stats()
    elif args.command == "changelog":
        result = cmd_changelog(args.limit)
    elif args.command == "versions":
        result = cmd_versions()
    elif args.command == "snapshots":
        result = cmd_snapshots()
    elif args.command == "rollback":
        result = cmd_rollback(args.version_id)
    elif args.command == "snapshot-rollback":
        result = cmd_snapshot_rollback(args.snapshot_id)
    else:
        parser.print_help()
        return
    
    # Output result as JSON
    if result is not None:
        import json
        print(json.dumps(result, indent=2, default=str))
    
def cmd_brain_search(query: str, limit: int = 10) -> list[dict]:
    """Search the second brain."""
    results = search_brain(query, limit=limit)
    
    if not results:
        print(f"No results for: {query}")
        return []
    
    print(f"Found {len(results)} results for '{query}':")
    for r in results:
        title = r.get("title", "Untitled")[:60]
        source = r.get("source_type", "?")
        tags = r.get("tags", "") or ""
        print(f"  [{source}] {title}")
        if tags:
            print(f"    Tags: {tags}")
    
    return results


def cmd_brain_list() -> list[dict]:
    """List all brain content."""
    items = list_all()
    
    if not items:
        print("Brain is empty.")
        return []
    
    print(f"Second Brain: {len(items)} items")
    for item in items:
        title = item.get("title", "Untitled")[:60]
        source = item.get("source_type", "?")
        created = item.get("created_at", "")[:10]
        print(f"  [{created}] [{source}] {title}")
    
    return items


def cmd_changelog(limit: int = 30) -> list[dict]:
    """View full change history."""
    items = list_versions(limit=limit)
    if not items:
        print("No changes recorded yet.")
        return []
    
    print(f"📜 Changelog — {len(items)} changes")
    for item in items:
        ts = item.get("timestamp", "")[:19]
        desc = item.get("description", "")[:80]
        typ = item.get("type", "")
        print(f"  [{ts}] ({typ}) {desc}")
    
    return items


def cmd_versions() -> list[dict]:
    """List all versions."""
    return cmd_changelog(limit=100)


def cmd_snapshots() -> list[dict]:
    """List all snapshots."""
    snaps = list_snapshots()
    if not snaps:
        print("No snapshots yet.")
        return []
    
    print(f"📸 Snapshots — {len(snaps)}")
    for s in snaps:
        ts = s.get("timestamp", "")[:19]
        desc = s.get("description", "")[:60]
        print(f"  [{ts}] {desc}")
    
    return snaps


def cmd_rollback(version_id: int) -> dict:
    """Rollback to a version."""
    result = rollback(version_id)
    print(json.dumps(result, indent=2))
    return result


def cmd_snapshot_rollback(snapshot_id: int) -> dict:
    """Full rollback to a snapshot."""
    result = rollback_to_snapshot(snapshot_id)
    print(json.dumps(result, indent=2))
    return result


def cmd_send_outreach(company: str, deal: str, to_email: str, owner_name: str = "") -> dict:
    """Send outreach email for a deal."""
    from modules.email_sender import send_outreach_email
    
    deal_details = {
        "company": company,
        "deal": deal,
        "owner": owner_name,
    }
    
    result = send_outreach_email(to_email, deal, owner_name, company, deal_details)
    
    if result.get("status") == "sent":
        print(f"✓ Email sent to {to_email}")
    else:
        print(f"✗ Failed: {result.get('error', 'Unknown error')}")
    
    return result


def cmd_generate_doc(company: str, deal: str, doc_type: str) -> dict:
    """Generate deal document."""
    from modules.documents import (
        generate_loi, generate_nda, generate_offer_letter,
        generate_term_sheet, generate_due_diligence_checklist,
        generate_purchase_agreement_outline
    )
    
    generators = {
        "loi": generate_loi,
        "nda": generate_nda,
        "offer": generate_offer_letter,
        "diligence": generate_due_diligence_checklist,
        "termsheet": generate_term_sheet,
        "purchase": generate_purchase_agreement_outline,
    }
    
    gen = generators.get(doc_type)
    if not gen:
        return {"error": f"Unknown document type: {doc_type}"}
    
    content = gen(company, "[Seller Name]", deal)
    
    # Save to file
    output_dir = Path(f"~/tan-executive/companies/{company}/docs").expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{deal.replace(' ', '_')}_{doc_type}.txt"
    
    with open(output_path, 'w') as f:
        f.write(content)
    
    print(f"✓ Document saved: {output_path}")
    return {"status": "generated", "path": str(output_path), "content": content}


def cmd_kb_search(query: str, limit: int = 10) -> list[dict]:
    """Search the Knowledge Brain for Peña principles."""
    from modules.knowledge_brain import search_knowledge_brain
    from modules.qla_bot import QABot, ContactCategory, ContactStatus, DealStage, OutreachChannel

    results = search_knowledge_brain(query, limit)
    
    if not results:
        print(f"No results for: {query}")
        return []
    
    print(f"Knowledge Brain — {len(results)} results for: {query}")
    for r in results:
        print(f"  [{r['id']}] ({r['category']}) {r['text'][:80]}...")
    
    return results


def cmd_kb_stats() -> dict:
    """Get Knowledge Brain statistics."""
    from modules.deal_engine import get_registry_stats
    stats = get_registry_stats()
    print(f"Knowledge Brain — {stats['total_items']} action items loaded")
    print(f"\nCategories:")
    for cat, count in sorted(stats['categories'].items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")
    print(f"\nStage Mapping:")
    for stage, count in stats['stage_mapping'].items():
        print(f"  {stage}: {count} categories")
    return stats


def cmd_start(prompt: str) -> dict:
    """Start QLA process from a simple prompt — auto-parses company/vertical/idea from text."""
    from modules.executive_loop import parse_idea
    from modules.deal_engine import execute_deal
    
    ensure_dirs()
    
    parsed = parse_idea(prompt)
    company = parsed.get("company", "New Venture")
    vertical = parsed.get("vertical", parsed.get("industry", "general"))
    geo = parsed.get("geo", parsed.get("location", "US"))
    idea = parsed.get("concept", prompt)
    
    print(f"🚀 Starting QLA process for: {company}")
    print(f"   Vertical: {vertical}")
    print(f"   Geography: {geo}")
    print(f"   Idea: {idea[:100]}...")
    
    state = execute_deal(company, vertical, geo, idea)
    return state.to_dict()


def cmd_execute(company: str, vertical: str, geo: str, idea: str) -> dict:
    """Execute deal using deterministic QLA procedure."""
    from modules.deal_engine import execute_deal
    state = execute_deal(company, vertical, geo, idea)
    return state.to_dict()


def cmd_approaches(idea: str, vertical: str, geo: str, detail: int | None = None) -> dict:
    """Generate multiple QLA-grounded approaches for a business idea."""
    from modules.approach_generator import generate_approaches, render_approaches_text, render_approach_detail
    
    approaches = generate_approaches(idea, vertical, geo)
    
    if detail and 1 <= detail <= len(approaches):
        a = approaches[detail - 1]
        print(render_approach_detail(a))
        return a.__dict__
    else:
        print(render_approaches_text(approaches))
        return {"approaches": [a.__dict__ for a in approaches], "count": len(approaches)}


def cmd_mission(args) -> dict:
    """Create, list, get, update, or delete a mission."""
    from modules.mission_center import create_mission, list_missions, get_mission, update_mission, format_for_discord, get_stats, load_missions, save_missions
    if args.action == "create":
        m = create_mission(
            title=args.title,
            description=args.description,
            priority=args.priority,
            company=args.company,
            source=args.source,
        )
        print(f"🚀 Mission created: {m['mission_id']}")
        return m
    elif args.action == "list":
        missions = list_missions()
        for m in missions:
            print(f"  {m['mission_id']} | {m['priority']} | {m['status']} | {m['title']}")
        return {"missions": missions, "count": len(missions)}
    elif args.action == "get":
        m = get_mission(args.mission_id)
        if m:
            print(format_for_discord(m))
        return m or {}
    elif args.action == "update":
        kwargs = {}
        if args.status:
            kwargs["status"] = args.status
        if args.pct_complete >= 0:
            kwargs["pct_complete"] = args.pct_complete
        m = update_mission(args.mission_id, **kwargs)
        if m:
            print(f"✅ Updated: {m['mission_id']}")
        return m or {}
    elif args.action == "delete":
        missions = load_missions()
        missions = [m for m in missions if m["mission_id"] != args.mission_id]
        save_missions(missions)
        print(f"🗑️ Deleted: {args.mission_id}")
        return {"deleted": args.mission_id}
    return {}


def cmd_qla(args) -> dict:
    from modules.qla_bot import QABot, ContactCategory, ContactStatus, DealStage, OutreachChannel
    """QLA Bot — Full deal automation scaffolding."""
    bot = QABot()

    if args.action == "status":
        return bot.get_pipeline_summary()
    elif args.action == "next":
        return {"actions": bot.get_next_actions()}
    elif args.action == "build-board":
        return bot.build_contact_list(ContactCategory.BOARD_TARGET, args.vertical, args.geo, max_results=args.max_results)
    elif args.action == "build-accounting":
        return bot.build_contact_list(ContactCategory.ACCOUNTING_FIRM, args.vertical, args.geo, max_results=args.max_results)
    elif args.action == "build-legal":
        return bot.build_contact_list(ContactCategory.LEGAL_FIRM, args.vertical, args.geo, max_results=args.max_results)
    elif args.action == "build-banks":
        return bot.build_contact_list(ContactCategory.BANK, args.vertical, args.geo, max_results=args.max_results)
    elif args.action == "build-sellers":
        return bot.build_contact_list(ContactCategory.SELLER, args.vertical, args.geo, max_results=args.max_results)
    elif args.action == "build-experts":
        return bot.build_contact_list(ContactCategory.INDUSTRY_EXPERT, args.vertical, args.geo, max_results=args.max_results)
    elif args.action == "build-jv":
        return bot.build_contact_list(ContactCategory.JV_PARTNER, args.vertical, args.geo, max_results=args.max_results)
    elif args.action == "add-contact":
        cat = ContactCategory(args.category) if args.category else ContactCategory.SERVICE_PROVIDER
        c = bot.add_contact(name=args.name, company=args.company or "", category=cat, notes=args.notes)
        print(f"✅ Contact added: {c.id}")
        return c.to_dict()
    elif args.action == "create-deal":
        d = bot.create_deal(company=args.deal_company or args.company or "", vertical=args.vertical, geo=args.geo, notes=args.notes)
        print(f"✅ Deal created: {d.id}")
        return d.to_dict()
    elif args.action == "advance-deal":
        d = bot.advance_deal(args.deal_id, args.stage)
        if d:
            print(f"✅ Deal advanced to: {d.stage.value}")
            return d.to_dict()
        return {"error": "Deal not found"}
    elif args.action == "log-outreach":
        from dataclasses import asdict
        r = bot.log_outreach(contact_id=args.contact_id, deal_id=args.deal_id or "", channel=args.channel, summary=args.summary)
        print(f"✅ Outreach logged: {r.id}")
        return asdict(r)
    elif args.action == "link":
        bot.link_contact_to_deal(args.contact_id, args.deal_id)
        return {"linked": True}
    return {}


def cmd_launch(
    idea: str,
    company: str | None,
    vertical: str | None,
    geo: str | None,
    approach: str,
    deal: str | None,
    parent_channel_id: str,
    guild_id: str,
) -> dict:
    """Launch a new deal thread — generate ultra deal card for Discord thread creation."""
    from modules.deal_card import generate_ultra_deal_card
    from modules.discord_threads import create_deal_thread
    from modules.executive_loop import parse_idea, build_company_scaffold
    from modules.storage import ensure_dirs
    from pathlib import Path
    
    ensure_dirs()
    parsed = parse_idea(idea)
    if not company:
        company = parsed.get("company", "New Venture")
    if not vertical:
        vertical = parsed.get("vertical", parsed.get("industry", ""))
    if not geo:
        geo = parsed.get("geo", parsed.get("location", ""))
    if not deal:
        deal = parsed.get("concept", idea)
    
    # Create company scaffold
    slug = company.lower().replace(" ", "-")
    root = Path.home() / "tan-executive" / "companies" / slug
    build_company_scaffold(root, vertical or "general", company)
    
    thread = create_deal_thread(
        company=company,
        deal_name=deal,
        approach=approach,
        parent_channel_id=parent_channel_id,
        guild_id=guild_id,
    )
    
    # Generate ultra deal card
    card = generate_ultra_deal_card(
        idea=idea,
        company=company,
        vertical=vertical,
        geo=geo,
        approach=approach,
    )
    
    # Save deal card
    thread_card_path = root / "DEAL_THREAD_CARD.md"
    with open(thread_card_path, "w") as f:
        f.write(card)
    
    output = f"""
🍋 **LEMONADE STAND — DEAL THREAD READY**

**Thread Name:** `{thread.thread_name}`
**Company Folder:** `{root}`

---

**YOUR NEXT STEPS:**

1. **Create a new thread** in Discord under the #lemonade-stand channel
2. **Thread name:** `{thread.thread_name}`
3. **Paste the deal card below** as the first message in the thread:

---

{card}

---

**Company scaffold created at:** `{root}`
**Deal card saved to:** `{thread_card_path}`

Once the thread is created, the QLA process will begin executing the deal.
"""
    print(output)
    
    return {
        "status": "launch_ready",
        "thread_name": thread.thread_name,
        "parent_channel_id": parent_channel_id,
        "deal_card": card,
        "company": company,
        "deal": deal,
        "vertical": vertical,
        "geo": geo,
        "company_folder": str(root),
        "thread_card_path": str(thread_card_path),
    }


def cmd_threads() -> dict:
    """List active deal threads."""
    from pathlib import Path
    
    companies_root = Path.home() / "tan-executive" / "companies"
    if not companies_root.exists():
        return {"threads": [], "message": "No companies yet. Use `launch` to create your first deal thread."}
    
    threads = []
    for company_dir in companies_root.iterdir():
        if company_dir.is_dir():
            card = company_dir / "DEAL_THREAD_CARD.md"
            if card.exists():
                threads.append({
                    "company": company_dir.name,
                    "thread_card": str(card),
                    "company_folder": str(company_dir),
                })
    
    return {"threads": threads, "count": len(threads)}


def cmd_initialize(company: str) -> dict:
    """Initialize the system after a Discord thread has been created.
    
    Run this after creating the thread manually to start the QLA process.
    The system reads the company scaffold and begins executing the deal.
    """
    from modules.executive_loop import load_company_state, save_company_state, build_company_scaffold
    from pathlib import Path
    
    slug = company.lower().replace(" ", "-")
    root = Path.home() / "tan-executive" / "companies" / slug
    
    if not root.exists():
        print(f"Company folder not found: {root}")
        print(f"Run: python main.py launch --company \"{company}\" first")
        return {"status": "error", "message": "Company not found"}
    
    # Load existing state or create new
    state = load_company_state(slug)
    if not state:
        state = {
            "company": company,
            "slug": slug,
            "status": "initialized",
            "created_in_discord": True,
            "scaffold_path": str(root),
        }
    
    state["status"] = "initialized"
    state["created_in_discord"] = True
    save_company_state(state)
    
    print(f"🍋 DEAL INITIALIZED")
    print(f"")
    print(f"Company: {company}")
    print(f"Folder: {root}")
    print(f"Status: Ready for QLA execution")
    print(f"")
    print(f"Next: python main.py execute --company \"{company}\" --vertical \"<vertical>\" --geo \"<geo>\" --idea \"<idea>\"")
    
    return state


def cmd_folder_factory(args) -> dict:
    """Folder Factory — generate complete QLA-powered deal system from business documentation."""
    doc = args.doc
    
    # Load doc from file if path provided
    if Path(doc).exists():
        doc = Path(doc).read_text(encoding="utf-8", errors="ignore")
    
    # Parse business doc
    print(f"📊 Parsing business documentation...")
    parsed = parse_business_doc(doc)
    
    if args.company:
        parsed["company"] = args.company
    
    # Generate folder
    output_root = Path(args.output)
    output_root.mkdir(parents=True, exist_ok=True)
    
    print(f"🏗️  Generating QLA deal system for: {parsed.get('company', 'NewVenture')}")
    result = generate_folder(parsed, output_root)
    
    print(f"")
    print(f"✅ FOLDER FACTORY COMPLETE")
    print(f"")
    print(f"Company: {result['company']}")
    print(f"Folder: {result['folder']}")
    print(f"Agents: {result['agents']}")
    print(f"QLA Phases: {result['qla_phases']}")
    print(f"Deal Structure: {result['deal_structure']}")
    print(f"Human Handoffs: {result['human_handoffs']}")
    print(f"")
    print(f"Next steps:")
    print(f"  1. Review business_model.json for accuracy")
    print(f"  2. Run: python main.py launch --company \"{result['company']}\"")
    print(f"  3. Run: python main.py execute --company \"{result['company']}\" --vertical \"<v>\" --geo \"<g>\" --idea \"<i>\"")
    
    return result


if __name__ == "__main__":
    main()
