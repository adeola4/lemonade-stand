"""
Loop Master V1 — Session Persistence + Compaction

Durable sessions with context compaction.
Inspired by DeepCode's compaction strategy and session runtime.
"""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


COMPACT_TRIGGER_FRACTION = 0.9
COMPACT_KEEP_CHARS = 60000
SUMMARIZATION_PROMPT = (
    "You are performing a CONTEXT CHECKPOINT COMPACTION. Create a handoff "
    "summary for another agent that will resume this task.\n\n"
    "The conversation above is about to be replaced by your summary. "
    "Anything you leave out is gone: the next agent cannot look it up.\n\n"
    "Include:\n"
    "- Every file read or written and every command run, BY NAME\n"
    "- Current progress and key decisions made\n"
    "- Important context, constraints, or user preferences\n"
    "- What remains to be done (clear next steps)\n"
    "- Any critical data, examples, file paths, or references\n\n"
    "Be concise and structured, but never drop a concrete name to save room."
)
SUMMARY_PREFIX = (
    "This is your own earlier conversation, compacted into a summary because "
    "it no longer fits in context. Everything below is a record of what you "
    "already did in THIS session — treat it exactly as you would treat the "
    "messages it replaced. Summary:"
)


@dataclass
class SessionMessage:
    """A single message in a session."""
    role: str  # user, assistant, tool, system
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tool_name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tokens: int = 0

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "tool_name": self.tool_name,
            "tool_call_id": self.tool_call_id,
            "tokens": self.tokens,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SessionMessage":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Session:
    """A durable session for loop execution."""
    id: str = field(default_factory=lambda: f"sess_{uuid.uuid4().hex[:12]}")
    loop_id: str = ""
    run_id: str = ""
    messages: List[SessionMessage] = field(default_factory=list)
    compacted_summaries: List[Dict[str, Any]] = field(default_factory=list)
    total_tokens: int = 0
    total_turns: int = 0
    compaction_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_compaction_at: Optional[str] = None
    status: str = "active"  # active, compacted, closed
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "loop_id": self.loop_id,
            "run_id": self.run_id,
            "messages": [m.to_dict() for m in self.messages],
            "compacted_summaries": self.compacted_summaries,
            "total_tokens": self.total_tokens,
            "total_turns": self.total_turns,
            "compaction_count": self.compaction_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_compaction_at": self.last_compaction_at,
            "status": self.status,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        messages = [SessionMessage.from_dict(m) for m in data.get("messages", [])]
        return cls(
            id=data.get("id", f"sess_{uuid.uuid4().hex[:12]}"),
            loop_id=data.get("loop_id", ""),
            run_id=data.get("run_id", ""),
            messages=messages,
            compacted_summaries=data.get("compacted_summaries", []),
            total_tokens=data.get("total_tokens", 0),
            total_turns=data.get("total_turns", 0),
            compaction_count=data.get("compaction_count", 0),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            updated_at=data.get("updated_at", datetime.now(timezone.utc).isoformat()),
            last_compaction_at=data.get("last_compaction_at"),
            status=data.get("status", "active"),
            metadata=data.get("metadata", {}),
        )

    @property
    def message_count(self) -> int:
        return len(self.messages)

    @property
    def context_chars(self) -> int:
        return sum(len(m.content) for m in self.messages)

    def add_message(self, role: str, content: str, tool_name: str = None, tokens: int = 0) -> SessionMessage:
        """Add a message to the session."""
        msg = SessionMessage(
            role=role,
            content=content,
            tool_name=tool_name,
            tokens=tokens,
        )
        self.messages.append(msg)
        self.total_tokens += tokens
        if role == "assistant":
            self.total_turns += 1
        self.updated_at = datetime.now(timezone.utc).isoformat()
        return msg

    def get_history(self, max_messages: int = 100) -> List[Dict[str, Any]]:
        """Get conversation history, respecting compaction."""
        history = []
        
        # Add summaries from previous compactions
        for summary in self.compacted_summaries:
            history.append({
                "role": "system",
                "content": f"{SUMMARY_PREFIX}\n\n{summary.get('text', '')}",
                "timestamp": summary.get("created_at"),
            })
        
        # Add recent messages
        recent = self.messages[-max_messages:]
        for msg in recent:
            history.append(msg.to_dict())
        
        return history

    def compact(self, summary_text: str) -> Dict[str, Any]:
        """
        Compact the session history.
        Keeps recent tail verbatim, replaces old history with summary.
        """
        # Calculate how many messages to keep (recent tail)
        keep_chars = COMPACT_KEEP_CHARS
        kept_messages: List[SessionMessage] = []
        current_chars = 0
        
        for msg in reversed(self.messages):
            msg_chars = len(msg.content)
            if current_chars + msg_chars > keep_chars:
                break
            kept_messages.insert(0, msg)
            current_chars += msg_chars
        
        # Record the compaction
        compaction_record = {
            "compaction_number": self.compaction_count + 1,
            "text": summary_text,
            "messages_replaced": len(self.messages) - len(kept_messages),
            "messages_kept": len(kept_messages),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.compacted_summaries.append(compaction_record)
        self.messages = kept_messages
        self.compaction_count += 1
        self.last_compaction_at = datetime.now(timezone.utc).isoformat()
        self.updated_at = datetime.now(timezone.utc).isoformat()
        
        return compaction_record

    def needs_compaction(self, max_context_chars: int) -> bool:
        """Check if session needs compaction."""
        return self.context_chars >= (max_context_chars * COMPACT_TRIGGER_FRACTION)


class CompactionStrategy:
    """Strategy for context compaction."""

    @staticmethod
    def tail_retaining(messages: List[SessionMessage], summary: str, keep_chars: int = COMPACT_KEEP_CHARS) -> List[SessionMessage]:
        """Keep recent tail verbatim, replace rest with summary."""
        kept: List[SessionMessage] = []
        current_chars = 0
        
        for msg in reversed(messages):
            msg_chars = len(msg.content)
            if current_chars + msg_chars > keep_chars:
                break
            kept.insert(0, msg)
            current_chars += msg_chars
        
        return kept

    @staticmethod
    def summarize_and_prune(messages: List[SessionMessage], summary: str, keep_chars: int = COMPACT_KEEP_CHARS) -> List[SessionMessage]:
        """Summarize old messages, keep recent tail."""
        # Same as tail_retaining for now — summarization requires LLM call
        return CompactionStrategy.tail_retaining(messages, summary, keep_chars)


class SessionStore:
    """Persistent storage for sessions."""

    STORAGE_PATH = os.path.expanduser("~/tan-executive/loop_master/v1/sessions.json")

    def __init__(self):
        self.sessions: Dict[str, Session] = {}
        self._load()

    def _load(self):
        if os.path.exists(self.STORAGE_PATH):
            try:
                with open(self.STORAGE_PATH, "r") as f:
                    data = json.load(f)
                for sid, sdata in data.get("sessions", {}).items():
                    self.sessions[sid] = Session.from_dict(sdata)
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        os.makedirs(os.path.dirname(self.STORAGE_PATH), exist_ok=True)
        with open(self.STORAGE_PATH, "w") as f:
            json.dump({
                "sessions": {sid: s.to_dict() for sid, s in self.sessions.items()},
                "saved_at": datetime.now(timezone.utc).isoformat()
            }, f, indent=2, default=str)

    def create(self, loop_id: str, run_id: str) -> Session:
        """Create a new session."""
        session = Session(loop_id=loop_id, run_id=run_id)
        self.sessions[session.id] = session
        self._save()
        return session

    def get(self, session_id: str) -> Optional[Session]:
        return self.sessions.get(session_id)

    def list_for_loop(self, loop_id: str) -> List[Session]:
        return [s for s in self.sessions.values() if s.loop_id == loop_id]

    def list_active(self) -> List[Session]:
        return [s for s in self.sessions.values() if s.status == "active"]

    def update(self, session: Session) -> Session:
        session.updated_at = datetime.now(timezone.utc).isoformat()
        self.sessions[session.id] = session
        self._save()
        return session

    def close(self, session_id: str) -> Optional[Session]:
        session = self.sessions.get(session_id)
        if session:
            session.status = "closed"
            session.updated_at = datetime.now(timezone.utc).isoformat()
            self._save()
        return session

    def get_stats(self) -> Dict[str, Any]:
        """Get session statistics."""
        total = len(self.sessions)
        active = sum(1 for s in self.sessions.values() if s.status == "active")
        compacted = sum(1 for s in self.sessions.values() if s.status == "compacted")
        closed = sum(1 for s in self.sessions.values() if s.status == "closed")
        total_compactions = sum(s.compaction_count for s in self.sessions.values())
        total_messages = sum(s.message_count for s in self.sessions.values())
        
        return {
            "total_sessions": total,
            "active": active,
            "compacted": compacted,
            "closed": closed,
            "total_compactions": total_compactions,
            "total_messages": total_messages,
        }


def get_session_store() -> SessionStore:
    """Get the global session store instance."""
    if not hasattr(get_session_store, "_instance"):
        get_session_store._instance = SessionStore()
    return get_session_store._instance
