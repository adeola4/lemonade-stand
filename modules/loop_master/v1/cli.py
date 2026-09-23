"""
Loop Master V1 — CLI Commands

All new V1 commands wired into main.py.
"""
from __future__ import annotations

import json
from typing import Any, Dict

from modules.loop_master.v1.state_machine import get_v1_store, LoopV1State, RunStatus, LoopV1, LoopV1Run
from modules.loop_master.v1.session import get_session_store
from modules.loop_master.v1.budget import get_budget_guard
from modules.loop_master.v1.scheduler import get_scheduler, validate_cron, cron_to_human
from modules.loop_master.v1.approval import get_approval_service, ApprovalCategory
from modules.loop_master.v1.evidence import get_evidence_store
from modules.loop_master.v1.agents import get_orchestrator
from modules.loop_master.v1.harness import get_harness_config


def cmd_loop_v1_create(args):
    """Create a goal-driven loop with completion criteria."""
    store = get_v1_store()
    
    loop = LoopV1(
        name=args.name,
        description=getattr(args, "description", "") or "",
        goal=getattr(args, "goal", "") or args.name,
        completion_criteria=getattr(args, "criteria", "") or "",
        priority=int(getattr(args, "priority", 2) or 2),
        max_iterations=int(getattr(args, "max_iterations", 100) or 100),
        max_turns_per_run=int(getattr(args, "max_turns", 50) or 50),
        max_tokens_per_run=int(getattr(args, "max_tokens", 100000) or 100000),
        max_wall_time_seconds=int(getattr(args, "max_wall_time", 3600) or 3600),
        cron=getattr(args, "cron", None),
        timezone=getattr(args, "timezone", "UTC"),
        requires_approval=getattr(args, "requires_approval", False),
        monthly_budget_cents=float(args.budget) if getattr(args, "budget", None) else None,
        est_run_cost_cents=float(getattr(args, "est_cost", 5.0) or 5.0),
    )
    
    # Add tags if provided
    if getattr(args, "tags", None):
        loop.tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    
    store.create(loop)
    
    # If cron is set, register with scheduler
    if loop.cron:
        is_valid, error = validate_cron(loop.cron)
        if is_valid:
            from modules.loop_master.v1.scheduler import ScheduleEntry
            scheduler = get_scheduler()
            scheduler.add_schedule(ScheduleEntry(
                loop_id=loop.id,
                cron=loop.cron,
                timezone=loop.timezone,
            ))
        else:
            return {
                "status": "warning",
                "message": f"Loop created but cron is invalid: {error}",
                "loop": loop.to_dict(),
            }
    
    return {
        "status": "ok",
        "message": f"V1 Loop created: {loop.id}",
        "loop": loop.to_dict(),
        "next_steps": [
            f"python main.py loop-v1-start {loop.id}",
            f"python main.py loop-v1-status {loop.id}",
        ]
    }


