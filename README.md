# 🍋 Lemonade Stand — Autonomous QLA Deal Execution

**Version:** V0.26 | **Status:** Active | **Owner:** Transaction Action Network (TAN)

## What Is Lemonade Stand?

Lemonade Stand is a **deal execution system** that runs Dan Peña's Quantum Leap Advantage (QLA) methodology autonomously. It is built as a **Hermes skill** (`tan-executive-agent`) with a **CLI tool** (`main.py`) and a **Vercel-hosted dashboard** (`lemonadestandui.vercel.app`).

**One sentence:** Give it a prompt or document about a business idea → it runs Peña's 11-step QLA process and produces real deal outputs (targets, research, scorecards, documents, outreach plans, pipeline tracking, missions).

---

## Two-Brain Architecture

### 🧠 Knowledge Brain — The QLA Methodology (Your SOP)

This is **the methodology** — the system the AI agent uses to build every workflow, every automation, every decision.

**Not a search database. The actual procedure the agent follows.**

- **What:** Dan Peña's *Your First $100 Million* extracted into 2,979 machine-readable action items
- **Purpose:** Dictates HOW the AI agent formats its automations, executes step-by-step, and builds every workflow
- **Content:**
  - Mindset principles (68)
  - Perception principles (431)
  - Execution & action principles (1,218)
  - Capital & financing principles (487)
  - Deal principles (291)
  - Strategy & consolidation (150)
  - Team & dream team (150)
  - Peña-isms (170)
  - Negotiation (14)
- **Mapped to:** Peña's 11-step deal process stages
- **Nature:** Static — extracted once from PDF, parsed into machine-readable procedures

### 🤖 AI Brain — The Autonomous Execution Layer (The Agent)

This is **the agent that does the work** — builds workflows, runs automations, executes deals.

**The AI Brain IS the agent. It doesn't search the Knowledge Brain. It FOLLOWS it.**

- **What:** Autonomous AI agent that runs business deals QLA-style
- **Purpose:** Automate every workflow critical to deal success
- **What it automates (examples):**
  - Ideal — identifying the right targets, structure, approach
  - Flow — pipeline workflows, deal stages, follow-up sequences
  - Content generation — outreach copy, emails, letters, LOIs, NDAs
  - Lead generation — finding sellers, JV partners, service providers
  - Banking relationships — identifying capital sources
  - Accounting firms — due diligence prep, financial analysis
  - Seller outreach — letters, emails, scripts, in-person strategies
  - Document generation — ES, LOI, NDA, Offer, Term Sheet, Projections
  - Joint venture partner identification
  - Deal pipeline tracking through 11 stages

### How They Work Together

```
User Prompt or Document
        ↓
Knowledge Brain (2,979 Peña action items — THE SOP)
        ↓
AI Brain (agent FOLLOWS the SOP to execute)
        ↓
11-Step QLA Deal Process → Real Outputs
```

**No search order.** The agent doesn't "query" the Knowledge Brain like a database. The Knowledge Brain IS the workflow the agent runs.

---

## 11-Step QLA Deal Process

Every deal goes through these stages, mapped to 2,979 Peña action items:

| Step | Stage | What Happens |
|------|-------|--------------|
| 1 | **Intake** | Parse idea → extract company/vertical/geo/approach |
| 2 | **Identify** | Source targets using Jina + DuckDuckGo search |
| 3 | **Generalities** | Market research, industry mapping |
| 4 | **Specifics** | Target details, financials, ownership structure |
| 5 | **Decision** | QLA scorecard — PROCEED / WATCH / KILL |
| 6 | **Investigation** | Red flags, verification, Peña principles cited |
| 7 | **Action Plan** | Channel + timeline + next steps |
| 8 | **Critical Path** | Dependencies, blockers, sequence |
| 9 | **Documents** | ES, LOI, NDA, Offer, Term Sheet, Projections |
| 10 | **Outreach** | Template generation per channel |
| 11 | **Pipeline** | Track through sourcing → closing |

---

## How to Use the Dashboard (lemonadestandui.vercel.app)

### Homepage Buttons

| Button | What It Does |
|--------|-------------|
| 🍋 **Launch** | Create a new deal thread — generates a Discord-ready deal card |
| 💡 **Approach Generator** | Enter an idea → get 8 QLA-grounded execution approaches |
| 🎯 **Mission Scroll** | Scrolling Peña quotes + Mission Status Tracker |
| 📋 **Status Tracker** | View all deals, active campaigns, pipeline |
| 🚀 **Start QLA** | Enter a prompt → runs full 11-step QLA cycle |
| 🔗 **Links Manager** | All important links in one place (websites, Discord, Drive, GitHub) |
| 🎯 **Missions** | Mission Center — create, track, and manage missions |
| 🧠 **Brain Feed** | Ingest URLs into the AI Brain |
| 📧 **Outreach** | Generate outreach templates per channel |

