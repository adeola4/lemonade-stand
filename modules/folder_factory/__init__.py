"""
Folder Factory — Superpowers-Native QLA Deal System Generator
Generates complete multi-agent deal automation using obra/superpowers skills.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

COMPANIES_ROOT = Path.home() / "tan-executive" / "companies"

# QLA Math Gates
QLA_GATES = {
    "DSCR_MINIMUM": 1.50,
    "ENTRY_MULTIPLE_MIN": 2.0,
    "ENTRY_MULTIPLE_MAX": 5.0,
    "PROFIT_SPLIT_TAN": 0.60,
    "PROFIT_SPLIT_SELLER": 0.40,
    "SELLER_NOTE_MAX": 0.90,
    "CASH_REQUIREMENT": 0.10,
}

# Superpowers skills to reference in generated agents
SUPERPOWERS_SKILLS = [
    "superpowers:test-driven-development",
    "superpowers:systematic-debugging",
    "superpowers:verification-before-completion",
    "superpowers:requesting-code-review",
    "superpowers:writing-plans",
    "superpowers:executing-plans",
    "superpowers:subagent-driven-development",
    "superpowers:brainstorming",
    "superpowers:dispatching-parallel-agents",
]


def parse_business_doc(doc_text: str) -> dict:
    """Parse any business doc into QLA-enriched model."""
    extracted = {
        "company": _extract_company_name(doc_text),
        "vertical": _extract_vertical(doc_text),
        "geo": _extract_geo(doc_text),
        "idea": _extract_idea(doc_text),
        "revenue": _extract_metric(doc_text, ["revenue", "rev", "sales", "turnover"]),
        "cash_flow": _extract_metric(doc_text, ["cash flow", "ebitda", "sde", "profit"]),
        "asking_price": _extract_metric(doc_text, ["asking", "price", "valuation", "value"]),
        "employees": _extract_metric(doc_text, ["employees", "staff", "headcount"]),
    }
    
    extracted["qla_phase_mapping"] = _map_to_qla_phases(extracted)
    extracted["deal_structure"] = _suggest_deal_structure(extracted)
    extracted["human_handoff_triggers"] = _determine_handoffs(extracted)
    extracted["knowledge_brain_items"] = _find_kb_references(extracted)
    extracted["superpowers_skills"] = SUPERPOWERS_SKILLS
    extracted["parsed_at"] = datetime.now(timezone.utc).isoformat()
    
    return extracted


def generate_folder(parsed: dict, output_root: Path) -> dict:
    """Generate complete superpowers-native deal system using subagent-driven development."""
    
    company = parsed.get("company", "NewVenture")
    slug = company.lower().replace(" ", "-").replace("/", "-")[:40]
    folder = output_root / slug
    
    # Create QLA 13-phase scaffold
    _create_qla_folders(folder, parsed)
    
    # Generate agents using superpowers subagent-driven-development pattern
    agents = ["deal_sourcing", "deal_scorer", "dd_checker", "offer_generator", "closer", "capital_calculator"]
    for agent_name in agents:
        _generate_agent(folder, agent_name, parsed)
    
    # Generate orchestration (LangGraph with superpowers verification)
    _generate_orchestration(folder, parsed)
    
    # Generate human handoff (superpowers systematic-debugging for failures)
    _generate_handoff(folder, parsed)
    
    # Generate integrations
    _generate_integrations(folder, parsed)
    
    # Generate superpowers config
    _generate_superpowers_config(folder, parsed)
    
    # Save business model
    (folder / "business_model.json").write_text(json.dumps(parsed, indent=2))
    
    return {
        "company": company,
        "folder": str(folder),
        "agents": len(agents),
        "qla_phases": len(parsed.get("qla_phase_mapping", [])),
        "deal_structure": parsed.get("deal_structure"),
        "human_handoffs": len(parsed.get("human_handoff_triggers", [])),
        "superpowers": True,
    }


def _generate_superpowers_config(folder: Path, parsed: dict):
    """Generate .superpowers/config.yaml for the generated system."""
    sp_dir = folder / ".superpowers"
    sp_dir.mkdir(parents=True, exist_ok=True)
    
    config = {
        "version": "1.0",
        "methodology": "subagent-driven-development",
        "qla_enabled": True,
        "skills": {
            "auto_trigger": {
                "superpowers:test-driven-development": "When writing agent code or tests",
                "superpowers:systematic-debugging": "When agent fails or produces errors",
                "superpowers:verification-before-completion": "Before marking any task complete",
                "superpowers:brainstorming": "When strategy or approach is unclear",
                "superpowers:subagent-driven-development": "When executing multi-step plans",
            }
        },
        "math_gates": QLA_GATES,
        "deal_structure": parsed.get("deal_structure"),
        "human_handoffs": parsed.get("human_handoff_triggers", []),
    }
    
    (sp_dir / "config.yaml").write_text(json.dumps(config, indent=2))


def _create_qla_folders(folder: Path, parsed: dict):
    """Create QLA 13-phase folder structure."""
    from modules.qla_framework import all_qla_folders
    
    for qla_folder in all_qla_folders():
        folder_path = folder / f"{qla_folder.number}_{qla_folder.name}"
        folder_path.mkdir(parents=True, exist_ok=True)
        
        readme = f"# {qla_folder.name}\n\n"
        readme += f"**QLA Phase:** {qla_folder.qla_phase}\n\n"
        readme += f"{qla_folder.description}\n\n"
        readme += f"## Core Actions\n\n"
        for action in qla_folder.core_actions:
            readme += f"- [ ] {action}\n"
        (folder_path / "README.md").write_text(readme)


def _generate_agent(folder: Path, agent_name: str, parsed: dict):
    """Generate a single agent with superpowers skills baked in."""
    agent_dir = folder / "agents" / agent_name
    agent_dir.mkdir(parents=True, exist_ok=True)
    
    (agent_dir / "agent.py").write_text(_agent_py(agent_name))
    (agent_dir / "prompts.py").write_text(_get_agent_prompts(agent_name, parsed))
    (agent_dir / "tools.py").write_text(_tools_py(agent_name))
    (agent_dir / "schemas.py").write_text(_schemas_py(agent_name))


def _generate_orchestration(folder: Path, parsed: dict):
    """Generate LangGraph orchestration with superpowers verification."""
    orch_dir = folder / "orchestration"
    orch_dir.mkdir(parents=True, exist_ok=True)
    
    (orch_dir / "state.py").write_text(_state_py(parsed))
    (orch_dir / "graph.py").write_text(_graph_py(parsed))
    (orch_dir / "conditions.py").write_text(_conditions_py())
    (orch_dir / "handoff.py").write_text(_handoff_py(parsed))


def _generate_handoff(folder: Path, parsed: dict):
    """Generate human handoff framework."""
    handoff_dir = folder / "human_handoff"
    handoff_dir.mkdir(parents=True, exist_ok=True)
    
    (handoff_dir / "queue.py").write_text(_queue_py())
    (handoff_dir / "notifier.py").write_text(_notifier_py())
    (handoff_dir / "escalation.py").write_text(_escalation_py(parsed))


def _generate_integrations(folder: Path, parsed: dict):
    """Generate integration stubs."""
    integ_dir = folder / "integrations"
    integ_dir.mkdir(parents=True, exist_ok=True)
    
    (integ_dir / "sheets.py").write_text(_sheets_py())
    (integ_dir / "drive.py").write_text(_drive_py())


# ── Extraction Helpers ───────────────────────────────────────

def _extract_company_name(text: str) -> str:
    """Extract company name from business doc."""
    text = text.strip()
    match = re.search(r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4})\s+(?:is|was|are)\s", text, re.MULTILINE)
    if match:
        return match.group(1).strip()[:60]
    match = re.search(r"(?:company|business)\s*:\s*([A-Z][A-Za-z\s&]+)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()[:60]
    return "NewVenture"


def _extract_vertical(text: str) -> str:
    verticals = ["healthcare", "home health", "plumbing", "HVAC", "SaaS", "real estate", "marine", "agriculture", "energy", "construction"]
    for v in verticals:
        if v.lower() in text.lower():
            return v
    return "general"


def _extract_geo(text: str) -> str:
    match = re.search(r"(?:in|across|throughout)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", text)
    return match.group(1) if match else "US"


def _extract_idea(text: str) -> str:
    return text[:200]


def _extract_metric(text: str, keywords: list) -> float | None:
    for kw in keywords:
        match = re.search(rf"{kw}[\s:]*[\$]?([\d,]+(?:\.\d+)?[KkMm]?)", text, re.IGNORECASE)
        if match:
            val = match.group(1).replace(",", "").replace("K", "000").replace("M", "000000")
            try:
                return float(val)
            except:
                pass
    return None


def _map_to_qla_phases(extracted: dict) -> list:
    phases = []
    if extracted.get("company"):
        phases.append("00_MISSION_VISION")
    if extracted.get("vertical"):
        phases.append("03_STRATEGY_CONSOLIDATION")
    if extracted.get("cash_flow"):
        phases.append("04_DEAL_FLOW")
    if extracted.get("asking_price"):
        phases.append("06_CAPITAL_STACK")
    return phases


def _suggest_deal_structure(extracted: dict) -> str:
    cash_flow = extracted.get("cash_flow") or 0
    asking = extracted.get("asking_price") or 0
    if cash_flow > 0 and asking > 0:
        multiple = asking / cash_flow
        if multiple <= 3.0:
            return "qla_classic"
        elif multiple <= 5.0:
            return "earnout_heavy"
    return "sba_seller"


def _determine_handoffs(extracted: dict) -> list:
    triggers = []
    asking = extracted.get("asking_price") or 0
    if asking > 100000:
        triggers.append(f"Deal value ${asking:,.0f} exceeds $100k threshold - human approval required")
    if extracted.get("cash_flow") and extracted.get("asking_price"):
        multiple = extracted["asking_price"] / extracted["cash_flow"]
        if multiple > 4.0:
            triggers.append(f"Multiple {multiple:.1f}x exceeds 4.0x - human review required")
    triggers.append("Any legal compliance flag requires immediate human takeover")
    triggers.append("Financial discrepancy > 20% requires human investigation")
    return triggers


def _find_kb_references(extracted: dict) -> list:
    try:
        from modules.knowledge_brain import search_knowledge_brain
        query = f"{extracted.get('vertical', '')} {extracted.get('deal_structure', '')} acquisition"
        return search_knowledge_brain(query, limit=5)
    except:
        return []


# ── Code Generators ──────────────────────────────────────────

def _agent_py(name: str) -> str:
    return (
        '"""' + name + ' agent — Superpowers-powered QLA execution."""\n'
        'from typing import TypedDict\n\n'
        'class State(TypedDict):\n'
        '    pass\n\n'
        'async def run(state: State) -> State:\n'
        '    """Execute ' + name + ' procedure per QLA methodology.\n\n'
        '    Uses superpowers skills:\n'
        '    - superpowers:test-driven-development for agent logic\n'
        '    - superpowers:systematic-debugging for error recovery\n'
        '    - superpowers:verification-before-completion for quality gates\n'
        '    """\n'
        '    return state\n'
    )