def cmd_loop_v1_start(args):
    """Start a loop with harness + budget."""
    store = get_v1_store()
    budget = get_budget_guard()
    scheduler = get_scheduler()
    
    loop = store.get(args.loop_id)
    if not loop:
        return {"status": "error", "message": "Loop not found"}
    
    # Check state
    if loop.state == LoopV1State.COMPLETED:
        return {"status": "error", "message": "Loop already completed"}
    if loop.state == LoopV1State.EXECUTING:
        return {"status": "error", "message": "Loop already executing"}
    
    # Budget admission check
    if not budget.can_spend(loop.id, loop.est_run_cost_cents, loop.monthly_budget_cents):
        return {
            "status": "error",
            "message": "Budget admission failed: would exceed budget caps",
            "budget_status": {
                "loop_spent_cents": budget.spent_by(loop.id),
                "loop_cap_cents": loop.monthly_budget_cents,
            }
        }
    
    # Concurrency check
    if scheduler.get_active_count() >= scheduler._max_concurrent:
        return {"status": "error", "message": "Max concurrent runs reached"}
    
    # Check if approval is required
    if loop.requires_approval:
        approval_svc = get_approval_service()
        # Create an approval request for starting this loop
        req = approval_svc.request(
            loop_id=loop.id,
            run_id="",
            category=ApprovalCategory.COMMAND,
            tool_name="loop_start",
            arguments={"loop_name": loop.name, "action": "start"},
            reason=f"Starting loop '{loop.name}' with budget {loop.est_run_cost_cents}c",
        )
        
        if req.status.value == "pending":
            loop.state = LoopV1State.PENDING
            store.update(loop.id, state=LoopV1State.PENDING)
            return {
                "status": "pending_approval",
                "message": "Loop requires approval before starting",
                "approval_id": req.id,
                "approval": req.to_dict(),
            }
    
    # Admit and start
    from modules.loop_master.v1.session import Session
    session_store = get_session_store()
    
    run = LoopV1Run(
        loop_id=loop.id,
        status=RunStatus.RUNNING,
        max_turns=loop.max_turns_per_run,
        max_tokens=loop.max_tokens_per_run,
        trigger=getattr(args, "trigger", "manual"),
        started_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    )
    store.add_run(run)
    
    # Create session
    session = session_store.create(loop_id=loop.id, run_id=run.id)
    run.session_id = session.id
    store.add_run(run)  # Update with session_id
    
    # Update loop state
    loop.state = LoopV1State.EXECUTING
    loop.current_run_id = run.id
    loop.current_session_id = session.id
    loop.last_run_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    loop.total_runs += 1
    store.update(loop.id, **{
        "state": loop.state,
        "total_runs": loop.total_runs,
        "last_run_at": loop.last_run_at,
        "current_session_id": session.id,
    })
    
    # Record budget
    budget.record(loop.id, loop.est_run_cost_cents, run.id)
    
    return {
        "status": "ok",
        "message": f"Loop '{loop.name}' started",
        "loop_id": loop.id,
        "run_id": run.id,
        "session_id": session.id,
        "run": run.to_dict(),
        "next_command": f"python main.py loop-v1-status {loop.id}",
    }


def cmd_loop_v1_status(args):
    """Show loop status with session state + evidence."""
    store = get_v1_store()
    session_store = get_session_store()
    evidence_store = get_evidence_store()
    budget = get_budget_guard()
    
    loop = store.get(args.loop_id)
    if not loop:
        return {"status": "error", "message": "Loop not found"}
    
    # Get active run
    runs = store.list_runs(loop.id)
    active_run = next((r for r in runs if r.status == RunStatus.RUNNING), None)
    
    # Get session
    sessions = session_store.list_for_loop(loop.id)
    active_session = next((s for s in sessions if s.status == "active"), None)
    
    # Get evidence
    evidence = evidence_store.list_for_loop(loop.id)
    certificates = evidence_store.list_certificates(loop.id)
    
    # Build harness status
    from modules.loop_master.v1.harness import Harness, get_harness_config
    if active_run:
        config = get_harness_config(loop)
        harness = Harness(config, loop.id)
        harness._tokens_used = active_run.tokens_used
        harness._turns_used = active_run.turns_used
        harness_status = harness.get_status()
    else:
        harness_status = None
    
    return {
        "status": "ok",
        "loop": loop.to_dict(),
        "active_run": active_run.to_dict() if active_run else None,
        "active_session": active_session.to_dict() if active_session else None,
        "harness_status": harness_status,
        "total_runs": len(runs),
        "total_evidence": len(evidence),
        "latest_certificate": certificates[0].to_dict() if certificates else None,
        "budget": {
            "spent_cents": budget.spent_by(loop.id),
            "cap_cents": loop.monthly_budget_cents,
            "remaining_cents": budget.remaining_for(loop.id, loop.monthly_budget_cents),
        },
        "recent_runs": [r.to_dict() for r in runs[-5:]],
    }


def cmd_loop_v1_approve(args):
    """Approve or reject a pending gate."""
    approval_svc = get_approval_service()
    store = get_v1_store()
    
    action = getattr(args, "approval_action", "approve")
    approval_id = args.approval_id
    
    if action == "reject":
        req = approval_svc.resolve(approval_id, approved=False, reason=getattr(args, "reason", ""))
    else:
        session_wide = getattr(args, "session_wide", False)
        req = approval_svc.resolve(approval_id, approved=True, session_wide=session_wide, reason=getattr(args, "reason", ""))
    
    if not req:
        return {"status": "error", "message": "Approval request not found"}
    
    # If this was a loop start approval, auto-start the loop
    if req.tool_name == "loop_start" and req.status.is_approved:
        loop = store.get(req.loop_id)
        if loop and loop.state == LoopV1State.PENDING:
            # Start the loop
            from modules.loop_master.v1.session import Session
            session_store = get_session_store()
            
            run = LoopV1Run(
                loop_id=loop.id,
                status=RunStatus.RUNNING,
                max_turns=loop.max_turns_per_run,
                max_tokens=loop.max_tokens_per_run,
                trigger="manual_approved",
                started_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
            )
            store.add_run(run)
            
            session = session_store.create(loop_id=loop.id, run_id=run.id)
            run.session_id = session.id
            
            loop.state = LoopV1State.EXECUTING
            loop.total_runs += 1
            store.update(loop.id, **{
                "state": loop.state,
                "total_runs": loop.total_runs,
                "current_session_id": session.id,
            })
    
    return {
        "status": "ok",
        "message": f"Approval {req.status.value}",
        "approval": req.to_dict(),
    }


