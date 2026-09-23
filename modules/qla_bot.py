"""QLA Bot — Full Deal Automation Scaffolding.

The QLA Bot is the organizational brain that manages the entire deal lifecycle:
  IDENTIFY → BUILD LISTS → RESEARCH → OUTREACH → QUALIFY → ENGAGE → NEGOTIATE → CLOSE

This module implements what Dan Peña calls the "QA" (Quantum Leap Advantage) approach:
automating the process from the first board target/chairman identification all the way
to sitting at the closing table with the seller signing the purchase agreement.

Lists managed:
- Board targets / Chairmen / Industry experts
- Accounting firms (waiting list)
- Legal firms (waiting list)
- Banks / Financial institutions
- Sellers / Acquisition targets
- JV partners
- Service providers

All lists are auto-building through outreach loops and tracked through the deal pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
import json
import re


# ─── Storage Paths ────────────────────────────────────────────────────────────

QA_DATA_DIR = Path.home() / "tan-executive" / "qa-bot"
CONTACTS_FILE = QA_DATA_DIR / "contacts.json"
DEALS_FILE = QA_DATA_DIR / "deals.json"
OUTREACH_LOG = QA_DATA_DIR / "outreach.json"


# ─── Enums ────────────────────────────────────────────────────────────────────

class ContactCategory(str, Enum):
    BOARD_TARGET = "board_target"
    CHAIRMAN = "chairman"
    INDUSTRY_EXPERT = "industry_expert"
    ACCOUNTING_FIRM = "accounting_firm"
    LEGAL_FIRM = "legal_firm"
    BANK = "bank"
    FINANCIAL_INST = "financial_institution"
    SELLER = "seller"
    JV_PARTNER = "jv_partner"
    SERVICE_PROVIDER = "service_provider"
    INVESTMENT_BANKER = "investment_broker"
    BROKERAGE = "brokerage"


class DealStage(str, Enum):
    IDENTIFY = "identify"
    BUILD_LISTS = "build_lists"
    RESEARCH = "research"
    OUTREACH = "outreach"
    QUALIFY = "qualify"
    ENGAGE = "engage"
    NEGOTIATE = "negotiate"
    DUE_DILIGENCE = "due_diligence"
    LOI = "loi"
    CLOSING = "closing"
    CLOSED = "closed"


class ContactStatus(str, Enum):
    IDENTIFIED = "identified"
    RESEARCHED = "researched"
    OUTREACHED = "outreached"
    RESPONDED = "responded"
    QUALIFIED = "qualified"
    ENGAGED = "engaged"
    ACTIVE = "active"
    DECLINED = "declined"
    ON_HOLD = "on_hold"
    CONVERTED = "converted"


class OutreachChannel(str, Enum):
    EMAIL = "email"
    LETTER = "letter"
    PHONE = "phone"
    IN_PERSON = "in_person"
    LINKEDIN = "linkedin"
    INTRODUCTION = "introduction"


# ─── Data Models ──────────────────────────────────────────────────────────────

@dataclass
class Contact:
    """A single contact in the QLA Bot system."""
    id: str
    name: str
    company: str
    category: ContactCategory
    title: str = ""
    email: str = ""
    phone: str = ""
    linkedin: str = ""
    source: str = ""  # how they were identified
    status: ContactStatus = ContactStatus.IDENTIFIED
    priority: str = "medium"  # high / medium / low
    notes: str = ""
    tags: list[str] = field(default_factory=list)
    deal_ids: list[str] = field(default_factory=list)
    outreach_count: int = 0
    last_outreach: str = ""
    next_action: str = ""
    next_action_date: str = ""
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        now = datetime.now(timezone.utc).isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["category"] = self.category.value
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Contact":
        d["category"] = ContactCategory(d["category"])
        d["status"] = ContactStatus(d["status"])
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class Deal:
    """A deal in the QLA Bot pipeline."""
    id: str
    company: str
    vertical: str
    geo: str
    stage: DealStage
    target_seller: str = ""
    ask_price: float = 0
    estimated_value: float = 0
    contacts: list[str] = field(default_factory=list)  # contact IDs
    documents: list[str] = field(default_factory=list)
    notes: str = ""
    red_flags: list[str] = field(default_factory=list)
    next_action: str = ""
    next_action_date: str = ""
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        now = datetime.now(timezone.utc).isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["stage"] = self.stage.value
        return d


@dataclass
class OutreachRecord:
    """Log entry for outreach attempts."""
    id: str
    contact_id: str
    deal_id: str
    channel: OutreachChannel
    direction: str = "outbound"  # outbound / inbound
    summary: str = ""
    response: str = ""
    follow_up_date: str = ""
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


# ─── QLA Bot Engine ────────────────────────────────────────────────────────────

class QABot:
    """QLA Bot engine — manages contacts, deals, and the full deal pipeline."""

    def __init__(self):
        self._ensure_dirs()
        self.contacts = self._load_contacts()
        self.deals = self._load_deals()
        self.outreach = self._load_outreach()

    def _ensure_dirs(self):
        QA_DATA_DIR.mkdir(parents=True, exist_ok=True)

    def _load_contacts(self) -> list[Contact]:
        if not CONTACTS_FILE.exists():
            return []
        data = json.loads(CONTACTS_FILE.read_text())
        return [Contact.from_dict(c) for c in data]

    def _save_contacts(self):
        CONTACTS_FILE.write_text(json.dumps([c.to_dict() for c in self.contacts], indent=2))

    def _load_deals(self) -> list[Deal]:
        if not DEALS_FILE.exists():
            return []
        data = json.loads(DEALS_FILE.read_text())
        return [Deal(**d) for d in data]

    def _save_deals(self):
        DEALS_FILE.write_text(json.dumps([d.to_dict() for d in self.deals], indent=2))

    def _load_outreach(self) -> list[OutreachRecord]:
        if not OUTREACH_LOG.exists():
            return []
        data = json.loads(OUTREACH_LOG.read_text())
        return [OutreachRecord(**r) for r in data]

    def _save_outreach(self):
        OUTREACH_LOG.write_text(json.dumps([asdict(r) for r in self.outreach], indent=2))

    @staticmethod
    def _id(prefix: str) -> str:
        return f"{prefix}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"

    # ── Contact Management ────────────────────────────────────────────────────

    def add_contact(
        self,
        name: str,
        company: str,
        category: ContactCategory | str,
        title: str = "",
        email: str = "",
        phone: str = "",
        linkedin: str = "",
        source: str = "",
        priority: str = "medium",
        notes: str = "",
        tags: list[str] | None = None,
    ) -> Contact:
        """Add a new contact to the QA system."""
        if isinstance(category, str):
            category = ContactCategory(category)

        contact = Contact(
            id=self._id("contact"),
            name=name,
            company=company,
            category=category,
            title=title,
            email=email,
            phone=phone,
            linkedin=linkedin,
            source=source,
            priority=priority,
            notes=notes,
            tags=tags or [],
        )
        self.contacts.append(contact)
        self._save_contacts()
        return contact

    def get_contacts(
        self,
        category: ContactCategory | str | None = None,
        status: ContactStatus | str | None = None,
        company: str | None = None,
        priority: str | None = None,
        deal_id: str | None = None,
    ) -> list[Contact]:
        """Filter contacts by any combination of fields."""
        results = self.contacts
        if category:
            if isinstance(category, str):
                category = ContactCategory(category)
            results = [c for c in results if c.category == category]
        if status:
            if isinstance(status, str):
                status = ContactStatus(status)
            results = [c for c in results if c.status == status]
        if company:
            results = [c for c in results if company.lower() in c.company.lower()]
        if priority:
            results = [c for c in results if c.priority == priority]
        if deal_id:
            results = [c for c in results if deal_id in c.deal_ids]
        return results

    def update_contact(self, contact_id: str, **kwargs: Any) -> Contact | None:
        """Update a contact's fields."""
        for c in self.contacts:
            if c.id == contact_id:
                for k, v in kwargs.items():
                    if hasattr(c, k):
                        setattr(c, k, v)
                c.updated_at = datetime.now(timezone.utc).isoformat()
                self._save_contacts()
                return c
        return None

    # ── Deal Management ───────────────────────────────────────────────────────

    def create_deal(
        self,
        company: str,
        vertical: str,
        geo: str,
        target_seller: str = "",
        ask_price: float = 0,
        estimated_value: float = 0,
        notes: str = "",
    ) -> Deal:
        """Create a new deal in the pipeline."""
        deal = Deal(
            id=self._id("deal"),
            company=company,
            vertical=vertical,
            geo=geo,
            stage=DealStage.IDENTIFY,
            target_seller=target_seller,
            ask_price=ask_price,
            estimated_value=estimated_value,
            notes=notes,
        )
        self.deals.append(deal)
        self._save_deals()
        return deal

    def advance_deal(self, deal_id: str, new_stage: DealStage | str) -> Deal | None:
        """Advance a deal to the next stage."""
        if isinstance(new_stage, str):
            new_stage = DealStage(new_stage)
        for d in self.deals:
            if d.id == deal_id:
                d.stage = new_stage
                d.updated_at = datetime.now(timezone.utc).isoformat()
                self._save_deals()
                return d
        return None

    def get_deals(self, stage: DealStage | str | None = None) -> list[Deal]:
        """Get deals, optionally filtered by stage."""
        if stage is None:
            return self.deals
        if isinstance(stage, str):
            stage = DealStage(stage)
        return [d for d in self.deals if d.stage == stage]

    def link_contact_to_deal(self, contact_id: str, deal_id: str):
        """Link a contact to a deal."""
        for c in self.contacts:
            if c.id == contact_id and deal_id not in c.deal_ids:
                c.deal_ids.append(deal_id)
                self._save_contacts()
        for d in self.deals:
            if d.id == deal_id and contact_id not in d.contacts:
                d.contacts.append(contact_id)
                self._save_deals()

    # ── Outreach ──────────────────────────────────────────────────────────────

    def log_outreach(
        self,
        contact_id: str,
        deal_id: str,
        channel: OutreachChannel | str,
        summary: str = "",
        direction: str = "outbound",
        response: str = "",
        follow_up_date: str = "",
    ) -> OutreachRecord:
        """Log an outreach attempt."""
        if isinstance(channel, str):
            channel = OutreachChannel(channel)
        record = OutreachRecord(
            id=self._id("outreach"),
            contact_id=contact_id,
            deal_id=deal_id,
            channel=channel,
            direction=direction,
            summary=summary,
            response=response,
            follow_up_date=follow_up_date,
        )
        self.outreach.append(record)
        self._save_outreach()

        # Update contact outreach count
        for c in self.contacts:
            if c.id == contact_id:
                c.outreach_count += 1
                c.last_outreach = datetime.now(timezone.utc).isoformat()
                if response:
                    c.status = ContactStatus.RESPONDED
                else:
                    c.status = ContactStatus.OUTREACHED
                self._save_contacts()
                break

        return record

    # ── List Building Loops ───────────────────────────────────────────────────

    def build_contact_list(
        self,
        category: ContactCategory | str,
        vertical: str,
        geo: str = "",
        source_query: str = "",
        max_results: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Build a contact list by searching for contacts of a given category
        in a given vertical/geo. This is the auto-loop that Peña's QA method
        uses to constantly build and refresh contact lists.

        Returns a list of contact dicts ready for outreach.
        """
        if isinstance(category, str):
            category = ContactCategory(category)

        # Build search query from methodology
        query_templates = {
            ContactCategory.BOARD_TARGET: f"{vertical} board of directors chairman CEO {geo}",
            ContactCategory.CHAIRMAN: f"{vertical} chairman board member {geo}",
            ContactCategory.INDUSTRY_EXPERT: f"{vertical} industry expert consultant {geo}",
            ContactCategory.ACCOUNTING_FIRM: f"{vertical} accounting firm CPA M&A {geo}",
            ContactCategory.LEGAL_FIRM: f"{vertical} M&A attorney law firm {geo}",
            ContactCategory.BANK: f"{vertical} bank financing commercial lending {geo}",
            ContactCategory.FINANCIAL_INST: f"{vertical} private equity family office {geo}",
            ContactCategory.SELLER: f"{vertical} business owner seller {geo}",
            ContactCategory.JV_PARTNER: f"{vertical} joint venture partner {geo}",
            ContactCategory.SERVICE_PROVIDER: f"{vertical} service provider {geo}",
            ContactCategory.INVESTMENT_BANKER: f"{vertical} investment banker M&A advisor {geo}",
            ContactCategory.BROKERAGE: f"{vertical} business broker {geo}",
        }

        query = source_query or query_templates.get(category, f"{vertical} {category.value} {geo}")

        # Return structure for the agent to fill via web search
        return {
            "category": category.value,
            "vertical": vertical,
            "geo": geo,
            "query": query,
            "max_results": max_results,
            "status": "ready_for_search",
            "next_step": f"Use web search to find: {query}",
        }

    def get_list_status(self) -> dict[str, Any]:
        """Get the current status of all contact lists."""
        status = {}
        for cat in ContactCategory:
            contacts = self.get_contacts(category=cat)
            status[cat.value] = {
                "total": len(contacts),
                "by_status": {
                    "identified": len([c for c in contacts if c.status == ContactStatus.IDENTIFIED]),
                    "researched": len([c for c in contacts if c.status == ContactStatus.RESEARCHED]),
                    "outreached": len([c for c in contacts if c.status == ContactStatus.OUTREACHED]),
                    "responded": len([c for c in contacts if c.status == ContactStatus.RESPONDED]),
                    "qualified": len([c for c in contacts if c.status == ContactStatus.QUALIFIED]),
                    "engaged": len([c for c in contacts if c.status == ContactStatus.ENGAGED]),
                    "active": len([c for c in contacts if c.status == ContactStatus.ACTIVE]),
                    "declined": len([c for c in contacts if c.status == ContactStatus.DECLINED]),
                    "on_hold": len([c for c in contacts if c.status == ContactStatus.ON_HOLD]),
                    "converted": len([c for c in contacts if c.status == ContactStatus.CONVERTED]),
                },
                "by_priority": {
                    "high": len([c for c in contacts if c.priority == "high"]),
                    "medium": len([c for c in contacts if c.priority == "medium"]),
                    "low": len([c for c in contacts if c.priority == "low"]),
                },
            }
        return status

    def get_outreach_stats(self) -> dict[str, Any]:
        """Get outreach statistics."""
        total = len(self.outreach)
        by_channel = {}
        for ch in OutreachChannel:
            by_channel[ch.value] = len([o for o in self.outreach if o.channel == ch])
        outbound = len([o for o in self.outreach if o.direction == "outbound"])
        inbound = len([o for o in self.outreach if o.direction == "inbound"])
        return {
            "total": total,
            "by_channel": by_channel,
            "outbound": outbound,
            "inbound": inbound,
            "contacts_with_responses": len([c for c in self.contacts if c.status == ContactStatus.RESPONDED]),
        }

    def get_pipeline_summary(self) -> dict[str, Any]:
        """Get a full pipeline summary."""
        return {
            "contacts": {
                "total": len(self.contacts),
                "by_category": {cat.value: len(self.get_contacts(category=cat)) for cat in ContactCategory},
                "by_status": {s.value: len(self.get_contacts(status=s)) for s in ContactStatus},
            },
            "deals": {
                "total": len(self.deals),
                "by_stage": {stage.value: len(self.get_deals(stage=stage)) for stage in DealStage},
            },
            "outreach": self.get_outreach_stats(),
            "lists": self.get_list_status(),
        }

    # ── QA Automation Loops ───────────────────────────────────────────────────

    def get_next_actions(self) -> list[dict[str, Any]]:
        """Get the next actions for the QA bot to execute."""
        actions = []

        # 1. Contacts that need outreach
        identified = self.get_contacts(status=ContactStatus.IDENTIFIED)
        for c in identified[:5]:
            actions.append({
                "type": "outreach",
                "contact_id": c.id,
                "contact_name": c.name,
                "company": c.company,
                "category": c.category.value,
                "action": f"Initial outreach to {c.name} at {c.company}",
                "channel": "email",
            })

        # 2. Contacts that need follow-up
        outreached = self.get_contacts(status=ContactStatus.OUTREACHED)
        for c in outreached[:3]:
            if c.outreach_count < 3:
                actions.append({
                    "type": "follow_up",
                    "contact_id": c.id,
                    "contact_name": c.name,
                    "company": c.company,
                    "action": f"Follow-up #{c.outreach_count + 1} to {c.name} at {c.company}",
                    "channel": "letter" if c.outreach_count == 1 else "phone",
                })

        # 3. Deals that need advancement
        for stage in [DealStage.IDENTIFY, DealStage.BUILD_LISTS, DealStage.OUTREACH, DealStage.QUALIFY]:
            deals = self.get_deals(stage=stage)
            for d in deals[:2]:
                actions.append({
                    "type": "advance_deal",
                    "deal_id": d.id,
                    "company": d.company,
                    "current_stage": d.stage.value,
                    "action": f"Advance {d.company} deal from {d.stage.value}",
                })

        # 4. Lists that need building
        list_status = self.get_list_status()
        for cat_name, status in list_status.items():
            if status["total"] < 10:
                actions.append({
                    "type": "build_list",
                    "category": cat_name,
                    "current_count": status["total"],
                    "action": f"Build {cat_name} list (currently {status['total']} contacts)",
                })

        return actions


# ─── CLI Interface ─────────────────────────────────────────────────────────────

def main():
    """CLI entry point for QLA Bot."""
    import sys

    bot = QABot()

    if len(sys.argv) < 2:
        print("QLA Bot — Deal Automation System")
        print("=" * 40)
        print(f"Contacts: {len(bot.contacts)}")
        print(f"Deals: {len(bot.deals)}")
        print(f"Outreach: {len(bot.outreach)}")
        print()
        print("Commands:")
        print("  qa-board <vertical> <geo>       — Build board target list")
        print("  qa-accounting <vertical> <geo>  — Build accounting firm list")
        print("  qa-legal <vertical> <geo>       — Build legal firm list")
        print("  qa-banks <vertical> <geo>       — Build bank/financial list")
        print("  qa-sellers <vertical> <geo>     — Build seller target list")
        print("  qa-status                       — Show full pipeline status")
        print("  qa-next                         — Show next actions")
        return

    command = sys.argv[1]

    if command == "qa-board" and len(sys.argv) >= 4:
        result = bot.build_contact_list(ContactCategory.BOARD_TARGET, sys.argv[2], sys.argv[3])
        print(json.dumps(result, indent=2))

    elif command == "qa-accounting" and len(sys.argv) >= 4:
        result = bot.build_contact_list(ContactCategory.ACCOUNTING_FIRM, sys.argv[2], sys.argv[3])
        print(json.dumps(result, indent=2))

    elif command == "qa-legal" and len(sys.argv) >= 4:
        result = bot.build_contact_list(ContactCategory.LEGAL_FIRM, sys.argv[2], sys.argv[3])
        print(json.dumps(result, indent=2))

    elif command == "qa-banks" and len(sys.argv) >= 4:
        result = bot.build_contact_list(ContactCategory.BANK, sys.argv[2], sys.argv[3])
        print(json.dumps(result, indent=2))

    elif command == "qa-sellers" and len(sys.argv) >= 4:
        result = bot.build_contact_list(ContactCategory.SELLER, sys.argv[2], sys.argv[3])
        print(json.dumps(result, indent=2))

    elif command == "qa-status":
        summary = bot.get_pipeline_summary()
        print(json.dumps(summary, indent=2))

    elif command == "qa-next":
        actions = bot.get_next_actions()
        print(json.dumps(actions, indent=2))

    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
