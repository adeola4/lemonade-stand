"""Executive loop: self-question → research → build → repeat.
Upgraded with: agent contracts, task board, exception layer, TWO-BRAIN architecture.
"""
from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Paths
DOCTRINE_MD = Path("/tmp/lemonade_doctrine.md")
COMPANIES_ROOT = Path.home() / "tan-executive" / "companies"
DASHBOARD = Path.home() / "tan-executive" / "dashboard.json"

# New modules
from modules.contract import get_contract, DEFAULT_CONTRACTS, write_contract_templates
from modules.task_board import (
    load_board, save_board, create_task, transition_task,
    TaskState, get_next_todo, get_blocked_tasks, get_workflow_metrics,
    WORKFLOW_TASK_TEMPLATES,
)
from modules.exception_layer import who_decides, build_exception_layer_md, DECISION_RULES
from modules.knowledge_brain import search_knowledge_brain

def knowledge_brain_status() -> dict:
    """Get Knowledge Brain status."""
    from modules.knowledge_brain import load_knowledge_brain
    items = load_knowledge_brain()
    return {
        "total_items": len(items),
        "status": "loaded" if items else "empty",
    }
from modules.cost_optimizer import route_command, Route
from modules.institutional_memory import has_skill, find_matching_skills

# Task categories derived from QLA methodology
TASK_TEMPLATES = [
    "00_MISSION_VISION",
    "01_MINDSET_CONDITIONING",
    "02_PERCEPTION_MANAGEMENT",
    "03_STRATEGY_CONSOLIDATION",
    "04_DEAL_FLOW",
    "05_NEGOTIATION_BANKING",
    "06_CAPITAL_STACK",
    "07_DREAM_TEAM",
    "08_OPERATIONS_EXCELLENCE",
    "09_RESEARCH_INTELLIGENCE",
    "10_EXIT_VALUATION",
    "11_PENA_ISMS_LIBRARY",
    "12_AGENT_TECH",
]


def knowledge_brain_search(query: str, top_k: int = 4) -> str:
    """Search the Knowledge Brain (source doctrine) for relevant content."""
    results = search_knowledge_brain(query, top_k=top_k)
    if not results:
        return ""
    snippets = [f"- Score {r['score']:.2f}: {r['text'][:200]}" for r in results]
    return "\n".join(snippets)


def ai_brain_search(query: str, limit: int = 5) -> str:
    """Search the AI Brain (ingested content) for relevant content."""
    try:
        from modules.brain.ingest import search_brain
        results = search_brain(query, limit=limit)
        if results:
            snippets = []
            for r in results:
                title = r.get("title", "")
                summary = r.get("summary", "")[:200]
                snippets.append(f"- {title}: {summary}")
            return "\n".join(snippets)
    except Exception:
        pass
    return ""


