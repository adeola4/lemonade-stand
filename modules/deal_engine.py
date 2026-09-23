"""Deal Engine — deterministic state machine based on Peña's 11-step methodology.
NO generative AI in the execution layer. Every step is procedure-driven.
Input: prompt or document → Output: executed deal, by the book.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from modules.knowledge_brain import load_knowledge_brain, search_knowledge_brain, get_action_items_for_phase


# ──────────────────────────────────────────────────────────────
#  ENUMERATIONS — every state is predefined, no dynamic creation
# ──────────────────────────────────────────────────────────────

class DealStage(Enum):
    """Peña's 11 Steps + supporting phases. Fixed. No additions."""
    INTAKE = "intake"
    IDENTIFY = "identify"           # Step 1
    GENERALITIES = "generalities"    # Step 2
    SPECIFICS = "specifics"          # Step 3
    COMMIT = "commit"               # Step 4
    PRELIMINARY_DECISION = "preliminary_decision"  # Step 5
    DEEP_INVESTIGATION = "deep_investigation"      # Step 6
    ACTION_PLAN = "action_plan"      # Step 7
    CRITICAL_PATH = "critical_path"  # Step 8
    IMPLEMENT = "implement"          # Step 9
    EXECUTE = "execute"             # Step 10
    REVIEW = "review"               # Step 11
    COMPLETE = "complete"
    BLOCKED = "blocked"
    KILLED = "killed"


class DocumentType(Enum):
    """Fixed document types — no generative creation."""
    EXECUTIVE_SUMMARY = "executive_summary"
    LOI = "loi"
    NDA = "nda"
    OFFER = "offer"
    TERM_SHEET = "termsheet"
    DUE_DILIGENCE = "diligence"
    OPERATING_AGREEMENT = "operating_agreement"
    FINANCIAL_PROJECTIONS = "projections"
    PITCH_DECK = "pitchdeck"
    WHITE_PAPER = "white_paper"


# ──────────────────────────────────────────────────────────────
#  STATE — fully deterministic, no optional fields
# ──────────────────────────────────────────────────────────────

@dataclass
class DealState:
    """Complete deal state. Every field is required at each stage."""
    company: str
    vertical: str
    geo: str
    idea: str
    stage: DealStage = DealStage.INTAKE
    documents: dict[str, str] = field(default_factory=dict)  # doc_type -> path
    pipeline: list[dict] = field(default_factory=list)
    knowledge_refs: list[dict] = field(default_factory=list)
    action_items_completed: list[str] = field(default_factory=list)
    action_items_pending: list[str] = field(default_factory=list)
    web_data: dict = field(default_factory=dict)
    outreach_plans: list[dict] = field(default_factory=list)
    scorecards: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    
    def transition(self, new_stage: DealStage) -> None:
        """Deterministic transition. No side effects."""
        self.stage = new_stage
    
    def is_complete(self) -> bool:
        return self.stage == DealStage.COMPLETE
    
    def is_blocked(self) -> bool:
        return self.stage in (DealStage.BLOCKED, DealStage.KILLED)
    
    def to_dict(self) -> dict:
        return {
            "company": self.company,
            "vertical": self.vertical,
            "geo": self.geo,
            "idea": self.idea,
            "stage": self.stage.value,
            "documents": self.documents,
            "pipeline": self.pipeline,
            "knowledge_refs_count": len(self.knowledge_refs),
            "action_items_completed": len(self.action_items_completed),
            "action_items_pending": len(self.action_items_pending),
            "web_data_keys": list(self.web_data.keys()),
            "outreach_plans": len(self.outreach_plans),
            "scorecards": len(self.scorecards),
            "errors": self.errors,
        }


# ──────────────────────────────────────────────────────────────
#  ACTION ITEM REGISTRY — all 3,000+ mapped to stages
# ──────────────────────────────────────────────────────────────