def _get_agent_prompts(name: str, parsed: dict) -> str:
    company = parsed.get("company", "TAN")
    vertical = parsed.get("vertical", "general")
    
    prompts = {
        "deal_sourcing": f"You are the Deal Sourcing Agent for {company}. Execute Peña's 11-step sourcing procedure. Use superpowers:brainstorming to identify target criteria. Output qualified leads.",
        "deal_scorer": f"You are the Deal Scoring Agent. Apply QLA 10-point scoring methodology. Use superpowers:test-driven-development to validate scoring logic. Be skeptical. No improvisation on partial data.",
        "dd_checker": f"You are the Due Diligence Agent. Be skeptical. Assume sellers are optimistic. Use superpowers:systematic-debugging to trace discrepancies. Cross-reference every claim.",
        "offer_generator": f"You are the Offer Generation Agent. Use QLA 6-structure model. Use superpowers:writing-plans before generating LOI. LOI must include QLA math gate: seller note = price - cash - OPM.",
        "closer": f"You are the Closing Agent. Track conditions precedent. Use superpowers:verification-before-completion before sending. Coordinate with legal counsel.",
        "capital_calculator": f"You are the Capital Stack Agent. OPM first. DSCR minimum 1.50x. Entry multiple 2.0-5.0x EBITDA. 60/40 profit split. Use superpowers:test-driven-development to validate calculations.",
    }
    
    prompt_text = prompts.get(name, "Execute QLA procedure.")
    
    return (
        '"""' + name + ' prompts — Superpowers-powered QLA."""\n'
        'SYSTEM_PROMPT = """' + prompt_text + '"""\n\n'
        '# Superpowers skills this agent uses\n'
        'SUPERPOWERS = [\n'
        '    "superpowers:test-driven-development",\n'
        '    "superpowers:systematic-debugging",\n'
        '    "superpowers:verification-before-completion",\n'
        ']\n'
    )


