"""Brain command with version tracking."""
from __future__ import annotations

import json
from pathlib import Path

from .ingest import extract_content, store_in_brain, search_brain, list_all, classify_url
from modules.versioning.version import record_change, create_snapshot, list_versions, rollback, get_version


def cmd_brain(url: str) -> dict:
    """Ingest URL and report system upgrade."""
    print(f"🧠 Ingesting: {url}")
    
    content = extract_content(url)
    raw_text = content.get("raw_text", "")
    
    if not raw_text:
        print("❌ Could not extract content")
        return {"status": "failed", "url": url}
    
    content_id = store_in_brain(content)
    
    if content_id < 0:
        print("❌ Failed to store")
        return {"status": "error", "url": url}
    
    # Report results
    source_type = content.get("source_type", "?")
    title = content.get("title", "Untitled")[:80]
    relevance = content.get("relevance", "GENERAL")
    char_count = len(raw_text)
    
    from .ingest import find_doctrine_refs, extract_action_items, extract_principles
    doctrine_refs = find_doctrine_refs(raw_text)
    action_items = extract_action_items(raw_text)
    principles = extract_principles(raw_text)
    
    # Record in version control
    record_change(
        change_type="brain_ingest",
        target=Path.home() / "tan-executive" / "brain" / "brain.db",
        description=f"Ingested: {title} ({source_type})",
        metadata={
            "url": url,
            "content_id": content_id,
            "relevance": relevance,
            "doctrine_refs": doctrine_refs,
        },
        do_backup=False,
    )
    
    print(f"")
    print(f"✅ Ingested as #{content_id}")
    print(f"")
    print(f"📋 Summary")
    print(f"   Title: {title}")
    print(f"   Type: {source_type}")
    print(f"   Relevance: {relevance}")
    print(f"   Content: {char_count:,} chars")
    print(f"")
    print(f"🏷️  Tags")
    print(f"   Doctrine refs: {', '.join(doctrine_refs) if doctrine_refs else 'None'}")
    print(f"   Action items: {len(action_items)}")
    print(f"   Principles: {len(principles)}")
    print(f"")
    
    if action_items:
        print(f"⚡ Top Action Items")
        for i, a in enumerate(action_items[:5], 1):
            print(f"   {i}. {a[:100]}")
        print(f"")
    
    if principles:
        print(f"💡 Key Principles")
        for i, p in enumerate(principles[:5], 1):
            print(f"   {i}. {p[:100]}")
        print(f"")
    
    print(f"🔄 System Change Logged")
    print(f"   All ingestions tracked with version control")
    print(f"   Rollback available at any time")
    
    return {
        "status": "ingested",
        "id": content_id,
        "url": url,
        "relevance": relevance,
        "source_type": source_type,
    }
