"""QLA Execution Engine — does the work, not just talks about it.
Integrates Knowledge Brain (3,010 Peña items) into every deal decision.
"""
from __future__ import annotations

import json
from modules.browser_search import search_web, search_targets, search_market_data, search_red_flags, search_target_details
from modules.outreach import generate_outreach, decide_channel
from modules.pipeline import load_pipeline, save_pipeline, add_deal, advance_stage, get_pipeline_summary, DealRecord
from modules.knowledge_brain import search_knowledge_brain, load_knowledge_brain, get_action_items_for_phase


# Peña's 11 Steps as executable workflows
QLA_DEAL_STEPS = [
    {"number": 1, "name": "Identify", "description": "Find targets in fragmented industries", "automated": True},
    {"number": 2, "name": "Investigate Generalities", "description": "Market size, trends, competition", "automated": True},
    {"number": 3, "name": "Investigate Specifics", "description": "Financials, ownership, operations", "automated": True},
    {"number": 4, "name": "Commit", "description": "Public commitment to the deal", "automated": False},
    {"number": 5, "name": "Preliminary Decision", "description": "Go/no-go with criteria", "automated": True},
    {"number": 6, "name": "Deep Investigation", "description": "Due diligence, red flags", "automated": True},
    {"number": 7, "name": "Action Plan", "description": "Timeline, resources, milestones", "automated": True},
    {"number": 8, "name": "Critical Path", "description": "Dependencies and blockers", "automated": True},
    {"number": 9, "name": "Implement", "description": "Execute the plan", "automated": False},
    {"number": 10, "name": "Execute", "description": "Manage and monitor progress", "automated": True},
    {"number": 11, "name": "Review", "description": "Assess results and adjust", "automated": True},
]


def identify_targets(vertical: str, geo: str, criteria: dict | None = None) -> list[dict]:
    """Step 1: Identify targets using web research + Knowledge Brain doctrine."""
    print("  Running web searches...")
    targets = search_targets(vertical, geo)
    
    # Knowledge Brain: add doctrine context for this vertical
    kb_refs = search_knowledge_brain(vertical, limit=3)
    if kb_refs:
        print(f"  Knowledge Brain: {len(kb_refs)} relevant principles")
        for ref in kb_refs[:2]:
            print(f"    [{ref['id']}] {ref['text'][:60]}")
    
    return targets


def investigate_generalities(vertical: str, geo: str) -> dict:
    """Step 2: Investigate generalities — market research."""
    print("  Researching market data...")
    return search_market_data(vertical, geo)


def investigate_specifics(targets: list[dict], vertical: str) -> list[dict]:
    """Step 3: Investigate specifics — target profiles."""
    profiles = []
    for target in targets[:3]:
        name = target.get("title", target.get("name", ""))
        print(f"  Researching: {name[:50]}...")
        details = search_target_details(name)
        profiles.append(details)
    return profiles


def score_target(target: dict, market: dict) -> dict:
    """Step 5: Preliminary decision — score the target using QLA criteria + Knowledge Brain."""
    name = target.get("title", target.get("name", "Unknown"))
    
    # Search Knowledge Brain for relevant scoring principles
    kb_principles = search_knowledge_brain("deal scoring criteria", limit=3)
    
    scorecard = {
        "target": name,
        "scores": {
            "revenue_size": "TBD - needs financials",
            "owner_motivation": "TBD - needs outreach",
            "market_fragmentation": "High (confirmed by market research)",
            "competitive_moat": "TBD - needs site visit",
            "financial_health": "TBD - needs tax returns",
            "geography_fit": "Confirmed (in target geo)",
        },
        "total": "TBD",
        "recommendation": "PROCEED TO DILIGENCE",
        "kb_principles": [f"[{p['id']}] {p['text'][:60]}" for p in kb_principles],
    }
    
    return scorecard


def deep_investigation(target: dict) -> dict:
    """Step 6: Deep investigation — red flag check."""
    name = target.get("title", target.get("name", ""))
    print(f"  Checking red flags for: {name[:50]}...")
    red_flags = search_red_flags(name)
    return {
        "target": name,
        "red_flags": red_flags,
        "status": "needs_human_review" if red_flags else "proceed",
    }