def _tools_py(name: str) -> str:
    return f'"""{name} tools."""\n# Tool bindings for {name}\n'


def _schemas_py(name: str) -> str:
    class_name = name.title().replace("_", "")
    return (
        '"""' + name + ' schemas."""\n'
        'from pydantic import BaseModel\n\n'
        f'class {class_name}Input(BaseModel):\n'
        '    pass\n\n'
        f'class {class_name}Output(BaseModel):\n'
        '    pass\n'
    )


def _state_py(parsed: dict) -> str:
    company = parsed.get("company", "company")
    return (
        '"""QLA State for ' + company + '."""\n'
        'from typing import TypedDict, List, Optional\n\n'
        'class DealState(TypedDict):\n'
        '    company: str\n'
        '    vertical: str\n'
        '    geo: str\n'
        '    idea: str\n'
        '    phase: str\n'
        '    leads: List[dict]\n'
        '    score: Optional[float]\n'
        '    dd_report: Optional[dict]\n'
        '    offer: Optional[dict]\n'
        '    loi: Optional[str]\n'
        '    human_approvals: List[dict]\n'
        '    errors: List[str]\n'
        '    superpowers_mode: str  # "subagent-driven-development" | "executing-plans"\n'
    )


def _graph_py(parsed: dict) -> str:
    company = parsed.get("company", "company")
    return (
        '"""LangGraph for ' + company + ' — Superpowers-powered."""\n'
        'from langgraph.graph import StateGraph, END\n'
        'from langgraph.checkpoint.memory import MemorySaver\n\n'
        'def build_graph():\n'
        '    workflow = StateGraph(DealState)\n\n'
        '    workflow.add_node("source", source_leads)\n'
        '    workflow.add_node("score", score_deals)\n'
        '    workflow.add_node("select", select_deal)\n'
        '    workflow.add_node("dd", run_dd)\n'
        '    workflow.add_node("offer", generate_offer)\n'
        '    workflow.add_node("loi", generate_loi)\n'
        '    workflow.add_node("verify", verify_with_superpowers)\n\n'
        '    workflow.set_entry_point("source")\n'
        '    workflow.add_edge("source", "score")\n'
        '    workflow.add_edge("score", "select")\n'
        '    workflow.add_edge("select", "dd")\n'
        '    workflow.add_conditional_edges("dd", dd_pass, {"yes": "offer", "no": END})\n'
        '    workflow.add_conditional_edges("offer", needs_approval, {"yes": "loi", "no": "verify"})\n'
        '    workflow.add_edge("verify", END)\n\n'
        '    return workflow.compile(checkpointer=MemorySaver())\n\n'
        'async def verify_with_superpowers(state):\n'
        '    """Use superpowers:verification-before-completion."""\n'
        '    return state\n\n'
        'async def source_leads(state): pass\n'
        'async def score_deals(state): pass\n'
        'async def select_deal(state): pass\n'
        'async def run_dd(state): pass\n'
        'async def generate_offer(state): pass\n'
        'async def generate_loi(state): pass\n\n'
        'def dd_pass(state):\n'
        '    return "yes" if state.get("dd_score", 0) >= 70 else "no"\n\n'
        'def needs_approval(state):\n'
        '    return "no"\n'
    )


