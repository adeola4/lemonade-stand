"""Outreach module — decides channel, drafts content, tracks responses.
The QLA bot picks the best channel per deal based on owner psychology and deal stage.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# Peña's outreach psychology:
# - Handwritten letter = highest response rate (stands out, shows effort)
# - Email = fast, scalable, good for follow-up
# - Phone = direct, shows confidence, works on older owners
# - In-person = ultimate power move (only for local deals)


@dataclass
class OutreachPlan:
    deal_name: str
    channel: str  # "email", "letter", "phone", "in_person"
    reasoning: str  # Why this channel
    owner_psychology: str  # What we know about the owner
    draft_subject: str = ""
    draft_body: str = ""
    draft_script: str = ""
    follow_up_days: int = 3
    escalate_after_days: int = 14
    status: str = "draft"


def decide_channel(target: dict, owner_info: dict | None = None) -> tuple[str, str]:
    """Decide the best outreach channel based on Peña's methodology.
    
    Returns: (channel, reasoning)
    """
    # Peña's rules:
    # 1. If we have a direct phone number and owner is >55 → phone first
    # 2. If owner is tech-savvy / business-savvy → email first
    # 3. If we know the address and deal is local → letter (stands out)
    # 4. For high-value targets → in-person (the power move)
    # 5. Default → letter (handwritten beats email 3:1)
    
    name = target.get("title", target.get("name", ""))
    estimated_value = target.get("estimated_value", "unknown")
    
    # Check what contact info we have
    has_phone = owner_info.get("phone") if owner_info else False
    has_email = owner_info.get("email") if owner_info else False
    has_address = owner_info.get("address") if owner_info else False
    owner_age = owner_info.get("age_estimate", 0) if owner_info else 0
    
    # High-value deal
    if estimated_value and isinstance(estimated_value, (int, float)) and estimated_value > 5000000:
        return "in_person", f"Deal value ${estimated_value:,.0f}+ warrants in-person. Peña: 'The personal touch on a big deal shows you're serious.'"
    
    # Older owner with phone
    if has_phone and owner_age > 55:
        return "phone", f"Owner estimated >55, direct phone available. Peña: 'Older owners respect confidence. Call them directly.'"
    
    # We have an address for a local deal
    if has_address:
        return "letter", f"Physical address available. Handwritten letter stands out from email noise. Peña: 'A real letter shows you took the time.'"
    
    # Default
    if has_email:
        return "email", "Email as primary channel. Fast, scalable, professional."
    
    return "letter", "Default to letter. Peña: 'Handwritten letters get 3x the response of cold emails.'"


def generate_outreach(target: dict, owner_name: str = "", company_name: str = "", 
                      buyer_name: str = "TAN Holdings") -> OutreachPlan:
    """Generate a complete outreach plan for a target."""
    channel, reasoning = decide_channel(target)
    
    plan = OutreachPlan(
        deal_name=target.get("title", target.get("name", "Unknown")),
        channel=channel,
        reasoning=reasoning,
        owner_psychology=owner_name if owner_name else "Unknown - needs research",
    )
    
    if channel == "email":
        plan.draft_subject = generate_email_subject(target, company_name)
        plan.draft_body = generate_email_body(target, owner_name, buyer_name)
        plan.follow_up_days = 3
    elif channel == "letter":
        plan.draft_body = generate_letter_body(target, owner_name, buyer_name)
        plan.follow_up_days = 7
    elif channel == "phone":
        plan.draft_script = generate_phone_script(target, owner_name, buyer_name)
        plan.follow_up_days = 2
    elif channel == "in_person":
        plan.draft_body = generate_inperson_strategy(target, owner_name, buyer_name)
        plan.follow_up_days = 5
    
    plan.escalate_after_days = plan.follow_up_days * 3
    
    return plan


def generate_email_subject(target: dict, company_name: str = "") -> str:
    """Generate email subject line."""
    name = target.get("title", target.get("name", "Your Business"))
    # Peña: subject line should be personal and specific
    subjects = [
        f"Question about {name}",
        f"Confidential inquiry - {name}",
        f"Potential acquisition - {name}",
    ]
    return subjects[0]


def generate_email_body(target: dict, owner_name: str = "", buyer_name: str = "TAN Holdings") -> str:
    """Generate personalized outreach email."""
    name = target.get("title", target.get("name", "Your Company"))
    owner = owner_name if owner_name else "[Owner Name]"
    
    email = f"""Subject: Question about {name}