def cmd_loop_v1_verify(args):
    """Manually trigger verification for a loop run."""
    store = get_v1_store()
    evidence_store = get_evidence_store()
    
    loop = store.get(args.loop_id)
    if not loop:
        return {"status": "error", "message": "Loop not found"}
    
    # Get latest run
    runs = store.list_runs(loop.id)
    if not runs:
        return {"status": "error", "message": "No runs found"}
    
    run_id = getattr(args, "run_id", None) or runs[-1].id
    
    # Trigger verification
    cert = evidence_store.verify_completion(loop.id, run_id)
    
    # Update loop state based on verification
    if cert.verification_status.value == "passed":
        loop.state = LoopV1State.COMPLETED
        loop.total_successes += 1
    elif cert.verification_status.value == "failed":
        loop.state = LoopV1State.FAILED
        loop.total_failures += 1
    else:
        loop.state = LoopV1State.EXECUTING
    
    store.update(loop.id, **{
        "state": loop.state,
        "total_successes": loop.total_successes,
        "total_failures": loop.total_failures,
    })
    
    return {
        "status": "ok",
        "message": f"Verification {cert.verification_status.value}",
        "certificate": cert.to_dict(),
        "new_state": loop.state.value,
    }


def cmd_loop_v1_sessions(args):
    """List active sessions with history."""
    session_store = get_session_store()
    store = get_v1_store()
    
    loop_id = getattr(args, "loop_id", None)
    
    if loop_id:
        sessions = session_store.list_for_loop(loop_id)
    else:
        sessions = session_store.list_active()
    
    return {
        "status": "ok",
        "total_sessions": len(sessions),
        "sessions": [
            {
                **s.to_dict(),
                "loop_name": store.get(s.loop_id).name if store.get(s.loop_id) else "Unknown",
            }
            for s in sessions
        ],
        "session_stats": session_store.get_stats(),
    }


def cmd_loop_v1_compact(args):
    """Manually trigger context compaction."""
    session_store = get_session_store()
    
    session = session_store.get(args.session_id)
    if not session:
        return {"status": "error", "message": "Session not found"}
    
    # Check if compaction is needed
    if not session.needs_compaction(session.metadata.get("max_context_chars", 400000)):
        return {
            "status": "ok",
            "message": "Compaction not yet needed",
            "context_chars": session.context_chars,
            "threshold": session.metadata.get("max_context_chars", 400000) * 0.9,
        }
    
    # Perform compaction (summary would come from LLM in real usage)
    summary_text = getattr(args, "summary", "Manual compaction performed")
    result = session.compact(summary_text)
    session_store.update(session)
    
    return {
        "status": "ok",
        "message": "Session compacted",
        "compaction": result,
        "session": session.to_dict(),
    }


def cmd_loop_v1_budget(args):
    """Show budget status."""
    budget = get_budget_guard()
    store = get_v1_store()
    
    loop_id = getattr(args, "loop_id", None)
    
    if loop_id:
        loop = store.get(loop_id)
        if not loop:
            return {"status": "error", "message": "Loop not found"}
        
        return {
            "status": "ok",
            "loop_id": loop_id,
            "loop_name": loop.name,
            "spent_cents": budget.spent_by(loop_id),
            "cap_cents": loop.monthly_budget_cents,
            "remaining_cents": budget.remaining_for(loop_id, loop.monthly_budget_cents),
            "recent_spend": budget.get_history(loop_id, limit=10),
        }
    
    return {
        "status": "ok",
        "budget": budget.get_status(),
        "loop_details": [
            {
                "loop_id": loop_id,
                "loop_name": store.get(loop_id).name if store.get(loop_id) else "Unknown",
                "spent_cents": budget.spent_by(loop_id),
            }
            for loop_id in budget.get_loop_ids()
        ],
    }


