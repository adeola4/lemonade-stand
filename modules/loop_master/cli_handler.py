import json
"""
QLA Loop Master CLI commands.
Allows creating, listing, starting, stopping, pausing, freezing, and deleting loops.
"""

from modules.loop_master import LoopMaster, LoopStatus, LoopPriority
from modules.loop_master.document_parser import parse_document, DocumentParser
from modules.loop_master.recursive_engine import review_loop, apply_improvements


def cmd_loop_master(args):
    """Handle loop-master CLI commands."""
    master = LoopMaster()

    if args.action == "execute":
        # Fire one iteration immediately (for testing)
        result = master.run_iteration(args.loop_id)
        return {"status": "ok", "execution": result}

    elif args.action == "daemon":
        # Start/stop the 24/7 daemon
        from modules.loop_master.daemon import get_daemon
        daemon = get_daemon(master)
        if not daemon.is_running:
            daemon.start()
            return {"status": "ok", "message": "Daemon started", "daemon": daemon.get_status()}
        return {"status": "ok", "message": "Daemon already running", "daemon": daemon.get_status()}

    if args.action == "status":
        return {"status": "ok", "data": master.get_stats()}

    elif args.action == "list":
        loops = master.list_loops(
            status=LoopStatus(args.status) if args.status else None,
            priority=LoopPriority(args.priority) if args.priority else None,
        )
        return {"status": "ok", "loops": [l.to_dict() for l in loops]}

    elif args.action == "create":
        priority = LoopPriority(args.priority) if args.priority else LoopPriority.NORMAL
        loop = master.create_loop(
            name=args.name,
            description=args.description or "",
            entry_point=args.entry_point or "",
            params=json.loads(args.params) if args.params else {},
            interval=args.interval or 60,
            priority=priority,
        )
        return {"status": "ok", "message": f"Loop created: {loop.id}", "loop": loop.to_dict()}

    elif args.action == "get":
        loop = master.get_loop(args.loop_id)
        if loop:
            return {"status": "ok", "loop": loop.to_dict()}
        return {"status": "error", "message": "Loop not found"}

    elif args.action == "update":
        updates = {}
        if args.name is not None:
            updates["name"] = args.name
        if args.description is not None:
            updates["description"] = args.description
        if args.interval is not None:
            updates["interval"] = args.interval
        if args.priority is not None:
            updates["priority"] = LoopPriority(args.priority).value
        if args.entry_point is not None:
            updates["entry_point"] = args.entry_point
        if args.params is not None:
            updates["params"] = json.loads(args.params)

        loop = master.update_loop(args.loop_id, **updates)
        if loop:
            return {"status": "ok", "message": "Loop updated", "loop": loop.to_dict()}
        return {"status": "error", "message": "Loop not found"}

    elif args.action == "delete":
        if master.delete_loop(args.loop_id):
            return {"status": "ok", "message": "Loop deleted"}
        return {"status": "error", "message": "Loop not found"}

    elif args.action == "start":
        if master.start_loop(args.loop_id):
            return {"status": "ok", "message": "Loop started"}
        return {"status": "error", "message": "Loop not found or already running"}

    elif args.action == "stop":
        if master.stop_loop(args.loop_id):
            return {"status": "ok", "message": "Loop stopped"}
        return {"status": "error", "message": "Loop not found"}

    elif args.action == "pause":
        if master.pause_loop(args.loop_id):
            return {"status": "ok", "message": "Loop paused"}
        return {"status": "error", "message": "Loop not found or not running"}

    elif args.action == "freeze":
        if master.freeze_loop(args.loop_id):
            return {"status": "ok", "message": "Loop frozen"}
        return {"status": "error", "message": "Loop not found"}

    elif args.action == "resume":
        if master.resume_loop(args.loop_id):
            return {"status": "ok", "message": "Loop resumed"}
        return {"status": "error", "message": "Loop not found or not paused/frozen"}

    elif args.action == "run-now":
        if master.run_loop_now(args.loop_id):
            return {"status": "ok", "message": "Loop triggered"}
        return {"status": "error", "message": "Loop not found or not running"}

    return {"status": "error", "message": f"Unknown action: {args.action}"}


def cmd_loop_parse(args):
    """Parse a document into a loop configuration without creating a loop."""
    try:
        result = parse_document(args.document, args.company)
        return result.to_dict()
    except Exception as e:
        return {"status": "error", "message": str(e)}


def cmd_loop_create_from_doc(args):
    """Parse a document and create a loop from it."""
    try:
        parsed = parse_document(args.document, args.company)
        if not parsed.success:
            return parsed.to_dict()

        config = parsed.config
        master = LoopMaster()
        loop = master.create_loop(
            name=config["name"],
            description=config["description"],
            entry_point=config["entry_point"],
            params=config["params"],
            interval=config["interval"],
            priority=LoopPriority(config["priority"]),
            metadata={"workflow": config.get("workflow", {})},
        )
        if args.auto_start:
            master.start_loop(loop.id)

        return {
            "status": "ok",
            "message": f"Loop '{loop.name}' created from document",
            "loop": loop.to_dict(),
            "parsed_config": config,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def cmd_loop_review(args):
    """Review loop execution history and suggest improvements."""
    try:
        master = LoopMaster()
        loop = master.get_loop(args.loop_id)
        if not loop:
            return {"status": "error", "message": "Loop not found"}

        # Get execution history
        from modules.loop_master.daemon import get_daemon
        daemon = get_daemon(master)
        history = daemon.get_history(loop_id=args.loop_id, limit=args.history_count)

        # Build loop config for review
        loop_config = {
            "name": loop.name,
            "description": loop.description,
            "entry_point": loop.entry_point,
            "interval": loop.interval,
            "priority": loop.priority.value,
            "params": loop.params,
            "workflow": loop.metadata.get("workflow", {}),
        }

        result = review_loop(loop_config, history)
        return result.to_dict()
    except Exception as e:
        return {"status": "error", "message": str(e)}


def cmd_loop_apply(args):
    """Apply improvements to a loop."""
    try:
        master = LoopMaster()
        loop = master.get_loop(args.loop_id)
        if not loop:
            return {"status": "error", "message": "Loop not found"}

        improvements = json.loads(args.improvements)

        loop_config = {
            "name": loop.name,
            "description": loop.description,
            "entry_point": loop.entry_point,
            "interval": loop.interval,
            "priority": loop.priority.value,
            "params": loop.params,
            "workflow": loop.metadata.get("workflow", {}),
        }

        updated_config = apply_improvements(loop_config, improvements)

        # Apply updates
        master.update_loop(
            args.loop_id,
            entry_point=updated_config["entry_point"],
            params=updated_config["params"],
            metadata={"workflow": updated_config.get("workflow", {})},
        )

        return {
            "status": "ok",
            "message": "Improvements applied",
            "loop": master.get_loop(args.loop_id).to_dict(),
            "improvements_applied": improvements,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