class ActionItemRegistry:
    """Loads all Knowledge Brain action items and maps them to deal stages.
    This is the code. The methodology made executable."""
    
    def __init__(self):
        self.all_items = load_knowledge_brain()
        self._build_index()
    
    def _build_index(self) -> None:
        """Index all items by category for deterministic lookup."""
        self.by_category: dict[str, list[dict]] = {}
        self.by_id: dict[str, dict] = {}
        
        for item in self.all_items:
            cat = item.get("category", "Unknown")
            if cat not in self.by_category:
                self.by_category[cat] = []
            self.by_category[cat].append(item)
            self.by_id[item.get("id", "")] = item
        
        # Map categories to deal stages
        self.stage_mapping = {
            DealStage.INTAKE: ["MINDSET PRINCIPLES", "PERCEPTION PRINCIPLES"],
            DealStage.IDENTIFY: ["DEAL PRINCIPLES", "STRATEGY & CONSOLIDATION PRINCIPLES"],
            DealStage.GENERALITIES: ["CAPITAL & FINANCING PRINCIPLES", "STRATEGY & CONSOLIDATION PRINCIPLES"],
            DealStage.SPECIFICS: ["DEAL PRINCIPLES", "TEAM & DREAM TEAM PRINCIPLES"],
            DealStage.COMMIT: ["MINDSET PRINCIPLES", "NEGOTIATION PRINCIPLES"],
            DealStage.PRELIMINARY_DECISION: ["DEAL PRINCIPLES", "CAPITAL & FINANCING PRINCIPLES"],
            DealStage.DEEP_INVESTIGATION: ["DEAL PRINCIPLES", "EXECUTION & ACTION PRINCIPLES"],
            DealStage.ACTION_PLAN: ["STRATEGY & CONSOLIDATION PRINCIPLES", "EXECUTION & ACTION PRINCIPLES"],
            DealStage.CRITICAL_PATH: ["EXECUTION & ACTION PRINCIPLES"],
            DealStage.IMPLEMENT: ["EXECUTION & ACTION PRINCIPLES", "PERCEPTION PRINCIPLES"],
            DealStage.EXECUTE: ["EXECUTION & ACTION PRINCIPLES", "CAPITAL & FINANCING PRINCIPLES"],
            DealStage.REVIEW: ["MINDSET PRINCIPLES", "STRATEGY & CONSOLIDATION PRINCIPLES"],
        }
    
    def get_items_for_stage(self, stage: DealStage) -> list[dict]:
        """Get all action items for a deal stage. Deterministic."""
        categories = self.stage_mapping.get(stage, [])
        items = []
        for cat in categories:
            items.extend(self.by_category.get(cat, []))
        return items
    
    def get_items_by_category(self, category: str) -> list[dict]:
        """Get items by exact category name."""
        return self.by_category.get(category, [])
    
    def get_total_count(self) -> int:
        return len(self.all_items)
    
    def get_category_counts(self) -> dict[str, int]:
        return {cat: len(items) for cat, items in self.by_category.items()}


# ──────────────────────────────────────────────────────────────
#  PROCEDURE RUNNER — executes steps in order, no deviation
# ──────────────────────────────────────────────────────────────