def cmd_loop_v1_evidence(args):
    """Show evidence for a loop run."""
    evidence_store = get_evidence_store()
    store = get_v1_store()
    
    loop_id = getattr(args, "loop_id", None)
    run_id = getattr(args, "run_id", None)
    
    if run_id:
        evidence = evidence_store.list_for_run(run_id)
        certificates = [c for c in evidence_store.certificates.values() if c.run_id == run_id]
    elif loop_id:
        evidence = evidence_store.list_for_loop(loop_id)
        certificates = evidence_store.list_certificates(loop_id)
    else:
        evidence = list(evidence_store.evidence.values())
        certificates = list(evidence_store.certificates.values())
    
    return {
        "status": "ok",
        "total_evidence": len(evidence),
        "total_certificates": len(certificates),
        "evidence": [e.to_dict() for e in evidence[-20:]],  # Last 20
        "certificates": [c.to_dict() for c in certificates[-5:]],  # Last 5
    }


def cmd_loop_v1_list(args):
    """List all V1 loops."""
    store = get_v1_store()
    
    state_filter = getattr(args, "state", None)
    state = LoopV1State(state_filter) if state_filter else None
    
    loops = store.list_all(state=state)
    
    return {
        "status": "ok",
        "total_loops": len(loops),
        "loops": [loop.to_dict() for loop in loops],
    }


def cmd_loop_v1_stop(args):
    """Stop/pause a loop."""
    store = get_v1_store()
    session_store = get_session_store()
    
    loop = store.get(args.loop_id)
    if not loop:
        return {"status": "error", "message": "Loop not found"}
    
    action = getattr(args, "v1_action", "pause")
    
    if action == "pause":
        if not loop.state.can_pause:
            return {"status": "error", "message": f"Cannot pause from state {loop.state.value}"}
        new_state = LoopV1State.PAUSED
    elif action == "complete":
        new_state = LoopV1State.COMPLETED
        loop.total_successes += 1
    elif action == "fail":
        new_state = LoopV1State.FAILED
        loop.total_failures += 1
    else:
        return {"status": "error", "message": f"Unknown action: {action}"}
    
    old_state = loop.state
    loop.state = new_state
    store.update(loop.id, state=new_state, total_successes=loop.total_successes, total_failures=loop.total_failures)
    
    # Close active session
    if loop.current_session_id:
        session_store.close(loop.current_session_id)
    
    return {
        "status": "ok",
        "message": f"Loop '{loop.name}' moved from {old_state.value} to {new_state.value}",
        "loop": loop.to_dict(),
    }


def cmd_loop_v1_delete(args):
    """Delete a V1 loop."""
    store = get_v1_store()
    scheduler = get_scheduler()
    
    loop = store.get(args.loop_id)
    if not loop:
        return {"status": "error", "message": "Loop not found"}
    
    name = loop.name
    store.delete(args.loop_id)
    scheduler.remove_schedule(args.loop_id)
    
    return {
        "status": "ok",
        "message": f"Loop '{name}' deleted",
        "loop_id": args.loop_id,
    }


def cmd_loop_v1_dashboard(args):
    """Get full dashboard data for V1 loops."""
    store = get_v1_store()
    session_store = get_session_store()
    evidence_store = get_evidence_store()
    budget = get_budget_guard()
    scheduler = get_scheduler()
    approval_svc = get_approval_service()
    
    loops = store.list_all()
    active_runs = store.get_active_runs()
    pending_approvals = approval_svc.list_pending()
    
    return {
        "status": "ok",
        "summary": {
            "total_loops": len(loops),
            "by_state": {
                state.value: sum(1 for l in loops if l.state == state)
                for state in LoopV1State
            },
            "active_runs": len(active_runs),
            "pending_approvals": len(pending_approvals),
        },
        "budget": budget.get_status(),
        "sessions": session_store.get_stats(),
        "evidence": evidence_store.get_summary(),
        "scheduler": scheduler.get_status(),
        "loops": [loop.to_dict() for loop in loops],
        "active_runs": [r.to_dict() for r in active_runs],
        "pending_approvals": [a.to_dict() for a in pending_approvals],
    }