def web_search(query: str, limit: int = 3) -> str:
    """Best-effort free web research. Returns snippet."""
    try:
        result = subprocess.run(
            ["python3", "-c",
             f"from hermes_tools import web_search; "
             f"r=web_search('{query}', limit={limit}); "
             "print(r.get('data',{}).get('web',[]))"],
            capture_output=True, text=True, timeout=25
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()[:1000]
    except Exception:
        pass
    return ""


def brain_search(query: str, limit: int = 5) -> str:
    """Search the second brain for relevant content."""
    try:
        from modules.brain.ingest import search_brain
        results = search_brain(query, limit=limit)
        if results:
            snippets = []
            for r in results:
                title = r.get("title", "")
                summary = r.get("summary", "")[:200]
                snippets.append(f"- {title}: {summary}")
            return "\n".join(snippets)
    except Exception:
        pass
    return ""


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def create_company_state(company: str, vertical: str, idea: str) -> dict:
    """Create initial state for a new company build."""
    return {
        "company": company,
        "vertical": vertical,
        "idea": idea,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "status": "building",
        "iteration": 0,
        "completed_tasks": [],
        "current_task": None,
        "blocked_on_user": [],
        "doctrine_citations": [],
        "output_root": str(COMPANIES_ROOT / slugify(company)),
    }


def save_company_state(state: dict) -> None:
    COMPANIES_ROOT.mkdir(parents=True, exist_ok=True)
    slug = slugify(state["company"])
    out = COMPANIES_ROOT / slug / "state.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    out.write_text(json.dumps(state, indent=2))


def load_company_state(company: str) -> dict | None:
    slug = slugify(company)
    p = COMPANIES_ROOT / slug / "state.json"
    if p.exists():
        return json.loads(p.read_text())
    return None


def save_dashboard(states: list[dict]) -> None:
    COMPANIES_ROOT.mkdir(parents=True, exist_ok=True)
    summary = [{
        "company": s["company"],
        "vertical": s["vertical"],
        "status": s["status"],
        "iteration": s["iteration"],
        "current_task": s.get("current_task"),
        "blocked_count": len(s.get("blocked_on_user", [])),
        "updated_at": s["updated_at"],
    } for s in states]
    DASHBOARD.write_text(json.dumps(summary, indent=2))


def parse_idea(message: str) -> dict:
    """Extract company name, vertical, concept from user message."""
    lines = message.strip().split("\n")
    first = lines[0] if lines else ""
    company = "NewCo"
    vertical = "general"
    concept = message.strip()
    
    # Look for patterns like "build X in Y" or "idea: X for Y"
    name_match = re.search(r'(?:build|create|start|company)\s+["\']?([A-Z][A-Za-z\s]+?)["\']?\s+(?:for|in|doing)', message, re.I)
    if name_match:
        company = name_match.group(1).strip()
    
    # Extract vertical — handle "Build a [VERTICAL] in/for/across..."
    vert_start = re.search(r'(?:build|create|start|establish)\s+(?:a\s+)?(?:company\s+(?:in|for)\s+)?([a-z\s]+(?:care|health|tech|services|food|retail|construction|finance))', message, re.I)
    if vert_start:
        vertical = vert_start.group(1).strip()
    
    # Fallback: vertical after "in/for/across the"
    if vertical == "general":
        fallback = re.search(r'(?:in|for|across)\s+(?:the\s+)?([a-z\s]+(?:care|health|tech|services|food|retail|construction|finance|industry|sector|market))', message, re.I)
        if fallback:
            vertical = fallback.group(1).strip()
    
    return {"company": company, "vertical": vertical, "concept": concept, "source_message": message}


def executive_iteration(state: dict) -> dict:
    """Run one iteration of the self-question → research → build loop."""
    task = state.get("current_task")
    if not task:
        # Pick next task
        for t in TASK_TEMPLATES:
            if t not in state.get("completed_tasks", []):
                task = t
                break
        if not task:
            state["status"] = "complete"
            return state
    
    state["current_task"] = task
    state["iteration"] += 1
    
    # Self-question: what do we need to build this task?
    questions = generate_questions(task, state)
    
    # Try to answer each question
    blocked = []
    answered = []
    
    for q in questions:
        # Check Knowledge Brain first (source doctrine)
        knowledge_hit = knowledge_brain_search(q, top_k=2)
        if knowledge_hit:
            answered.append({"question": q, "source": "knowledge_brain", "answer": knowledge_hit[:300]})
            continue
        
        # Check AI Brain second (ingested content)
        ai_hit = ai_brain_search(q, limit=3)
        if ai_hit:
            answered.append({"question": q, "source": "ai_brain", "answer": ai_hit[:300]})
            continue
        
        # Check web last
        web_hit = web_search(f"{state['vertical']} {q}")
        if web_hit:
            answered.append({"question": q, "source": "web", "answer": web_hit[:300]})
            continue
        
        # Blocked on user
        blocked.append(q)
    
    # If not blocked, build the task
    if not blocked:
        build_task_output(state, task, answered)
        state["completed_tasks"].append(task)
        state["current_task"] = None
    else:
        state["blocked_on_user"] = blocked
        state["status"] = "blocked_on_user"
    
    save_company_state(state)
    return state


def generate_questions(task: str, state: dict) -> list[str]:
    """Generate self-questions for a QLA task based on Peña's principles."""
    v = state["vertical"]
    
    # QLA-specific questions for each phase
    qla_questions = {
        "00_MISSION_VISION": [
            f"What is the QLA mission for a {v} business using Peña's 'masterful illusion'?",
            f"What does 'Expectations of Super Success' look like for {v}?",
            f"What is your Pay-Price-to-Action for achieving dominance in {v}?",
            f"How do you commit publicly to the {v} project (Peña's D6 principle)?",
        ],
        "01_MINDSET_CONDITIONING": [
            f"How do you expand comfort zone boundaries in {v} (Peña's M20, M21)?",
            f"What does 'simulation' look like for {v} decisions (Peña's M21)?",
            f"How do you 'double your failure rate' in {v} (Peña's M11)?",
            f"What conventional wisdom must you reject in {v} (Peña's M9)?",
        ],
        "02_PERCEPTION_MANAGEMENT": [
            f"How do you build 'masterful illusion' for {v} (Peña's M35)?",
            f"What image projects premium value in {v}?",
            f"How does 'structure follows strategy' apply to {v} (Peña's M30)?",
            f"What perception must exist before the substance in {v}?",
        ],
        "03_STRATEGY_CONSOLIDATION": [
            f"Which fragmented industries in {v} have mom-and-pops with 20-40% margins (Peña's D15)?",
            f"What is the quantum growth thesis for {v} (Peña's D11)?",
            f"How do you 'stick to your knitting' in {v} (Peña's D13)?",
            f"What second acquisition complements the first in {v} (Peña's D20)?",
        ],
        "04_DEAL_FLOW": [
            f"What are the 11 steps for sourcing {v} deals (Peña's D2)?",
            f"How do you investigate before investing in {v} (Peña's M32)?",
            f"What red flags must you screen for in {v} targets (Peña's D4)?",
            f"How do you maintain a pipeline of 50+ {v} targets?",
        ],
        "05_NEGOTIATION_BANKING": [
            f"How do you map the other party's comfort zone in {v} negotiations?",
            f"What is your Pay-Price-to-Action for {v} deals (Peña's D8)?",
            f"How do you romance bankers for {v} financing?",
            f"What seller financing structures work for {v}?",
        ],
        "06_CAPITAL_STACK": [
            f"How do you structure 80%+ OPM for {v} acquisitions?",
            f"What lender relationships do you need for {v}?",
            f"How do you avoid using operating funds for equity in {v} (Peña's D19)?",
            f"What is the optimal capital stack for {v}?",
        ],
        "07_DREAM_TEAM": [
            f"Who should be on your Board of Directors for {v}?",
            f"How do you apply the Doofus Test to {v} hires (Peña's Appendix B)?",
            f"What equity participation structure attracts {v} talent?",
            f"Who are your trusted outside advisors for {v}?",
        ],
        "08_OPERATIONS_EXCELLENCE": [
            f"How do you implement the 21-hour rule in {v} (Peña's E principles)?",
            f"What does 'no Plan B' mentality look like for {v}?",
            f"How do you create order from {v} chaos?",
            f"What daily war room metrics matter for {v}?",
        ],
        "09_RESEARCH_INTELLIGENCE": [
            f"What intelligence do you need on 3-5 {v} target industries?",
            f"How do you track hiring activity and expansion signals in {v}?",
            f"What competitive intelligence matters for {v}?",
            f"How do you maintain target lists of 50+ {v} candidates?",
        ],
        "10_EXIT_VALUATION": [
            f"How do you design exit strategy from Day 1 for {v}?",
            f"What perception of value must you build for {v}?",
            f"What EBITDA multiple target for {v} consolidation plays?",
            f"How do you time the market for {v} exit?",
        ],
        "11_PENA_ISMS_LIBRARY": [
            f"Which Peña-isms apply most to {v}?",
            f"How do you integrate Peña-isms into {v} decision-making?",
            f"What are the top 10 Peña-isms for your {v} business?",
        ],
        "12_AGENT_TECH": [
            f"What QLA-specific agent contracts do you need for {v}?",
            f"How do you configure Knowledge Brain search for {v} decisions?",
            f"What exception layer rules apply to {v} operations?",
        ],
    }
    
    return qla_questions.get(task, [f"What is needed for {task} in {v}?"])


def build_task_output(state: dict, task: str, research: list[dict]) -> None:
    """Write task output to the company folder."""
    root = Path(state["output_root"])
    task_dir = root / task
    task_dir.mkdir(parents=True, exist_ok=True)
    
    # Combine research into a task document
    lines = [
        f"# {task} — {state['company']}",
        "",
        f"Vertical: {state['vertical']}",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Research & Citations",
        "",
    ]
    for r in research:
        lines.append(f"### Question: {r['question']}")
        lines.append(f"**Source:** {r['source']}")
        lines.append(r['answer'][:400])
        lines.append("")
    
    (task_dir / f"task_{task.lower().replace(' ', '_')}.md").write_text("\n".join(lines))
    (task_dir / "research.json").write_text(json.dumps(research, indent=2))


def build_company_scaffold(company_path: Path, vertical: str, company: str) -> None:
    """Build the QLA-structured company scaffold."""
    from modules.qla_scaffold import build_qla_scaffold
    build_qla_scaffold(company_path, vertical, company)


def run_executive_loop(company: str | None = None, max_iterations: int = 15) -> dict:
    """Run the executive loop until complete, blocked, or max iterations."""
    state = load_company_state(company) if company else None
    if not state:
        return {"error": f"No company state found for {company}"}
    
    while state["status"] == "building" and state["iteration"] < max_iterations:
        state = executive_iteration(state)
        if state["status"] == "blocked_on_user":
            break
    
    # Update dashboard
    all_states = load_all_states()
    save_dashboard(all_states)
    
    return state


def load_all_states() -> list[dict]:
    """Load all company states."""
    states = []
    if COMPANIES_ROOT.exists():
        for d in COMPANIES_ROOT.iterdir():
            if d.is_dir():
                s = d / "state.json"
                if s.exists():
                    states.append(json.loads(s.read_text()))
    return states
