"""Version control and change management for the executive agent system.

Every change — ingested content, new skills, modified workflows — is tracked,
backed up, and reversible. Nothing is ever truly deleted; old versions are
preserved for restore.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSIONS_DB = Path.home() / "tan-executive" / "versions" / "versions.db"
BACKUPS_ROOT = Path.home() / "tan-executive" / "backups"
ROOT = Path.home() / ".hermes" / "skills" / "tan-executive-agent"


def init_db() -> sqlite3.Connection:
    """Initialize versions database."""
    VERSIONS_DB.parent.mkdir(parents=True, exist_ok=True)
    BACKUPS_ROOT.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(VERSIONS_DB))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS versions (
            id INTEGER PRIMARY KEY,
            timestamp TEXT,
            description TEXT,
            change_type TEXT,
            target_path TEXT,
            backup_path TEXT,
            content_before TEXT,
            content_after TEXT,
            metadata TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY,
            timestamp TEXT,
            description TEXT,
            manifest TEXT
        )
    """)
    conn.commit()
    return conn


def file_hash(path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    if not path.exists():
        return ""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def file_tree_manifest(root: Path) -> dict[str, str]:
    """Build a manifest of all files with their hashes."""
    manifest = {}
    for p in root.rglob("*"):
        if p.is_file() and ".git" not in str(p):
            try:
                rel = str(p.relative_to(root))
                manifest[rel] = file_hash(p)
            except Exception:
                pass
    return manifest


def create_snapshot(description: str) -> int:
    """Create a full snapshot of the current system state."""
    init_db()
    manifest = file_tree_manifest(ROOT)
    ts = datetime.now(timezone.utc).isoformat()

    # Backup all files
    backup_dir = BACKUPS_ROOT / ts.replace(":", "-")
    backup_dir.mkdir(parents=True, exist_ok=True)
    for rel_path in manifest:
        src = ROOT / rel_path
        dst = backup_dir / rel_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(str(src), str(dst))
        except Exception:
            pass

    # Store snapshot record
    conn = init_db()
    cursor = conn.execute(
        "INSERT INTO snapshots (timestamp, description, manifest) VALUES (?, ?, ?)",
        (ts, description, json.dumps(manifest, indent=2))
    )
    conn.commit()
    snap_id = cursor.lastrowid
    conn.close()
    return snap_id


def file_backed_up(target: Path, version_id: int) -> str | None:
    """Backup a single file before modification. Returns path to backup."""
    if not target.exists():
        return None
    backup_dir = BACKUPS_ROOT / f"v{version_id}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    rel = str(target.relative_to(ROOT)) if str(target).startswith(str(ROOT)) else str(target)
    backup_path = backup_dir / rel.replace("/", "__")
    try:
        shutil.copy2(str(target), str(backup_path))
        return str(backup_path)
    except Exception:
        return None


def record_change(
    change_type: str,
    target: Path,
    description: str,
    content_before: str = "",
    content_after: str = "",
    metadata: dict | None = None,
    do_backup: bool = True,
) -> int:
    """Record a change and optionally backup the target file first."""
    conn = init_db()
    ts = datetime.now(timezone.utc).isoformat()
    backup_path = None

    if do_backup and target.exists():
        # Pre-backup before we modify
        backup_path = file_backed_up(target, 0)

    cursor = conn.execute("""
        INSERT INTO versions (timestamp, description, change_type, target_path,
                              backup_path, content_before, content_after, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        ts,
        description,
        change_type,
        str(target),
        backup_path,
        content_before,
        content_after,
        json.dumps(metadata or {}),
    ))
    conn.commit()
    version_id = cursor.lastrowid
    conn.close()
    return version_id


def install_or_upgrade(
    target: Path,
    new_content: str,
    change_description: str,
    metadata: dict | None = None,
) -> dict:
    """Install or upgrade a file with full versioning."""
    content_before = ""
    if target.exists():
        content_before = target.read_text(encoding="utf-8", errors="ignore")

    # Record change with backup
    vid = record_change(
        change_type="upgrade" if target.exists() else "install",
        target=target,
        description=change_description,
        content_before=content_before,
        content_after=new_content,
        metadata=metadata,
    )

    # Write new content
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(new_content, encoding="utf-8")

    return {
        "version_id": vid,
        "action": "upgraded" if content_before else "installed",
        "backup": str(BACKUPS_ROOT / f"v{vid}"),
        "target": str(target),
    }


def rollback(version_id: int) -> dict:
    """Rollback to a previous version."""
    conn = init_db()
    row = conn.execute(
        "SELECT * FROM versions WHERE id = ?", (version_id,)
    ).fetchone()

    if not row:
        conn.close()
        return {"error": f"No version {version_id} found"}

    columns = ["id", "timestamp", "description", "change_type", "target_path",
               "backup_path", "content_before", "content_after", "metadata"]
    ver = dict(zip(columns, row))

    target = Path(ver["target_path"])
    backup = ver["backup_path"]

    result = {"version_id": version_id, "target": str(target)}

    # Try backup file first
    if backup and Path(backup).exists():
        shutil.copy2(backup, target)
        result["restored_from"] = backup
    elif ver["content_before"]:
        # Fall back to recorded content
        target.write_text(ver["content_before"], encoding="utf-8")
        result["restored_from"] = "version_record"
    else:
        result["error"] = "No backup or content_before available"

    # Record the rollback
    record_change(
        change_type="rollback",
        target=target,
        description=f"Rollback to version {version_id}",
        do_backup=False,
    )

    conn.close()
    return result


def rollback_to_snapshot(snapshot_id: int) -> dict:
    """Full system rollback to a snapshot."""
    conn = init_db()
    row = conn.execute(
        "SELECT * FROM snapshots WHERE id = ?", (snapshot_id,)
    ).fetchone()

    if not row:
        conn.close()
        return {"error": f"No snapshot {snapshot_id} found"}

    ts = row[1]
    manifest = json.loads(row[3])
    backup_dir = BACKUPS_ROOT / ts.replace(":", "-")

    restored = []
    failed = []

    for rel_path in manifest:
        backup_file = backup_dir / rel_path
        target = ROOT / rel_path
        if backup_file.exists():
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(backup_file), str(target))
                restored.append(rel_path)
            except Exception as e:
                failed.append({"path": rel_path, "error": str(e)})
        else:
            failed.append({"path": rel_path, "error": "backup not found"})

    record_change(
        change_type="snapshot_rollback",
        target=ROOT,
        description=f"Full rollback to snapshot {snapshot_id} ({ts})",
        do_backup=False,
    )

    conn.close()
    return {
        "snapshot_id": snapshot_id,
        "restored": len(restored),
        "failed": failed,
    }


def list_versions(limit: int = 20) -> list[dict]:
    """List all version records."""
    conn = init_db()
    rows = conn.execute("""
        SELECT id, timestamp, description, change_type, target_path
        FROM versions ORDER BY id DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [
        {"id": r[0], "timestamp": r[1], "description": r[2], "type": r[3], "target": r[4]}
        for r in rows
    ]


def list_snapshots() -> list[dict]:
    """List all snapshots."""
    conn = init_db()
    rows = conn.execute("""
        SELECT id, timestamp, description FROM snapshots ORDER BY id DESC
    """).fetchall()
    conn.close()
    return [{"id": r[0], "timestamp": r[1], "description": r[2]} for r in rows]


def get_version(version_id: int) -> dict | None:
    """Get full version record."""
    conn = init_db()
    row = conn.execute("SELECT * FROM versions WHERE id = ?", (version_id,)).fetchone()
    conn.close()
    if not row:
        return None
    columns = ["id", "timestamp", "description", "change_type", "target_path",
               "backup_path", "content_before", "content_after", "metadata"]
    d = dict(zip(columns, row))
    try:
        d["metadata"] = json.loads(d["metadata"]) if d["metadata"] else {}
    except Exception:
        d["metadata"] = {}
    return d
