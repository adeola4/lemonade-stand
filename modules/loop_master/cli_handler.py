import json
"""
QLA Loop Master CLI commands.
Allows creating, listing, starting, stopping, pausing, freezing, and deleting loops.
"""

from modules.loop_master import LoopMaster, LoopStatus, LoopPriority


def cmd_loop_master(args):
    """Handle loop-master CLI commands."""
    master = LoopMaster()
    
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