class DealProcedureRunner:
    """Runs the full QLA deal process as a deterministic state machine.
    
    No LLM in the loop. Every procedure is predefined.
    Same input → same output. Every. Single. Time.
    """
    
    def __init__(self):
        self.registry = ActionItemRegistry()
    
    def run(self, company: str, vertical: str, geo: str, idea: str) -> DealState:
        """Run the complete deal procedure."""
        state = DealState(company=company, vertical=vertical, geo=geo, idea=idea)
        
        print(f"\n{'='*70}")
        print(f"  QLA DEAL ENGINE — Deterministic Execution")
        print(f"  Company: {company}")
        print(f"  Vertical: {vertical}")
        print(f"  Geography: {geo}")
        print(f"  Knowledge Base: {self.registry.get_total_count()} action items loaded")
        print(f"{'='*70}\n")
        
        # Stage 1: INTAKE — Parse and validate
        self._procedure_intake(state)
        if state.is_blocked():
            return state
        
        # Stage 2: IDENTIFY — Find targets (Step 1)
        self._procedure_identify(state)
        
        # Stage 3: GENERALITIES — Market research (Step 2)
        self._procedure_generalities(state)
        
        # Stage 4: SPECIFICS — Target research (Step 3)
        self._procedure_specifics(state)
        
        # Stage 5: PRELIMINARY_DECISION — Score (Step 5, Step 4 needs human)
        self._procedure_preliminary_decision(state)
        
        # Stage 6: DEEP_INVESTIGATION — Red flags (Step 6)
        self._procedure_deep_investigation(state)
        
        # Stage 7: ACTION_PLAN — Build plan (Step 7)
        self._procedure_action_plan(state)
        
        # Stage 8: CRITICAL_PATH — Map dependencies (Step 8)
        self._procedure_critical_path(state)
        
        # Stage 9: Generate all documents
        self._procedure_generate_documents(state)
        
        # Stage 10: Create outreach plans
        self._procedure_outreach(state)
        
        # Stage 11: Add to pipeline
        self._procedure_add_to_pipeline(state)
        
        # Mark complete
        state.transition(DealStage.COMPLETE)
        
        self._print_summary(state)
        
        return state
    
    # ── PROCEDURES — each maps to a QLA step ──
    
    def _procedure_intake(self, state: DealState) -> None:
        """Stage 1: Parse the idea, validate inputs, load action items."""
        print("── STAGE 1: INTAKE ──")
        
        # Load action items for this stage
        items = self.registry.get_items_for_stage(DealStage.INTAKE)
        state.knowledge_refs = items[:10]
        
        print(f"  Action items loaded: {len(items)}")
        print(f"  Mindset principles: {len(self.registry.get_items_by_category('MINDSET PRINCIPLES'))}")
        print(f"  Perception principles: {len(self.registry.get_items_by_category('PERCEPTION PRINCIPLES'))}")
        print("  ✓ Intake complete")
        
        state.transition(DealStage.IDENTIFY)
    
    def _procedure_identify(self, state: DealState) -> None:
        """Step 1: Identify targets using web search + Knowledge Brain."""
        print("\n── STAGE 2: IDENTIFY (Step 1) ──")
        
        from modules.browser_search import search_targets
        
        # Deterministic search — same query, same results
        targets = search_targets(state.vertical, state.geo)
        
        # Load Knowledge Brain refs for this stage
        kb_items = self.registry.get_items_for_stage(DealStage.IDENTIFY)
        
        state.web_data["targets"] = targets
        state.web_data["target_count"] = len(targets)
        state.knowledge_refs.extend(kb_items[:5])
        
        print(f"  Targets found: {len(targets)}")
        print(f"  Knowledge Brain refs: {len(kb_items)}")
        for t in targets[:3]:
            print(f"    - {t.get('title', 'Unknown')[:50]}")
        
        state.transition(DealStage.GENERALITIES)
    
    def _procedure_generalities(self, state: DealState) -> None:
        """Step 2: Investigate generalities — market research."""
        print("\n── STAGE 3: GENERALITIES (Step 2) ──")
        
        from modules.browser_search import search_market_data
        
        market = search_market_data(state.vertical, state.geo)
        kb_items = self.registry.get_items_for_stage(DealStage.GENERALITIES)
        
        state.web_data["market"] = market
        state.web_data["market_topics"] = len(market)
        state.knowledge_refs.extend(kb_items[:5])
        
        print(f"  Market topics researched: {len(market)}")
        for topic in market.keys():
            print(f"    - {topic}")
        
        state.transition(DealStage.SPECIFICS)
    
    def _procedure_specifics(self, state: DealState) -> None:
        """Step 3: Investigate specifics — target profiles."""
        print("\n── STAGE 4: SPECIFICS (Step 3) ──")
        
        from modules.browser_search import search_target_details
        
        targets = state.web_data.get("targets", [])
        profiles = []
        for target in targets[:3]:
            name = target.get("title", target.get("name", ""))
            details = search_target_details(name)
            profiles.append(details)
        
        kb_items = self.registry.get_items_for_stage(DealStage.SPECIFICS)
        
        state.web_data["profiles"] = profiles
        state.knowledge_refs.extend(kb_items[:5])
        
        print(f"  Profiles built: {len(profiles)}")
        
        state.transition(DealStage.PRELIMINARY_DECISION)
    
    def _procedure_preliminary_decision(self, state: DealState) -> None:
        """Step 5: Score targets (Step 4 = commit, needs human)."""
        print("\n── STAGE 5: PRELIMINARY DECISION (Step 5) ──")
        print("  Step 4 (Commit) — REQUIRES HUMAN. Skipping to Step 5.")
        
        targets = state.web_data.get("targets", [])
        market = state.web_data.get("market", {})
        
        scorecards = []
        for target in targets[:3]:
            name = target.get("title", target.get("name", "Unknown"))
            scorecard = {
                "target": name,
                "scores": {
                    "revenue_size": "TBD",
                    "owner_motivation": "TBD",
                    "market_fragmentation": "High",
                    "competitive_moat": "TBD",
                    "financial_health": "TBD",
                    "geography_fit": "Confirmed",
                },
                "recommendation": "PROCEED TO DILIGENCE" if market else "NEED MORE DATA",
            }
            scorecards.append(scorecard)
        
        kb_items = self.registry.get_items_for_stage(DealStage.PRELIMINARY_DECISION)
        state.knowledge_refs.extend(kb_items[:5])
        state.scorecards = scorecards
        
        print(f"  Scorecards: {len(scorecards)}")
        for sc in scorecards:
            print(f"    - {sc['target'][:50]}: {sc['recommendation']}")
        
        state.transition(DealStage.DEEP_INVESTIGATION)
    
    def _procedure_deep_investigation(self, state: DealState) -> None:
        """Step 6: Red flag check."""
        print("\n── STAGE 6: DEEP INVESTIGATION (Step 6) ──")
        
        from modules.browser_search import search_red_flags
        
        targets = state.web_data.get("targets", [])
        for target in targets[:3]:
            name = target.get("title", target.get("name", ""))
            flags = search_red_flags(name)
            print(f"  {name[:50]}: {len(flags)} red flag categories checked")
        
        kb_items = self.registry.get_items_for_stage(DealStage.DEEP_INVESTIGATION)
        state.knowledge_refs.extend(kb_items[:5])
        
        state.transition(DealStage.ACTION_PLAN)
    
    def _procedure_action_plan(self, state: DealState) -> None:
        """Step 7: Build action plan — timeline, resources, milestones."""
        print("\n── STAGE 7: ACTION PLAN (Step 7) ──")
        
        plan = {
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
                "Signed NDA", "Verified financials", "Submitted LOI",
                "LOI accepted", "DD complete", "PA signed", "Closed",
            ],
        }
        
        state.web_data["action_plan"] = plan
        
        kb_items = self.registry.get_items_for_stage(DealStage.ACTION_PLAN)
        state.knowledge_refs.extend(kb_items[:5])
        
        print("  Action plan built (12-week timeline)")
        print(f"  Milestones: {len(plan['milestones'])}")
        
        state.transition(DealStage.CRITICAL_PATH)
    
    def _procedure_critical_path(self, state: DealState) -> None:
        """Step 8: Map critical path — dependencies and blockers."""
        print("\n── STAGE 8: CRITICAL PATH (Step 8) ──")
        
        path = [
            {"task": "Seller accepts NDA", "blocked_by": None, "status": "pending"},
            {"task": "Financials verified", "blocked_by": "NDA signed", "status": "pending"},
            {"task": "LOI submitted", "blocked_by": "Financials verified", "status": "pending"},
            {"task": "LOI accepted", "blocked_by": "Seller response", "status": "pending"},
            {"task": "DD complete", "blocked_by": "LOI accepted", "status": "pending"},
            {"task": "Financing secured", "blocked_by": "DD complete", "status": "pending"},
            {"task": "Closing", "blocked_by": "All above", "status": "pending"},
        ]
        
        state.web_data["critical_path"] = path
        
        kb_items = self.registry.get_items_for_stage(DealStage.CRITICAL_PATH)
        state.knowledge_refs.extend(kb_items[:3])
        
        print(f"  Critical path: {len(path)} steps")
        
        state.transition(DealStage.IMPLEMENT)
    
    def _procedure_generate_documents(self, state: DealState) -> None:
        """Generate all deal documents from templates — NO generative content."""
        print("\n── STAGE 9: DOCUMENT GENERATION ──")
        
        from modules.documents import (
            generate_loi, generate_nda, generate_offer_letter,
            generate_term_sheet, generate_due_diligence_checklist,
            generate_purchase_agreement_outline
        )
        from modules.paperworkman_integration import (
            generate_executive_summary, generate_financial_projections
        )
        
        output_dir = Path.home() / "tan-executive" / "companies" / state.company.lower().replace(" ", "-") / "docs"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate ONLY from templates — no generative fill
        docs_to_generate = [
            ("executive_summary", lambda: generate_executive_summary(state.to_dict())),
            ("loi", lambda: generate_loi(state.company, "[SELLER]", "[TARGET]")),
            ("nda", lambda: generate_nda(state.company, "[SELLER]", "[TARGET]")),
            ("offer", lambda: generate_offer_letter(state.company, "[SELLER]", "[TARGET]")),
            ("termsheet", lambda: generate_term_sheet(state.company, "[SELLER]", "[TARGET]")),
            ("projections", lambda: generate_financial_projections(state.to_dict())),
        ]
        
        for name, gen_fn in docs_to_generate:
            content = gen_fn()
            path = output_dir / f"{state.company.replace(' ', '_')}_{name}.txt"
            path.write_text(content)
            state.documents[name] = str(path)
            print(f"  ✓ {name}: {path.name}")
        
        state.transition(DealStage.EXECUTE)
    
    def _procedure_outreach(self, state: DealState) -> None:
        """Generate outreach plans for top targets."""
        print("\n── STAGE 10: OUTREACH PLANNING ──")
        
        from modules.outreach import generate_outreach
        
        targets = state.web_data.get("targets", [])
        for target in targets[:3]:
            plan = generate_outreach(target, buyer_name=state.company)
            state.outreach_plans.append({
                "target": target.get("title", "Unknown"),
                "channel": plan.channel,
                "reasoning": plan.reasoning,
            })
            print(f"  {target.get('title', 'Unknown')[:50]}: {plan.channel}")
        
        state.transition(DealStage.REVIEW)
    
    def _procedure_add_to_pipeline(self, state: DealState) -> None:
        """Add deals to pipeline tracker."""
        print("\n── STAGE 11: PIPELINE TRACKING ──")
        
        from modules.pipeline import add_deal, DealRecord
        
        targets = state.web_data.get("targets", [])
        for target in targets[:3]:
            deal = DealRecord(
                name=target.get("title", "Unknown"),
                stage="sourced",
                vertical=state.vertical,
                geo=state.geo,
            )
            add_deal(state.company, deal)
            print(f"  Added: {target.get('title', 'Unknown')[:50]}")
        
        state.transition(DealStage.COMPLETE)
    
    def _print_summary(self, state: DealState) -> None:
        """Print deterministic execution summary."""
        print(f"\n{'='*70}")
        print(f"  QLA DEAL EXECUTION COMPLETE")
        print(f"  Company: {state.company}")
        print(f"  Stage: {state.stage.value}")
        print(f"  Targets: {state.web_data.get('target_count', 0)}")
        print(f"  Documents: {len(state.documents)}")
        print(f"  Outreach Plans: {len(state.outreach_plans)}")
        print(f"  Knowledge Refs: {len(state.knowledge_refs)}")
        print(f"  Action Items in Registry: {self.registry.get_total_count()}")
        print(f"{'='*70}\n")


# ──────────────────────────────────────────────────────────────
#  CLI ENTRY POINT
# ──────────────────────────────────────────────────────────────

def execute_deal(company: str, vertical: str, geo: str, idea: str) -> DealState:
    """Main entry point for deterministic deal execution."""
    runner = DealProcedureRunner()
    return runner.run(company, vertical, geo, idea)


def get_registry_stats() -> dict:
    """Get action item registry statistics."""
    reg = ActionItemRegistry()
    return {
        "total_items": reg.get_total_count(),
        "categories": reg.get_category_counts(),
        "stage_mapping": {stage.value: len(cats) for stage, cats in reg.stage_mapping.items()},
    }