### Workflow

1. **Start:** Enter a business idea (any level of detail)
2. **Approach:** Pick from 8 QLA execution approaches
3. **Generate:** Get an ultra-detailed deal card for Discord
4. **Launch:** Create a Discord thread with the deal card
5. **Execute:** System runs 11-step QLA cycle automatically
6. **Track:** Monitor deals in pipeline + Mission Center
7. **Outreach:** Generate templates and send via email/letter

### Mission Center

The Mission Center connects two systems:
- **Mission Scroll Generator** — creates color-coded mission briefings
- **Daily Status Tracker** — tracks active missions, blockers, progress

Features:
- Create missions manually on the web UI
- Admit missions via Discord: `@Hermes mission: [title] priority: [critical/standard/routine] for [company]`
- Track status: Active / Blocked / Completed
- Priority coding: 🔴 Critical / 🟠 Standard / 🟢 Routine

---

## CLI Commands

```bash
# Start a new deal from a prompt
python main.py start "Build a home health care roll-up in the Southeast US"

# Execute full QLA cycle
python main.py execute --company "Apex" --vertical "home health care" --geo "Southeast US" --idea "..."

# Generate approaches
python main.py approaches --idea "Build a home health care roll-up" --vertical "home health care" --geo "Southeast US"

# Launch deal thread (generates Discord-ready card)
python main.py launch --idea "Build a home health care roll-up" --company "Apex" --approach "Acquisition Roll-Up"

# Mission management
python main.py mission --action create --title "Close 3 LOI" --priority critical --company "Apex" --source discord
python main.py mission --action list
python main.py mission-stats

# View pipeline
python main.py pipeline --company "Apex"

# Generate outreach
python main.py outreach --company "Apex" --target "John Smith" --owner "Jane Doe"

# Brain operations
python main.py brain "https://example.com/article"
python main.py brain-search "OPM leverage capital structure"
python main.py kb-stats
```

---

## Document Types Generated

- **Executive Summary** — Deal overview, ask, use of funds
- **Letter of Intent (LOI)** — Acquisition terms, valuation range
- **Non-Disclosure Agreement (NDA)** — Mutual confidentiality
- **Offer Letter** — Formal purchase offer
- **Term Sheet** — Key deal terms summary
- **Due Diligence Checklist** — Document request list
- **Purchase Agreement Outline** — Asset/stock purchase structure
- **Financial Projections** — 3-year revenue/EBITDA forecast

---

## System Architecture

```
Hermes Agent (Discord / Telegram)
        ↓
tan-executive-agent skill (main.py)
        ↓
┌─────────────────────────────────────┐
│  Knowledge Brain (2,979 Peña items) │
│  ↓ dictates HOW                     │
│  AI Brain (agent execution layer)   │
│  ↓ runs                             │
│  11-Step QLA Process                │
│  ↓ produces                         │
│  Deal Pipeline + Documents + Output │
└─────────────────────────────────────┘
        ↓
Vercel Dashboard (lemonadestandui.vercel.app)
- Mission Scroll + Status Tracker
- Approach Generator
- Deal Launch + Deal Card
- Mission Center
- Links Manager
- Brain Feed
- Outreach Templates
```

---

## Key Principles

1. **All outputs grounded in QLA doctrine** — no generative fluff
2. **Deterministic workflows** — same input → same output
3. **No search order** — Knowledge Brain IS the workflow, not a lookup table
4. **Autonomous execution** — agent stops only when no remaining task can be built without user-provided data that is NOT web-searchable
5. **Two-way sync** — web UI ↔ Discord agent ↔ CLI all produce the same data
6. **Zero budget** — no paid APIs, Jina + DuckDuckGo HTML search

---

## Version History

| Version | Changes |
|---------|---------|
| V0.26 | Mission Center, Links Manager, Approach Generator, Launch Deal Thread, README |
| V0.25 | Launch panel, version string fix |
| V0.24 | Launch Deal Thread UI |
| V0.23 | Launch CLI command |
| V0.22 | Approach Generator (8 QLA approaches) |
| V0.21 | Knowledge Brain = methodology SOP, AI Brain = agent that executes it |
| V0.20 | AI Brain purpose clarified: automate business so AI agent can run it |
| V0.19 | Two-Brain Architecture distinction |
| V0.18 | Mission Scroll + Status Tracker |
| V0.17 | Deployment alias fix |
| V0.16 | Start QLA tab, README |
| V0.15 | Deal Engine |
| V0.14 | Paperworkman UI + Knowledge Brain wired into QLA |
| V0.13 | Knowledge Brain search working |

---

## Owner & Contact

**Owner:** Transaction Action Network (TAN)
**Discord:** TAN LAB #1 SUPERCOMPUTER / lemonade-stand
**Agent:** Hermes