def _conditions_py() -> str:
    return (
        '"""QLA Math Gates — Hard Constraints (enforced by superpowers:TDD)."""\n'
        'DSCR_MINIMUM = 1.50\n'
        'ENTRY_MULTIPLE_MIN = 2.0\n'
        'ENTRY_MULTIPLE_MAX = 5.0\n'
        'PROFIT_SPLIT_TAN = 0.60\n'
        'PROFIT_SPLIT_SELLER = 0.40\n'
        'SELLER_NOTE_MAX = 0.90\n'
        'CASH_REQUIREMENT = 0.10\n\n'
        'def check_dscr(debt_service: float, cash_flow: float) -> bool:\n'
        '    return (cash_flow / debt_service) >= DSCR_MINIMUM if debt_service > 0 else False\n\n'
        'def check_multiple(price: float, ebitda: float) -> bool:\n'
        '    mult = price / ebitda if ebitda > 0 else 0\n'
        '    return ENTRY_MULTIPLE_MIN <= mult <= ENTRY_MULTIPLE_MAX\n'
    )


def _handoff_py(parsed: dict) -> str:
    company = parsed.get("company", "company")
    triggers = parsed.get("human_handoff_triggers", [])
    
    trigger_lines = ",\n    ".join(f'"{t}"' for t in triggers)
    
    return (
        '"""Human Handoff Logic for ' + company + '."""\n'
        '# Uses superpowers:systematic-debugging for failure diagnosis\n\n'
        'HANDOFF_TRIGGERS = [\n'
        f'    {trigger_lines}\n'
        ']\n\n'
        'def check_handoff(state: dict) -> tuple[bool, str]:\n'
        '    """Check if state requires human handoff."""\n'
        '    price = state.get("asking_price", 0)\n'
        '    if price > 100000:\n'
        '        return True, f"Deal value ${price:,.0f} exceeds $100k threshold"\n'
        '    if state.get("dd_discrepancy", 0) > 0.20:\n'
        '        return True, "Financial discrepancy > 20%"\n'
        '    if state.get("legal_flag"):\n'
        '        return True, "Legal compliance flag detected"\n'
        '    return False, ""\n'
    )


