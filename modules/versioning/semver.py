"""Semantic version tracking for the Executive Agent system.

Every change increments the version number by 0.01.
V0.01 → V0.02 → V0.03 ...
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

VERSIONS_DB = Path.home() / "tan-executive" / "versions" / "versions.db"


def _db() -> sqlite3.Connection:
    VERSIONS_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(VERSIONS_DB))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS semver (
            id INTEGER PRIMARY KEY,
            version TEXT NOT NULL,
            changes TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    return conn


def current_version() -> str:
    """Get the current semantic version."""
    conn = _db()
    row = conn.execute("SELECT version FROM semver ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    return row[0] if row else "V0.00"


def bump_version(change_description: str) -> str:
    """Bump version by 0.01 and record the change."""
    current = current_version()
    # Parse V0.XX
    num = int(current.replace("V", "").replace(".", ""))
    new_num = num + 1
    new_version = f"V{new_num // 100:01d}.{new_num % 100:02d}"
    
    conn = _db()
    conn.execute(
        "INSERT INTO semver (version, changes, created_at) VALUES (?, ?, ?)",
        (new_version, change_description, datetime.now(timezone.utc).isoformat())
    )
    conn.commit()
    conn.close()
    return new_version


def version_history() -> list[dict]:
    """Get full version history."""
    conn = _db()
    rows = conn.execute("SELECT version, changes, created_at FROM semver ORDER BY id ASC").fetchall()
    conn.close()
    return [{"version": r[0], "changes": r[1], "timestamp": r[2]} for r in rows]


def record_version_change(from_ver: str, to_ver: str, change: str) -> None:
    """Record a version change with from/to tracking."""
    conn = _db()
    conn.execute(
        "INSERT INTO semver (version, changes, created_at) VALUES (?, ?, ?)",
        (to_ver, f"{from_ver} → {to_ver}: {change}", datetime.now(timezone.utc).isoformat())
    )
    conn.commit()
    conn.close()
