"""Approach Generator — for any business model/idea, generate multiple
QLA-grounded ways to execute it. Government contracts, acquisitions,
startups, middleman, offers, etc.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DealApproach:
    """One way to execute a business model QLA-style."""
    approach_id: str
    category: str  # government_contract, acquisition, startup, middleman, offer, jv, etc.
    title: str
    description: str
    peña_alignment: str  # which QLA principles apply
    first_steps: list[str] = field(default_factory=list)
    timeframe_estimate: str = ""
    capital_required: str = ""
    risk_level: str = ""
    scale_potential: str = ""
    examples: list[str] = field(default_factory=list)


def generate_approaches(idea: str, vertical: str, geo: str = "US") -> list[DealApproach]:
    """Generate multiple QLA-grounded execution approaches for a business model."""
    
    approaches = []
    
    # Parse the idea for keywords to customize suggestions
    idea_lower = idea.lower()
    vertical_lower = vertical.lower()
    
    # 1. GOVERNMENT CONTRACT APPROACH
    approaches.append(DealApproach(
        approach_id="gov_contract",
        category="Government Contract",
        title=f"Win Government Contracts in {vertical.title()}",
        description=(
            f"Use the QLA 'find a need and fill it' principle to identify "
            f"government agencies spending money on {vertical_lower}. "
            f"Position your company as the vendor. Government contracts "
            f"are recurring revenue — Peña calls this 'the annuity business.'"
        ),
        peña_alignment=(
            "QLA Principle: 'Sell to the government — they never go out of business.' "
            "Opportunity is defined by need. Government has endless needs in "
            f"{vertical_lower} and limited qualified vendors."
        ),
        first_steps=[
            f"1. Search SAM.gov for {vertical_lower} active RFPs",
            f"2. Register in SAM (System for Award Management)",
            "3. Get necessary certifications (8(a), HUBZone, SDVOSB if applicable)",
            f"4. Research incumbent contracts up for recompete in {geo}",
            "5. Build past performance through small subcontracts first",
            f"6. Network with program officers in {vertical_lower} agencies"
        ],
        timeframe_estimate="6-18 months to first contract",
        capital_required="$5K-$50K (certification, bidding, setup)",
        risk_level="Medium",
        scale_potential="$500K-$50M+ annual revenue",
        examples=[
            f"- {vertical.title()} services contract with VA/DoD",
            f"- State Medicaid {vertical_lower} services agreement",
            f"- Municipal {vertical_lower} operations contract",
            f"- Federal SBA/8(a) set-aside in {vertical_lower}"
        ]
    ))
    
    # 2. ROLL-UP / CONSOLIDATION APPROACH
    approaches.append(DealApproach(
        approach_id="rollup",
        category="Acquisition Roll-Up",
        title=f"Roll Up Fragmented {vertical.title()} Businesses",
        description=(
            f"Use Peña's consolidation principle: find a fragmented industry "
            f"with many small players, acquire them systematically, create "
            f"operating leverage, and dominate a region/nation. "
            f"{vertical.title()} in {geo} is likely fragmented with owners looking to exit."
        ),
        peña_alignment=(
            "QLA Principle: 'Consolidation creates economies of scale and "
            "pricing power.' Buy at 3-4x EBITDA, improve operations, "
            "refinance at 6-8x. That's the spread."
        ),
        first_steps=[
            f"1. Identify 50-200 potential targets in {geo}",
            f"2. Build acquisition criteria: revenue $500K-$5M, owner looking to retire",
            f"3. Secure or arrange acquisition capital (SBA, seller financing, private equity)",
            f"4. Send handwritten letters to top 20 targets",
            "5. Meet with interested sellers, negotiate LOIs",
            "6. Close first acquisition (trophy deal)",
            "7. Use trophy deal to finance next 3-5 acquisitions"
        ],
        timeframe_estimate="3-6 months to first close; 2-5 years to scale",
        capital_required="$250K-$2M (first deal, then recycling)",
        risk_level="Medium-High",
        scale_potential="$5M-$100M revenue; exit at 8-12x EBITDA",
        examples=[
            f"- Buy 5-10 {vertical_lower} businesses at 3x EBITDA",
            "- Centralize back-office, reduce costs 20-30%",
            "- Cross-sell services across portfolio companies",
            "- Build regional brand, then national"
        ]
    ))
    
    # 3. STARTUP / GREENFIELD APPROACH
    approaches.append(DealApproach(
        approach_id="startup",
        category="Startup",
        title=f"Build a {vertical.title()} Startup",
        description=(
            f"Use Peña's 'scratch the itch' principle: if you have a "
            f"better way to solve {vertical_lower} problems, build it "
            f"from scratch. This is the highest risk/highest reward approach."
        ),
        peña_alignment=(
            "QLa Principle: 'See a need, fill it, and get paid.' "
            "The best businesses solve a burning problem that people "
            "will pay to make go away."
        ),
        first_steps=[
            f"1. Identify the #1 pain point in {vertical_lower}",
            f"2. Design a solution 10x better than current options",
            f"3. Find 10 customers willing to pay BEFORE building",
            f"4. Build MVP (minimum viable product/service)",
            "5. Sell, deliver, iterate, repeat",
            f"6. Scale via the 'Quantum Leap' — reinvest profits for growth"
        ],
        timeframe_estimate="6-12 months to product-market fit",
        capital_required="$10K-$250K (bootstrap) or $500K-$2M (VC)",
        risk_level="High",
        scale_potential="$0-$1B+ (lottery ticket upside)",
        examples=[
            f"- {vertical.title()} marketplace/platform",
            f"- {vertical.title()} SaaS tool",
            f"- Premium {vertical_lower} service business",
            f"- {vertical.title()} franchise model"
        ]
    ))
    
    # 4. MIDDLEMAN / BROKER APPROACH
    approaches.append(DealApproach(
        approach_id="middleman",
        category="Middleman / Broker",
        title=f"Become the {vertical.title()} Middleman",
        description=(
            f"Use Peña's OPM principle: connect buyers and sellers "
            f"in {vertical_lower} without owning the underlying asset. "
            f"You take a fee/percentage for making the introduction. "
            f"This is the lowest-capital approach."
        ),
        peña_alignment=(
            "QLA Principle: 'Other People's Money, Other People's Resources.' "
            "You don't need to own anything — just connect supply and demand "
            "and take your spread."
        ),
        first_steps=[
            f"1. Identify the buyers in {vertical_lower} (who's paying?)",
            f"2. Identify the sellers (who has supply but can't reach buyers?)",
            f"3. Build a simple introduction/brokerage process",
            f"4. Get letters of intent from both sides",
            f"5. Negotiate your fee (5-15% typical)",
            f"6. Execute first deal, then systematize"
        ],
        timeframe_estimate="1-3 months to first deal",
        capital_required="$1K-$10K (legal, marketing)",
        risk_level="Low-Medium",
        scale_potential="$100K-$10M annual income",
        examples=[
            f"- {vertical.title()} lead generation broker",
            f"- {vertical.title()} M&A advisor/business broker",
            f"- {vertical.title()} real estate finder's fee",
            f"- {vertical.title()} import/export intermediary"
        ]
    ))
    
    # 5. JOINT VENTURE APPROACH
    approaches.append(DealApproach(
        approach_id="jv",
        category="Joint Venture",
        title=f"Form {vertical.title()} Joint Ventures",
        description=(
            f"Use Peña's 'leverage other people's expertise' principle: "
            f"find people who already have {vertical_lower} businesses "
            f"and partner with them for growth. They have the business, "
            f"you bring the growth capital or capabilities."
        ),
        peña_alignment=(
            "QLA Principle: 'Don't compete — cooperate. Find people "
            "who are already winning and make them more money.'"
        ),
        first_steps=[
            f"1. Identify successful {vertical_lower} operators in {geo}",
            f"2. Approach them with a growth idea they can't execute alone",
            f"3. Structure JV: they contribute the business, you contribute growth",
            f"4. Negotiate profit split (50/50 typical for equal contribution)",
            f"5. Execute growth plan together",
            "6. Expand to more JVs once first succeeds"
        ],
        timeframe_estimate="2-6 months to first JV",
        capital_required="$25K-$100K (your contribution to growth)",
        risk_level="Medium",
        scale_potential="$500K-$20M across portfolio of JVs",
        examples=[
            f"- JV with existing {vertical_lower} business for expansion",
            f"- JV with technology company to modernize {vertical_lower}",
            f"- JV with sales team to grow {vertical_lower} revenue",
            f"- JV with real estate owner for {vertical_lower} facility"
        ]
    ))
    
    # 6. LICENSING / FRANCHISING APPROACH
    approaches.append(DealApproach(
        approach_id="license",
        category="Licensing / Franchise",
        title=f"License or Franchise Your {vertical.title()} Model",
        description=(
            f"Use Peña's 'duplicate success' principle: once you have "
            f"a working {vertical_lower} model, license or franchise it "
            f"to operators in other markets. They pay you for the system."
        ),
        peña_alignment=(
            "QLA Principle: 'Create once, collect forever.' Build the "
            "system once, then let others pay you to use it."
        ),
        first_steps=[
            f"1. Prove the {vertical_lower} model works in one market",
            f"2. Document the system (operations manual, playbook)",
            f"3. Decide: license (franchise fee + royalties) or franchise",
            f"4. Create franchise disclosure document (FDD)",
            f"5. Recruit first 3 franchisees/licensees",
            f"6. Support their success (your success depends on theirs)"
        ],
        timeframe_estimate="6-12 months to first franchisee",
        capital_required="$50K-$200K (legal, FDD, recruitment)",
        risk_level="Medium",
        scale_potential="$1M-$100M (royalty stream)",
        examples=[
            f"- {vertical.title()} franchise system",
            f"- {vertical.title()} licensing to operators",
            f"- {vertical.title()} area developer model",
            f"- {vertical.title()} master franchise for regions"
        ]
    ))
    
    # 7. TURNAROUND / DISTRESSED APPROACH
    approaches.append(DealApproach(
        approach_id="turnaround",
        category="Turnaround / Distressed",
        title=f"Acquire Distressed {vertical.title()} Businesses",
        description=(
            f"Use Peña's 'blood in the streets' principle: find "
            f"{vertical_lower} businesses in distress, acquire them "
            f"cheap, fix operations, and profit from the recovery. "
            f"This is how you buy dollars for 50 cents."
        ),
        peña_alignment=(
            "QLA Principle: 'The best time to buy is when others are "
            "panicking. The best time to sell is when others are greedy.'"
        ),
        first_steps=[
            f"1. Identify struggling {vertical_lower} businesses in {geo}",
            f"2. Analyze why they're failing (usually poor management, not bad market)",
            f"3. Approach owners with a solution to their problem",
            f"4. Negotiate low purchase price (distressed = leverage for you)",
            f"5. Take over, fix operations, restore profitability",
            f"6. Either hold for cash flow or sell at higher multiple"
        ],
        timeframe_estimate="1-3 months to first distressed deal",
        capital_required="$100K-$500K (acquisition + turnaround capital)",
        risk_level="High",
        scale_potential="$2M-$50M (buy at 2x, sell at 6-8x)",
        examples=[
            f"- Distressed {vertical.lower} business acquisition",
            f"- Bankruptcy {vertical_lower} asset purchase",
            f"- Underperforming {vertical_lower} turnaround",
            f"- {vertical.title()} management buyout"
        ]
    ))
    
    # 8. REAL ESTATE BACKED APPROACH
    approaches.append(DealApproach(
        approach_id="realestate",
        category="Real Estate + Business",
        title=f"Combine Real Estate with {vertical.title()} Operations",
        description=(
            f"Use Peña's 'own the dirt' principle: in {vertical_lower}, "
            f"real estate is often the most valuable asset. Buy the business "
            f"AND the real estate, or structure a sale-leaseback. "
            f"Real estate provides collateral, cash flow, and upside."
        ),
        peña_alignment=(
            "QLa Principle: 'Land is the basis of all wealth. They're "
            "not making any more of it.'"
        ),
        first_steps=[
            f"1. Find {vertical_lower} businesses where real estate is part of deal",
            f"2. Get property appraised separately from business valuation",
            f"3. Structure deal to acquire both (or just real estate + lease)",
            f"4. Use real estate as collateral for acquisition financing",
            f"5. If business fails, you still own the real estate (downside protection)",
            f"6. Benefit from both business income AND property appreciation"
        ],
        timeframe_estimate="3-9 months to first deal",
        capital_required="$500K-$5M (real estate component)",
        risk_level="Medium (real estate is collateral)",
        scale_potential="$5M-$50M (combined business + real estate value)",
        examples=[
            f"- Buy {vertical_lower} facility + business together",
            f"- Sale-leaseback on {vertical_lower} property",
            f"- {vertical.title()} REIT holding company",
            f"- Ground-up {vertical_lower} facility development"
        ]
    ))
    
    return approaches


def render_approaches_text(approaches: list[DealApproach]) -> str:
    """Render approaches as formatted text for CLI output."""
    lines = []
    lines.append("=" * 70)
    lines.append("  QLA APPROACH GENERATOR — Multiple Ways to Execute Your Idea")
    lines.append("=" * 70)
    lines.append(f"  {len(approaches)} approaches generated from Peña methodology")
    lines.append("")
    
    for i, a in enumerate(approaches, 1):
        lines.append(f"  [{i}] {a.category.upper()}: {a.title}")
        lines.append(f"      Timeframe: {a.timeframe_estimate} | Capital: {a.capital_required} | Risk: {a.risk_level}")
        lines.append(f"      Scale: {a.scale_potential}")
        lines.append(f"      {a.description[:100]}...")
        lines.append("")
    
    lines.append("-" * 70)
    lines.append("  Pick a number to see full details and first steps.")
    lines.append("-" * 70)
    
    return "\n".join(lines)


def render_approach_detail(a: DealApproach) -> str:
    """Render one approach in full detail."""
    lines = []
    lines.append("=" * 70)
    lines.append(f"  {a.category.upper()}: {a.title}")
    lines.append("=" * 70)
    lines.append("")
    lines.append(f"  DESCRIPTION:")
    lines.append(f"  {a.description}")
    lines.append("")
    lines.append(f"  PEÑA ALIGNMENT:")
    lines.append(f"  {a.peña_alignment}")
    lines.append("")
    lines.append(f"  FIRST STEPS:")
    for step in a.first_steps:
        lines.append(f"  {step}")
    lines.append("")
    lines.append(f"  TIMEFRAME:  {a.timeframe_estimate}")
    lines.append(f"  CAPITAL:    {a.capital_required}")
    lines.append(f"  RISK:       {a.risk_level}")
    lines.append(f"  SCALE:      {a.scale_potential}")
    lines.append("")
    lines.append(f"  EXAMPLES:")
    for ex in a.examples:
        lines.append(f"  {ex}")
    lines.append("=" * 70)
    
    return "\n".join(lines)