def _queue_py() -> str:
    return (
        '"""Approval Queue — SQLite-backed."""\n'
        'import sqlite3\n'
        'import json\n'
        'from datetime import datetime\n\n'
        'class ApprovalQueue:\n'
        '    def __init__(self, db_path="./state/approvals.db"):\n'
        '        self.conn = sqlite3.connect(db_path)\n'
        '        self.conn.execute("""CREATE TABLE IF NOT EXISTS approvals (\n'
        '            id INTEGER PRIMARY KEY, deal_id TEXT, deal_name TEXT,\n'
        '            valuation REAL, action_required TEXT, context_json TEXT,\n'
        '            status TEXT DEFAULT \'pending\', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,\n'
        '            resolved_at TIMESTAMP, resolution TEXT, resolved_by TEXT)""")\n\n'
        '    def add(self, deal_id, deal_name, valuation, action, context):\n'
        '        cur = self.conn.execute(\n'
        '            "INSERT INTO approvals (deal_id, deal_name, valuation, action_required, context_json) VALUES (?,?,?,?,?)",\n'
        '            (deal_id, deal_name, valuation, action, json.dumps(context)))\n'
        '        self.conn.commit()\n'
        '        return cur.lastrowid\n\n'
        '    def pending(self):\n'
        '        cur = self.conn.execute("SELECT * FROM approvals WHERE status=\'pending\'")\n'
        '        return [dict(zip([d[0] for d in cur.description], row)) for row in cur.fetchall()]\n\n'
        '    def resolve(self, approval_id, resolution, by="human"):\n'
        '        self.conn.execute(\n'
        '            "UPDATE approvals SET status=?, resolution=?, resolved_by=?, resolved_at=? WHERE id=?",\n'
        '            ("approved" if resolution=="approve" else "rejected", resolution, by, datetime.utcnow().isoformat(), approval_id))\n'
        '        self.conn.commit()\n'
    )


def _notifier_py() -> str:
    return (
        '"""Discord/Telegram notifier for handoffs."""\n'
        'import os, json\n\n'
        'def notify_discord(message: str, webhook_url: str = ""):\n'
        '    if not webhook_url:\n'
        '        webhook_url = os.environ.get("DISCORD_WEBHOOK_URL", "")\n'
        '    if webhook_url:\n'
        '        import urllib.request\n'
        '        data = json.dumps({"content": message}).encode()\n'
        '        req = urllib.request.Request(webhook_url, data=data, headers={"Content-Type": "application/json"})\n'
        '        urllib.request.urlopen(req, timeout=10)\n\n'
        'def notify_telegram(message: str, bot_token: str = "", chat_id: str = ""):\n'
        '    if not bot_token:\n'
        '        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")\n'
        '    if not chat_id:\n'
        '        chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")\n'
        '    if bot_token and chat_id:\n'
        '        import urllib.request\n'
        '        url = f"https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={chat_id}&text={message}"\n'
        '        urllib.request.urlopen(url, timeout=10)\n'
    )


def _escalation_py(parsed: dict) -> str:
    company = parsed.get("company", "company")
    return (
        '"""Escalation rules for ' + company + '."""\n\n'
        'ESCALATION_RULES = [\n'
        '    {"condition": "deal_value > 100000", "action": "notify_deal_lead"},\n'
        '    {"condition": "dd_discrepancy > 0.20", "action": "notify_cfo"},\n'
        '    {"condition": "legal_flag", "action": "notify_legal"},\n'
        '    {"condition": "negotiation_round > 2", "action": "escalate_to_ceo"},\n'
        ']\n'
    )


def _sheets_py() -> str:
    return (
        '"""Google Sheets integration."""\n'
        'import json, os\n'
        'from pathlib import Path\n\n'
        'TOKEN = Path.home() / ".hermes/google_token.json"\n\n'
        'def append_row(sheet_id: str, tab: str, row: list):\n'
        '    # Uses existing google_token.json\n'
        '    pass\n'
    )


def _drive_py() -> str:
    return (
        '"""Google Drive integration."""\n'
        'from pathlib import Path\n\n'
        'def upload_file(folder_id: str, file_path: str) -> str:\n'
        '    # Upload to Drive, return file ID\n'
        '    return "file_id_placeholder"\n'
    )
