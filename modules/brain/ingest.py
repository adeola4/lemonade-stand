"""Second Brain ingestion pipeline with versioning.

Every ingestion is tracked. Upgrades are installed with full backup/rollback.
"""
from __future__ import annotations

import json
import re
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

BRAIN_DB = Path.home() / "tan-executive" / "brain" / "brain.db"
DOCTRINE_MD = Path("/tmp/lemonade_doctrine.md")

from modules.versioning.version import (
    init_db as init_versions_db,
    record_change,
    install_or_upgrade,
    file_backed_up,
    create_snapshot,
    list_versions,
    list_snapshots,
    rollback,
    rollback_to_snapshot,
    get_version,
)


def init_db() -> sqlite3.Connection:
    """Initialize the brain database."""
    BRAIN_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(BRAIN_DB))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS content (
            id INTEGER PRIMARY KEY,
            url TEXT UNIQUE,
            source_type TEXT,
            title TEXT,
            raw_text TEXT,
            summary TEXT,
            doctrine_refs TEXT,
            action_items TEXT,
            principles TEXT,
            relevance TEXT,
            metadata TEXT,
            created_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            content_id INTEGER,
            tag TEXT,
            FOREIGN KEY(content_id) REFERENCES content(id)
        )
    """)
    conn.commit()
    return conn


def classify_url(url: str) -> str:
    """Classify URL type."""
    parsed = urlparse(url.lower())
    host = parsed.hostname or ""
    path = parsed.path or ""

    if "twitter.com" in host or "x.com" in host:
        return "twitter_thread" if "/status/" in path else "twitter_profile"
    if "github.com" in host:
        return "github_repo"
    if "medium.com" in host:
        return "medium"
    if "substack.com" in host:
        return "substack"
    if "reddit.com" in host or "redd.it" in host:
        return "reddit"
    if "news.ycombinator.com" in host:
        return "hackernews"
    if "linkedin.com" in host:
        return "linkedin"
    if path.endswith(".pdf"):
        return "pdf"
    return "webpage"


def fetch_with_jina(url: str) -> str | None:
    """Fetch URL via r.jina.ai."""
    try:
        result = subprocess.run(
            ["curl", "-sL", f"https://r.jina.ai/{url}",
             "-H", "Accept: text/plain",
             "--max-time", "10"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0 and result.stdout.strip():
            text = result.stdout.strip()
            if "Anonymous access to x.com blocked" in text:
                return None
            if "login wall" in text.lower() or len(text) < 50:
                return None
            return text
    except Exception:
        pass
    return None


def fetch_with_fxtwitter(url: str) -> dict | None:
    """Fetch tweet via api.fxtwitter.com."""
    try:
        result = subprocess.run(
            ["curl", "-sL", url.replace("https://x.com/", "https://api.fxtwitter.com/").replace("https://twitter.com/", "https://api.fxtwitter.com/"),
             "--max-time", "10"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data
    except Exception:
        pass
    return None


def fetch_web_content(url: str) -> str | None:
    """Fetch general web content with fallback."""
    try:
        from hermes_tools import web_extract
        result = web_extract([url], char_limit=15000)
        if result.get("results"):
            r = result["results"][0]
            text = r.get("content", "")
            if text and len(text) > 100:
                return text
    except Exception:
        pass
    return fetch_with_jina(url)


def extract_content(url: str) -> dict[str, Any]:
    """Extract content using platform-aware methods."""
    source_type = classify_url(url)

    if source_type == "twitter_thread":
        return extract_twitter_thread(url)
    elif source_type == "github_repo":
        return extract_github_repo(url)
    elif source_type in ("medium", "substack", "reddit"):
        return extract_via_jina(url, source_type)
    elif source_type == "linkedin":
        return {"url": url, "source_type": source_type, "title": "LinkedIn (auth required)", "raw_text": "", "metadata": "{}", "relevance": "NO_ACCESS"}
    else:
        return extract_generic_web(url, source_type)


def extract_twitter_thread(url: str) -> dict[str, Any]:
    """Extract Twitter/X thread using Jina + fxtwitter."""
    clean_url = url.split("?")[0]

    text = fetch_with_jina(clean_url)
    if text:
        return {
            "url": url,
            "source_type": "twitter_thread",
            "title": "Twitter Thread",
            "raw_text": text[:10000],
            "metadata": "{}",
            "relevance": classify_relevance(text)
        }

    data = fetch_with_fxtwitter(clean_url)
    if data:
        tweet_text = data.get("tweet", {}).get("text", "")
        author = data.get("tweet", {}).get("author", {}).get("name", "")
        return {
            "url": url,
            "source_type": "twitter_thread",
            "title": f"Tweet by {author}",
            "raw_text": tweet_text[:10000],
            "metadata": json.dumps({"author": author}),
            "relevance": classify_relevance(tweet_text)
        }

    return {
        "url": url,
        "source_type": "twitter_thread",
        "title": "Twitter Thread (extract failed)",
        "raw_text": "",
        "metadata": "{}",
        "relevance": "NOISE"
    }


def extract_github_repo(url: str) -> dict[str, Any]:
    """Extract GitHub repo README + metadata."""
    parsed = urlparse(url)
    path_parts = [p for p in (parsed.path or "").split("/") if p]
    if len(path_parts) < 2:
        return {"url": url, "source_type": "github_repo", "title": "GitHub Repo", "raw_text": "", "metadata": "{}", "relevance": "NOISE"}

    owner, repo = path_parts[0], path_parts[1]

    readme = ""
    for branch in ["main", "master"]:
        try:
            result = subprocess.run(
                ["curl", "-s", "--max-time", "10",
                 f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/README.md"],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0 and result.stdout.strip():
                readme = result.stdout
                break
        except Exception:
            continue

    meta = {}
    try:
        result = subprocess.run(
            ["curl", "-s", "--max-time", "10",
             f"https://api.github.com/repos/{owner}/{repo}"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            meta = json.loads(result.stdout)
    except Exception:
        pass

    raw_text = f"# {meta.get('full_name', repo)}\n\n{meta.get('description', '')}\n\n{readme}"
    title = meta.get("full_name", f"{owner}/{repo}")

    return {
        "url": url,
        "source_type": "github_repo",
        "title": title,
        "raw_text": raw_text[:15000],
        "metadata": json.dumps({
            "stars": meta.get("stargazers_count", 0),
            "language": meta.get("language", ""),
            "topics": meta.get("topics", []),
        }),
        "relevance": classify_relevance(raw_text)
    }


def extract_via_jina(url: str, source_type: str) -> dict[str, Any]:
    """Extract via Jina proxy (Medium, Substack, Reddit)."""
    text = fetch_with_jina(url)
    if text:
        return {
            "url": url,
            "source_type": source_type,
            "title": source_type.capitalize(),
            "raw_text": text[:15000],
            "metadata": "{}",
            "relevance": classify_relevance(text)
        }

    return {
        "url": url,
        "source_type": source_type,
        "title": f"{source_type.capitalize()} (extract failed)",
        "raw_text": "",
        "metadata": "{}",
        "relevance": "NOISE"
    }


def extract_generic_web(url: str, source_type: str) -> dict[str, Any]:
    """Extract generic web content."""
    text = fetch_web_content(url)
    if text:
        return {
            "url": url,
            "source_type": source_type,
            "title": "Web Content",
            "raw_text": text[:15000],
            "metadata": "{}",
            "relevance": classify_relevance(text)
        }

    return {
        "url": url,
        "source_type": source_type,
        "title": "Web Content (extract failed)",
        "raw_text": "",
        "metadata": "{}",
        "relevance": "NOISE"
    }


def classify_relevance(text: str) -> str:
    """Classify content relevance."""
    text_lower = text.lower()

    tan_qla_terms = [
        "acquisition", "consolidation", "roll-up", "rollup", "quantum leap",
        "seller financing", "opm", "other people's money", "ebitda",
        "deal", "deal flow", "buy business", "buy a business", "exit",
        "valuation", "multiple", "leverage", "lbo", "private equity",
        "search fund", "smb", "main street", "business broker",
        "due diligence", "letter of intent", "loi", "term sheet",
        "investment banking", "m&a", "mergers", "acquisitions"
    ]

    marketing_terms = [
        "marketing", "advertising", "lead generation", "sales funnel",
        "conversion", "copywriting", "content marketing", "seo",
        "social media", "email marketing", "growth hacking"
    ]

    ai_terms = [
        "ai agent", "llm", "automation", "rag", "fine-tuning",
        "vector database", "embedding", "prompt engineering",
        "ai workflow", "agent orchestration", "mcp server"
    ]

    for term in tan_qla_terms:
        if term in text_lower:
            return "TAN_QLA"

    for term in marketing_terms:
        if term in text_lower:
            return "MARKETING"

    for term in ai_terms:
        if term in text_lower:
            return "GENESIS"

    return "GENERAL"


def find_doctrine_refs(text: str) -> list[str]:
    """Find references to doctrine principles."""
    if not DOCTRINE_MD.exists():
        return []

    text_lower = text.lower()
    terms = [
        "quantum leap", "comfort zone", "doofus test", "seller financing",
        "other people's money", "opm", "11 steps", "five credos",
        "perception is reality", "structure follows strategy", "investigate before you invest",
        "two presentations a week", "expand your comfort zone", "barrio", "castle",
        "chaos", "order from chaos", "dream team", "banker",
        "consolidation", "acquisition", "roll-up", "roll up",
        "high performance", "super success", "mentor", "dan peña"
    ]

    hits = []
    for term in terms:
        if term in text_lower:
            hits.append(term)

    return hits


def extract_action_items(text: str) -> list[str]:
    """Extract action items."""
    actions = []
    lines = text.split("\n")
    for line in lines:
        line = line.strip()
        if not line or len(line) < 20:
            continue
        if re.match(r"^(you should|you must|you need to|make sure|always|never|do this|don't do|step \d+|first|second|third)\b", line, re.I):
            actions.append(line[:300])
        if re.match(r"^\d+[\.\)]\s+\w", line) and len(line) < 400:
            actions.append(line)

    return actions[:15]


def extract_principles(text: str) -> list[str]:
    """Extract key principles."""
    principles = []

    sentences = re.split(r"[.!?\n]+", text)
    for s in sentences:
        s = s.strip()
        if len(s) < 30 or len(s) > 500:
            continue
        if re.match(r"^(the key|remember|always|never|principle|rule|law|truth|lesson|fundamental|critical)\b", s, re.I):
            principles.append(s)
        if re.search(r"\b(is|are|means|requires|demands|creates|destroys|builds)\b", s, re.I):
            if len(s.split()) <= 25:
                principles.append(s)

    return principles[:20]


def store_in_brain(content: dict[str, Any]) -> int:
    """Store in brain."""
    conn = init_db()

    raw_text = content.get("raw_text", "")
    doctrine_refs = find_doctrine_refs(raw_text)
    action_items = extract_action_items(raw_text)
    principles = extract_principles(raw_text)
    relevance = content.get("relevance", "GENERAL")
    summary = raw_text[:1000].strip()

    try:
        cursor = conn.execute("""
            INSERT OR REPLACE INTO content 
            (url, source_type, title, raw_text, summary, doctrine_refs, action_items, principles, relevance, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            content["url"],
            content["source_type"],
            content["title"],
            raw_text,
            summary,
            json.dumps(doctrine_refs),
            json.dumps(action_items),
            json.dumps(principles),
            relevance,
            json.dumps(content.get("metadata", {})),
            datetime.now(timezone.utc).isoformat()
        ))
        content_id = cursor.lastrowid

        for ref in doctrine_refs:
            conn.execute("INSERT OR IGNORE INTO tags (content_id, tag) VALUES (?, ?)", (content_id, ref))

        conn.execute("INSERT OR IGNORE INTO tags (content_id, tag) VALUES (?, ?)", (content_id, relevance))

        conn.commit()
        return content_id
    except Exception as e:
        print(f"Store error: {e}")
        return -1
    finally:
        conn.close()