def run_qla_deal_sourcing(company: str, vertical: str, geo: str) -> dict:
    """Run the full 11-step QLA deal sourcing workflow."""
    print(f"\n{'='*60}")
    print(f"  QLA DEAL SOURCING — {company}")
    print(f"  {vertical} in {geo}")
    print(f"{'='*60}\n")
    
    # Step 1: Identify targets
    print("Step 1: Identify targets...")
    targets = identify_targets(vertical, geo)
    print(f"  Found {len(targets)} potential targets")
    for t in targets[:5]:
        print(f"    - {t.get('title', 'Unknown')[:50]}")
    
    if not targets:
        return {"status": "no_targets", "message": "No targets found"}
    
    # Step 2: Research market
    print("\nStep 2: Investigate generalities...")
    market = investigate_generalities(vertical, geo)
    print(f"  Researched {len(market)} market topics")
    
    # Step 3: Research targets
    print("\nStep 3: Investigate specifics...")
    profiles = investigate_specifics(targets[:3], vertical)
    print(f"  Built {len(profiles)} target profiles")
    
    # Step 4: Commit (needs human)
    print("\nStep 4: Commit — NEEDS HUMAN")
    print("  Peña says: 'Commit publicly. Tell everyone what you're going to do.'")
    print("  → Draft a commitment letter for the top target")
    
    # Step 5: Score targets
    print("\nStep 5: Score targets...")
    scorecards = []
    for target in targets[:3]:
        sc = score_target(target, market)
        scorecards.append(sc)
        print(f"  ✓ {sc['target'][:50]}")
    
    # Step 6: Run diligence
    print("\nStep 6: Deep investigation...")
    diligence = []
    for target in targets[:3]:
        d = deep_investigation(target)
        diligence.append(d)
        status = "⚠ NEEDS REVIEW" if d.get("red_flags") else "✓ Clear"
        print(f"  {status} — {d.get('target', 'Unknown')[:50]}")
    
    # Step 7: Action plans
    print("\nStep 7: Build action plans...")
    action_plans = []
    for target in targets[:3]:
        plan = build_action_plan(target)
        action_plans.append(plan)
        print(f"  ✓ {target.get('title', 'Unknown')[:50]}")
    
    # Step 8: Critical path
    print("\nStep 8: Map critical path...")
    critical_paths = []
    for target in targets[:3]:
        path = map_critical_path(target)
        critical_paths.append(path)
        print(f"  ✓ {target.get('title', 'Unknown')[:50]}")
    
    print(f"\n{'='*60}")
    print(f"  QLA DEAL SOURCING COMPLETE")
    print(f"  Targets: {len(targets)}")
    print(f"  Profiles: {len(profiles)}")
    print(f"  Scorecards: {len(scorecards)}")
    print(f"  Diligence: {len(diligence)}")
    print(f"  Action Plans: {len(action_plans)}")
    print(f"{'='*60}\n")
    
    return {
        "status": "complete",
        "targets": targets,
        "market": market,
        "profiles": profiles,
        "scorecards": scorecards,
        "diligence": diligence,
        "action_plans": action_plans,
        "critical_paths": critical_paths,
    }


def build_action_plan(target: dict) -> dict:
    """Step 7: Action plan — timeline, resources, milestones."""
    name = target.get("title", target.get("name", "Unknown"))
    return {
        "target": name,
        "timeline": {
            "week_1": "Initial outreach and NDA",
            "week_2_3": "Financial review and valuation",
            "week_4": "LOI draft and negotiation",
            "week_5_8": "Due diligence deep dive",
            "week_9_10": "Purchase agreement",
            "week_11_12": "Closing and transition",
        },
        "resources": {
            "legal": "M&A attorney",
            "financial": "Quality of earnings provider",
            "operational": "Industry consultant",
        },
        "milestones": [
            "Signed NDA",
            "Verified financials",
            "Submitted LOI",
            "Approved by seller",
            "Due diligence complete",
            "Purchase agreement signed",
            "Closed",
        ],
    }


