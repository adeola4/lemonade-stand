"""Deep research module for vertical/niche analysis."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

DOCTRINE_MD = Path("/tmp/lemonade_doctrine.md")


def generate_research_bundle(vertical: str, company: str, web_results: dict | None = None) -> dict[str, Any]:
    """Generate a complete research bundle for a vertical.
    
    Args:
        vertical: the industry/niche
        company: company name
        web_results: optional pre-computed web search results from agent layer.
                     If None, attempts standalone web search.
    """
    bundle = {
        "vertical": vertical,
        "company": company,
        "market_size": research_market_size(vertical, web_results),
        "fragmentation": research_fragmentation(vertical, web_results),
        "consolidation_map": research_consolidation(vertical, web_results),
        "target_profile": generate_target_profile(vertical),
        "ebitda_multiples": research_ebitda_multiples(vertical, web_results),
        "seller_financing_norms": research_seller_financing(vertical, web_results),
        "regulatory_barriers": research_regulatory(vertical, web_results),
        "capital_stack_norms": research_capital_stack(vertical, web_results),
        "red_flags": research_red_flags(vertical),
        "doctrine_principles": extract_doctrine_principles(vertical),
    }
    return bundle


def web_search(query: str, limit: int = 3) -> list[dict]:
    """Best-effort free web research. Returns list of results.
    
    Tries multiple methods:
    1. hermes_tools.web_search (when running in agent context)
    2. curl-based search (when standalone)
    """
    # Try hermes_tools first (agent context)
    try:
        from hermes_tools import web_search as hs_search
        result = hs_search(query, limit=limit)
        if result and isinstance(result, dict):
            return result.get("data", {}).get("web", [])
    except (ImportError, Exception):
        pass
    
    # Fallback: use curl with a basic search (DuckDuckGo HTML or similar)
    # Since most search engines block direct API calls, we try a simple approach
    try:
        result = subprocess.run(
            ["curl", "-s", "-A", "Mozilla/5.0",
             f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}",
             "--max-time", "10"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0 and result.stdout.strip():
            # Extract titles from DuckDuckGo HTML
            titles = re.findall(r'class="result__a"[^>]*>([^<]+)<', result.stdout)
            snippets = re.findall(r'class="result__snippet"[^>]*>([^<]+)<', result.stdout)
            return [
                {"title": t[:100], "description": s[:200]}
                for t, s in zip(titles[:limit], snippets[:limit])
            ]
    except Exception:
        pass
    
    return []


def _web_results_to_text(results: list[dict]) -> str:
    """Convert web search results to readable text."""
    if not results:
        return ""
    return " | ".join(f"{r.get('title', '')}: {r.get('description', '')}" for r in results[:3])


def extract_doctrine_principles(vertical: str) -> list[str]:
    """Extract relevant principles from doctrine PDF."""
    if not DOCTRINE_MD.exists():
        return []
    text = DOCTRINE_MD.read_text(encoding="utf-8", errors="ignore")
    chunks = re.split(r"\f+|\n(?=[A-Z][A-Z\s]+\n)", text)
    chunks = [c.strip() for c in chunks if len(c.strip()) > 80]
    
    vwords = set(re.findall(r"[a-z]{3,}", vertical.lower()))
    results = []
    for c in chunks:
        cwords = set(re.findall(r"[a-z]{3,}", c.lower()))
        if vwords & cwords:
            results.append(c[:800])
    
    # Also include core principles regardless of vertical
    core_principles = [
        "11 Steps from an idea to its execution",
        "Five Credos of Success",
        "Comfort Zone expansion",
        "Doofus Test",
        "Other People's Money (OPM)",
        "Quantum Leap Advantage",
        "Structure follows Strategy",
        "Perception is Reality",
        "Investigate before you invest",
    ]
    return results[:5] + core_principles


def generate_target_profile(vertical: str) -> dict:
    """Generate a target company profile for the vertical."""
    return {
        "revenue_range": "$2M-$50M",
        "ebitda_range": "$500K-$5M",
        "multiple_range": "3.0x-6.0x EBITDA",
        "preferred_characteristics": [
            f"Strong regional presence in {vertical}",
            "Owner-operator nearing retirement",
            "Documented cash flow history",
            "Minimal capital expenditure requirements",
            "Recurring revenue component",
        ],
        "avoid": [
            "Declining revenue > 2 years",
            "Over-reliance on single customer",
            "Unresolved legal disputes",
            "Declining market share",
        ],
    }


def research_market_size(vertical: str, web_results: dict | None = None) -> str:
    """Research market size via web."""
    if web_results and web_results.get("market_size"):
        return web_results["market_size"]
    results = web_search(f"{vertical} market size 2024 2025")
    text = _web_results_to_text(results)
    return text if text else f"Market size data for {vertical} — web search returned no results. Manual input required."


def research_fragmentation(vertical: str, web_results: dict | None = None) -> str:
    """Research fragmentation via web."""
    if web_results and web_results.get("fragmentation"):
        return web_results["fragmentation"]
    results = web_search(f"{vertical} industry fragmentation consolidation 2024")
    text = _web_results_to_text(results)
    return text if text else f"Fragmentation data for {vertical} — web search returned no results. Manual input required."


def research_consolidation(vertical: str, web_results: dict | None = None) -> list[dict]:
    """Research recent consolidation activity."""
    if web_results and web_results.get("consolidation_map"):
        return web_results["consolidation_map"]
    results = web_search(f"{vertical} acquisition M&A 2024 2025")
    if results:
        return [{"title": r.get("title", "")[:100], "url": r.get("url", "")} for r in results[:5]]
    return []


def research_ebitda_multiples(vertical: str, web_results: dict | None = None) -> str:
    """Research typical EBITDA multiples."""
    if web_results and web_results.get("ebitda_multiples"):
        return web_results["ebitda_multiples"]
    results = web_search(f"{vertical} EBITDA multiples valuation 2024")
    text = _web_results_to_text(results)
    return text if text else f"EBITDA multiple data for {vertical} — web search returned no results. Manual input required."


def research_seller_financing(vertical: str, web_results: dict | None = None) -> str:
    """Research seller financing norms."""
    if web_results and web_results.get("seller_financing_norms"):
        return web_results["seller_financing_norms"]
    results = web_search(f"{vertical} seller financing norms 2024")
    text = _web_results_to_text(results)
    return text if text else f"Seller financing norms for {vertical} — web search returned no results. Manual input required."


def research_regulatory(vertical: str, web_results: dict | None = None) -> str:
    """Research regulatory barriers."""
    if web_results and web_results.get("regulatory_barriers"):
        return web_results["regulatory_barriers"]
    results = web_search(f"{vertical} regulatory requirements barriers 2024")
    text = _web_results_to_text(results)
    return text if text else f"Regulatory data for {vertical} — web search returned no results. Manual input required."


def research_capital_stack(vertical: str, web_results: dict | None = None) -> str:
    """Research capital stack norms."""
    if web_results and web_results.get("capital_stack_norms"):
        return web_results["capital_stack_norms"]
    results = web_search(f"{vertical} acquisition capital stack financing 2024")
    text = _web_results_to_text(results)
    return text if text else f"Capital stack norms for {vertical} — web search returned no results. Manual input required."


def research_red_flags(vertical: str) -> list[str]:
    """Extract red flags from doctrine + web."""
    return [
        "Declining revenue or EBITDA",
        "Owner dependency (key-man risk)",
        "Customer concentration > 20%",
        "Unresolved litigation",
        "Environmental liabilities",
        "Outdated technology or systems",
        "Poor employee retention",
        "Related-party transactions",
    ]