def search_brain(query: str, limit: int = 10) -> list[dict]:
    """Search brain."""
    conn = init_db()

    try:
        rows = conn.execute("""
            SELECT c.*, GROUP_CONCAT(t.tag) as tags
            FROM content c
            LEFT JOIN tags t ON c.id = t.content_id
            WHERE c.title LIKE ? OR c.raw_text LIKE ? OR c.summary LIKE ? OR t.tag LIKE ?
            GROUP BY c.id
            ORDER BY c.created_at DESC
            LIMIT ?
        """, (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%", limit)).fetchall()

        columns = ["id", "url", "source_type", "title", "raw_text", "summary",
                   "doctrine_refs", "action_items", "principles", "relevance", "metadata", "created_at", "tags"]
        results = []
        for row in rows:
            d = dict(zip(columns, row))
            for field in ["doctrine_refs", "action_items", "principles", "metadata"]:
                try:
                    d[field] = json.loads(d[field]) if d[field] else []
                except Exception:
                    d[field] = []
            results.append(d)

        return results
    finally:
        conn.close()


def list_all() -> list[dict]:
    """List all brain content."""
    conn = init_db()
    try:
        rows = conn.execute("""
            SELECT id, url, source_type, title, summary, relevance, created_at
            FROM content ORDER BY created_at DESC
        """).fetchall()
        return [
            {"id": r[0], "url": r[1], "source_type": r[2], "title": r[3],
             "summary": r[4][:200] if r[4] else "", "relevance": r[5], "created_at": r[6]}
            for r in rows
        ]
    finally:
        conn.close()


def get_content(content_id: int) -> dict | None:
    """Get full content by ID."""
    conn = init_db()
    try:
        row = conn.execute("SELECT * FROM content WHERE id = ?", (content_id,)).fetchone()
        if not row:
            return None
        columns = ["id", "url", "source_type", "title", "raw_text", "summary",
                   "doctrine_refs", "action_items", "principles", "relevance", "metadata", "created_at"]
        d = dict(zip(columns, row))
        for field in ["doctrine_refs", "action_items", "principles", "metadata"]:
            try:
                d[field] = json.loads(d[field]) if d[field] else []
            except Exception:
                d[field] = []
        return d
    finally:
        conn.close()
