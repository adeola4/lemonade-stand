from modules.loop_master.prompt_engine import interpret_prompt, create_loop_from_prompt
from modules.loop_master.engine import LoopMaster, LoopPriority


def cmd_loop_gen(args):
    """Generate a loop from a natural language prompt."""
    prompt = args.prompt
    company = args.company or "tan"
    auto_start = getattr(args, "auto_start", False)
    
    if not prompt:
        return {"status": "error", "message": "Prompt is required"}
    
    try:
        config = interpret_prompt(prompt, company)
        master = LoopMaster()
        loop = master.create_loop(
            name=config["name"],
            description=config["description"],
            entry_point=config["entry_point"],
            params=config["params"],
            interval=config["interval"],
            priority=LoopPriority(config["priority"]),
        )
        if auto_start:
            master.start_loop(loop.id)
        
        return {
            "status": "ok",
            "message": f"Loop '{loop.name}' created from prompt",
            "loop": loop.to_dict(),
            "config": config,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