{owner},

I'll be direct.

I'm acquiring home health care agencies in the Southeast. Your company came across my radar, and I'd like to have a brief conversation.

I'm not a broker. I'm a buyer.

Here's what I bring to the table:
- Close within 60 days
- Keep your team intact
- Honor your legacy
- Fair price based on real numbers

If you've ever considered selling — even casually — let's talk. No obligation. Confidential.

Call me directly: [YOUR PHONE]

Or reply to this email.

Best,
{buyer_name}
"""
    return email


def generate_letter_body(target: dict, owner_name: str = "", buyer_name: str = "TAN Holdings") -> str:
    """Generate handwritten letter template."""
    name = target.get("title", target.get("name", "Your Company"))
    owner = owner_name if owner_name else "[Owner Name]"
    
    letter = f"""[HANDWRITTEN ON PLAIN PAPER]

{owner}

I'm writing to you directly because I believe your company, {name}, might be a fit for what I'm building.

I'm not a business broker. I'm acquiring home health care agencies in the Southeast US. I close fast, I keep teams intact, and I pay fair prices.

If the thought of selling has ever crossed your mind, I'd appreciate a conversation.

Call me: [YOUR PHONE]
Email: [YOUR EMAIL]

Confidential. No pressure. Just a conversation.

Sincerely,
{buyer_name}

P.S. Even if you're not interested, I'd be happy to share what I'm seeing in the market — no strings attached.
"""
    return letter


def generate_phone_script(target: dict, owner_name: str = "", buyer_name: str = "TAN Holdings") -> str:
    """Generate phone call script."""
    name = target.get("title", target.get("name", "Your Company"))
    
    script = f"""PHONE SCRIPT: {name}

[PRE-CALL]
- Best time: Tuesday-Thursday, 10am-2pm
- Backup time: Tuesday-Thursday, 4pm-5pm
- Have deal sheet ready
- Be standing up (projects confidence)

[OPENING]
"Hi [Owner Name], my name is [Your Name] with {buyer_name}. Do you have 90 seconds? I know you're busy."

[IF YES / "SURE"]
"I'm acquiring home health care agencies in the Southeast. Your company came up in my research, and I wanted to reach out directly. I'm not a broker — I'm a buyer. We close within 60 days, keep teams intact, and pay fair prices."

[IF INTERESTED]
"Great. Here's what I'd like to do: can we set up a 15-minute call next week? I'll share exactly how I work and what I'm looking for. If there's a fit, we move forward. If not, no hard feelings."

[IF NOT INTERESTED / "NOT INTERESTED"]
"I appreciate you being straight with me. Can I ask one quick question — is it that you're not interested in selling, or just not right now?"

[IF "NOT RIGHT NOW"]
"Understood. Can I send you a quick email with my info? That way, when the time is right, you know who to call."

[IF HARD NO]
"Thank you for your time. If anything changes, here's my number. I mean that."

[CLOSING]
"Again, I appreciate your time. I'll follow up in a few days. Talk soon."

[POST-CALL]
- Log outcome in pipeline
- Schedule follow-up task
- If left voicemail: shorter version, emphasize "not a broker"
"""
    return script


def generate_inperson_strategy(target: dict, owner_name: str = "", buyer_name: str = "TAN Holdings") -> str:
    """Generate in-person visit strategy."""
    name = target.get("title", target.get("name", "Target Company"))
    
    strategy = f"""IN-PERSON VISIT STRATEGY: {name}

[PEÑA METHOD]
"The ultimate power move is showing up. It shows you're serious, you're confident, and you respect the owner enough to be there in person."

[PREPARATION]
- Research the company thoroughly before arriving
- Know the owner's background, interests, history
- Bring a one-page deal sheet (not a full deck)
- Dress sharp but not flashy
- Arrive 5 minutes early

[THE VISIT]
- Don't ask to buy the company in the first meeting
- Ask questions about their business, their story, their goals
- Find out what they REALLY want (money is #1, but legacy, team, freedom all matter)
- Share your vision — what you're building, why it matters
- Let them ask questions
- End with: "I'd love to come back and show you what a deal might look like"

[FOLLOW-UP]
- Send handwritten thank-you note the same day
- Call within 48 hours to continue conversation
- Don't rush — in-person deals take longer but close bigger
"""
    return strategy
