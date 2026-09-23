"""Web search via Jina + DuckDuckGo HTML — no gateway, no API key."""
from __future__ import annotations

import json
import re
import subprocess
from typing import Any


def search_web(query: str, num_results: int = 10) -> list[dict]:
    """Search DuckDuckGo HTML via Jina proxy."""
    import urllib.parse
    
    encoded = urllib.parse.quote_plus(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded}"
    
    try:
        result = subprocess.run(
            ["curl", "-s", "-L", "--max-time", "20",
             f"https://r.jina.ai/{url}",
             "-H", "X-Return-Format: text"],
            capture_output=True, text=True, timeout=25
        )
        
        if result.returncode != 0:
            return []
        
        raw = result.stdout.strip()
        if not raw or 'blocked by network security' in raw.lower():
            return []
        
        lines = raw.split('\n')
        results = []
        
        for i, line in enumerate(lines):
            # Look for URL line (indented, contains http or www.)
            # Format: "       URL    Description..."
            url_match = re.match(r'\s+(https?://\S+|www\.\S+)\s*(.*)', line)
            if url_match:
                raw_url = url_match.group(1)
                desc_inline = url_match.group(2).strip()
                
                # Normalize URL
                url = raw_url if raw_url.startswith('http') else f'https://{raw_url}'
                
                if 'duckduckgo' in url:
                    continue
                
                # Find title: previous non-empty, non-URL line
                title = ""
                for j in range(i-1, -1, -1):
                    candidate = lines[j].strip()
                    if candidate and 'http' not in candidate and not candidate.startswith('['):
                        title = candidate
                        break
                
                # Collect description from following lines
                desc_lines = [desc_inline] if desc_inline else []
                for j in range(i+1, len(lines)):
                    next_line = lines[j].strip()
                    if not next_line:
                        break
                    if re.match(r'\s+(https?://|www\.)', lines[j]):
                        break
                    if next_line.startswith('['):
                        continue
                    desc_lines.append(next_line)
                
                desc = ' '.join(desc_lines)[:300]
                
                if title:
                    results.append({
                        "title": title,
                        "url": url,
                        "snippet": desc,
                        "source": "jina_ddg",
                    })
                
                if len(results) >= num_results:
                    return results
        
        return results
        
    except Exception as e:
        return []


def search_targets(vertical: str, geo: str) -> list[dict]:
    """Search for companies that might be acquisition targets."""
    queries = [
        f"{vertical} companies {geo} for sale",
        f"{vertical} businesses {geo} acquisition",
        f"buy {vertical} company {geo}",
    ]
    
    all_results = []
    seen_urls = set()
    
    for query in queries:
        results = search_web(query, 5)
        for r in results:
            url = r.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_results.append(r)
    
    return all_results


def search_market_data(vertical: str, geo: str) -> dict:
    """Search for market size, fragmentation, and consolidation data."""
    results = {}
    
    queries = {
        "market_size": f"{vertical} market size {geo} 2024 2025",
        "fragmentation": f"{vertical} industry fragmentation consolidation opportunities",
        "valuation": f"{vertical} EBITDA multiples acquisition valuation 2025",
        "trends": f"{vertical} industry trends growth forecast {geo}",
    }
    
    for key, query in queries.items():
        search_results = search_web(query, 5)
        results[key] = search_results
    
    return results


def search_red_flags(company_name: str) -> list[dict]:
    """Search for red flags about a company."""
    queries = [
        f"{company_name} lawsuit legal issues",
        f"{company_name} complaints BBB",
        f"{company_name} financial problems bankruptcy",
        f"{company_name} regulatory issues violations",
    ]
    
    flags = []
    for query in queries:
        results = search_web(query, 3)
        if results:
            flags.append({"query": query, "results": results})
    
    return flags


def search_target_details(company_name: str) -> dict:
    """Search for detailed information about a specific company."""
    details = {"name": company_name, "findings": {}}
    
    queries = {
        "overview": f"{company_name} company overview revenue employees",
        "ownership": f"{company_name} owner founder leadership",
        "news": f"{company_name} news recent developments",
    }
    
    for key, query in queries.items():
        results = search_web(query, 5)
        details["findings"][key] = results
    
    return details


def search_competition(vertical: str, geo: str) -> list[dict]:
    """Search for competitive landscape."""
    query = f"{vertical} top companies market share {geo}"
    return search_web(query, 8)