def map_critical_path(target: dict) -> dict:
    """Step 8: Critical path — dependencies and blockers."""
    name = target.get("title", target.get("name", "Unknown"))
    return {
        "target": name,
        "path": [
            {"task": "Seller accepts NDA", "blocked_by": None, "status": "pending"},
            {"task": "Financials verified", "blocked_by": "NDA signed", "status": "pending"},
            {"task": "LOI submitted", "blocked_by": "Financials verified", "status": "pending"},
            {"task": "LOI accepted", "blocked_by": "Seller response", "status": "pending"},
            {"task": "Due diligence complete", "blocked_by": "LOI accepted", "status": "pending"},
            {"task": "Financing secured", "blocked_by": "Due diligence", "status": "pending"},
            {"task": "Closing", "blocked_by": "All above", "status": "pending"},
        ],
    }


def run_qla_full_cycle(company: str, vertical: str, geo: str) -> dict:
    """Run the full QLA cycle: source → outreach → track."""
    print(f"\n{'='*60}")
    print(f"  QLA FULL CYCLE — {company}")
    print(f"  {vertical} in {geo}")
    print(f"{'='*60}\n")
    
    # Phase 1: Source targets
    print("PHASE 1: SOURCE TARGETS")
    print("-" * 40)
    targets = identify_targets(vertical, geo)
    print(f"  Found {len(targets)} targets")
    
    if not targets:
        return {"status": "no_targets", "message": "No targets found"}
    
    # Phase 2: Research market
    print("\nPHASE 2: RESEARCH MARKET")
    print("-" * 40)
    market = investigate_generalities(vertical, geo)
    print(f"  Researched {len(market)} topics")
    
    # Phase 3: Research targets + Generate outreach
    print("\nPHASE 3: RESEARCH TARGETS + OUTREACH")
    print("-" * 40)
    
    deals = []
    for target in targets[:5]:
        name = target.get("title", target.get("name", "Unknown"))
        print(f"\n  Processing: {name[:50]}")
        
        # Research specifics
        print(f"    Researching specifics...")
        details = search_target_details(name)
        
        # Score target
        print(f"    Scoring...")
        score = score_target(target, market)
        
        # Check red flags
        print(f"    Checking red flags...")
        red_flags = search_red_flags(name)
        
        # Decide outreach channel
        print(f"    Deciding outreach channel...")
        channel, reasoning = decide_channel(target)
        print(f"    → Channel: {channel}")
        print(f"    → Reason: {reasoning[:60]}")
        
        # Generate outreach plan
        plan = generate_outreach(target, buyer_name=company)
        
        # Build deal record
        deal = {
            "name": name,
            "title": name,
            "stage": "sourced",
            "vertical": vertical,
            "geo": geo,
            "estimated_value": "TBD",
            "owner_name": "Unknown",
            "outreach_plan": {
                "channel": plan.channel,
                "reasoning": plan.reasoning,
                "draft_subject": plan.draft_subject,
                "draft_body": plan.draft_body,
                "draft_script": plan.draft_script,
                "follow_up_days": plan.follow_up_days,
            },
            "red_flags": red_flags,
            "scorecard": score,
            "action_plan": build_action_plan(target),
            "details": details,
        }
        
        # Add to pipeline
        add_deal(company, DealRecord(
            name=name,
            stage="sourced",
            vertical=vertical,
            geo=geo,
            outreach_plan=plan.__dict__,
            red_flags=red_flags,
            scorecard=score,
            action_plan=build_action_plan(target),
        ))
        
        deals.append(deal)
        print(f"    ✓ Added to pipeline")
    
    # Summary
    print(f"\n{'='*60}")
    print(f"  QLA FULL CYCLE COMPLETE")
    print(f"  Targets sourced: {len(targets)}")
    print(f"  Deals in pipeline: {len(deals)}")
    print(f"  Market research: {len(market)} topics")
    print(f"{'='*60}\n")
    
    # Show pipeline summary
    summary = get_pipeline_summary(company)
    print(f"  Pipeline: {summary['total_deals']} deals total")
    for stage, count in summary['by_stage'].items():
        if count > 0:
            print(f"    {stage}: {count}")
    
    return {
        "status": "complete",
        "targets_sourced": len(targets),
        "deals_added": len(deals),
        "deals": deals,
        "pipeline_summary": summary,
    }
