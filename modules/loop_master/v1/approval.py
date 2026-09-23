"""
Loop Master V1 — Human-in-the-Loop Approval Gates

Durable approval state machine for permission-gated actions.
Inspired by DeepCode's ApprovalService.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Dict, List, Optional


class ApprovalCategory(StrEnum):
    """Categories of actions that may require approval."""
    COMMAND = "command"
    FILE_WRITE = "file_write"
    NETWORK = "network"
    EXTERNAL_TOOL = "external_tool"
    DESTRUCTIVE = "destructive"


class ApprovalStatus(StrEnum):
    """Status of an approval request."""
    PENDING = "pending"
    APPROVED = "approved"
    APPROVED_SESSION = "approved_session"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

    @property
    def is_resolved(self) -> bool:
        return self in {
            ApprovalStatus.APPROVED,
            ApprovalStatus.APPROVED_SESSION,
            ApprovalStatus.REJECTED,
            ApprovalStatus.CANCELLED,
            ApprovalStatus.EXPIRED,
        }

    @property
    def is_approved(self) -> bool:
        return self in {ApprovalStatus.APPROVED, ApprovalStatus.APPROVED_SESSION}


@dataclass
class ApprovalRequest:
    """A single approval request."""
    id: str = field(default_factory=lambda: f"apr_{uuid.uuid4().hex[:12]}")
    loop_id: str = ""
    run_id: str = ""
    category: ApprovalCategory = ApprovalCategory.COMMAND
    tool_name: str = ""
    arguments: Dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    status: ApprovalStatus = ApprovalStatus.PENDING
    decision: Optional[Dict[str, Any]] = None
    requested_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None
    expires_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "loop_id": self.loop_id,
            "run_id": self.run_id,
            "category": self.category.value,
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "reason": self.reason,
            "status": self.status.value,
            "decision": self.decision,
            "requested_at": self.requested_at,
            "resolved_at": self.resolved_at,
            "expires_at": self.expires_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ApprovalRequest":
        data["category"] = ApprovalCategory(data.get("category", "command"))
        data["status"] = ApprovalStatus(data.get("status", "pending"))
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at and self.status == ApprovalStatus.PENDING

    @property
    def age_seconds(self) -> float:
        return time.time() - self.requested_at


@dataclass
class ApprovalGrant:
    """A durable grant for a specific tool within a loop session."""
    loop_id: str = ""
    tool_name: str = ""
    source_approval_id: str = ""
    granted_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "loop_id": self.loop_id,
            "tool_name": self.tool_name,
            "source_approval_id": self.source_approval_id,
            "granted_at": self.granted_at,
        }


class ApprovalService:
    """
    Manages human-in-the-loop approval gates.
    
    Creates, resolves, and expires permission-gated tool calls.
    Tracks session-scoped grants to avoid repeated approvals.
    """

    STORAGE_PATH = os.path.expanduser("~/tan-executive/loop_master/v1/approvals.json")

    def __init__(self, default_timeout_seconds: float = 300.0):
        self._requests: Dict[str, ApprovalRequest] = {}
        self._grants: Dict[str, ApprovalGrant] = {}  # f"{loop_id}:{tool_name}" -> grant
        self._default_timeout = default_timeout_seconds
        self._load()

    def _load(self):
        if os.path.exists(self.STORAGE_PATH):
            try:
                with open(self.STORAGE_PATH, "r") as f:
                    data = json.load(f)
                for adata in data.get("requests", []):
                    req = ApprovalRequest.from_dict(adata)
                    self._requests[req.id] = req
                for gdata in data.get("grants", []):
                    grant = ApprovalGrant(**gdata)
                    key = f"{grant.loop_id}:{grant.tool_name}"
                    self._grants[key] = grant
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        os.makedirs(os.path.dirname(self.STORAGE_PATH), exist_ok=True)
        with open(self.STORAGE_PATH, "w") as f:
            json.dump({
                "requests": [r.to_dict() for r in self._requests.values()],
                "grants": [g.to_dict() for g in self._grants.values()],
                "saved_at": datetime.now(timezone.utc).isoformat()
            }, f, indent=2, default=str)

    def request(
        self,
        loop_id: str,
        run_id: str,
        category: ApprovalCategory,
        tool_name: str,
        arguments: Dict[str, Any],
        reason: str = "",
        timeout_seconds: Optional[float] = None,
    ) -> ApprovalRequest:
        """Create a new approval request."""
        # Check if already granted for this session
        if self.is_granted(loop_id, tool_name):
            # Auto-approve
            req = ApprovalRequest(
                loop_id=loop_id,
                run_id=run_id,
                category=category,
                tool_name=tool_name,
                arguments=arguments,
                reason=reason,
                status=ApprovalStatus.APPROVED,
                metadata={"auto_approved": True},
            )
            req.resolved_at = time.time()
            self._requests[req.id] = req
            self._save()
            return req

        # Create pending request
        now = time.time()
        timeout = timeout_seconds or self._default_timeout
        req = ApprovalRequest(
            loop_id=loop_id,
            run_id=run_id,
            category=category,
            tool_name=tool_name,
            arguments=arguments,
            reason=reason,
            expires_at=now + timeout,
        )
        self._requests[req.id] = req
        self._save()
        return req

    def resolve(
        self,
        approval_id: str,
        approved: bool,
        session_wide: bool = False,
        reason: str = "",
    ) -> Optional[ApprovalRequest]:
        """Resolve an approval request."""
        req = self._requests.get(approval_id)
        if req is None:
            return None

        if req.status.is_resolved:
            return req

        now = time.time()
        req.resolved_at = now
        req.decision = {
            "approved": approved,
            "session_wide": session_wide,
            "reason": reason,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
        }

        if approved:
            req.status = ApprovalStatus.APPROVED_SESSION if session_wide else ApprovalStatus.APPROVED
            # Create grant if session-wide
            if session_wide:
                grant = ApprovalGrant(
                    loop_id=req.loop_id,
                    tool_name=req.tool_name,
                    source_approval_id=req.id,
                )
                key = f"{req.loop_id}:{req.tool_name}"
                self._grants[key] = grant
        else:
            req.status = ApprovalStatus.REJECTED

        self._save()
        return req

    def cancel(self, approval_id: str) -> Optional[ApprovalRequest]:
        """Cancel a pending approval request."""
        req = self._requests.get(approval_id)
        if req is None or req.status.is_resolved:
            return None

        req.status = ApprovalStatus.CANCELLED
        req.resolved_at = time.time()
        self._save()
        return req

    def expire_pending(self) -> List[ApprovalRequest]:
        """Expire all pending requests past their timeout."""
        expired: List[ApprovalRequest] = []
        now = time.time()
        
        for req in self._requests.values():
            if req.status == ApprovalStatus.PENDING and req.expires_at and now > req.expires_at:
                req.status = ApprovalStatus.EXPIRED
                req.resolved_at = now
                expired.append(req)
        
        if expired:
            self._save()
        return expired

    def is_granted(self, loop_id: str, tool_name: str) -> bool:
        """Check if a tool is already granted for this loop."""
        key = f"{loop_id}:{tool_name}"
        return key in self._grants

    def get_request(self, approval_id: str) -> Optional[ApprovalRequest]:
        return self._requests.get(approval_id)

    def list_pending(self) -> List[ApprovalRequest]:
        """List all pending approvals."""
        self.expire_pending()  # Clean up first
        return [r for r in self._requests.values() if r.status == ApprovalStatus.PENDING]

    def list_all(self, loop_id: Optional[str] = None) -> List[ApprovalRequest]:
        """List all approval requests, optionally filtered by loop."""
        requests = list(self._requests.values())
        if loop_id:
            requests = [r for r in requests if r.loop_id == loop_id]
        return sorted(requests, key=lambda r: r.requested_at, reverse=True)

    def get_grants(self, loop_id: str) -> List[ApprovalGrant]:
        """Get all grants for a loop."""
        return [g for g in self._grants.values() if g.loop_id == loop_id]

    def revoke_grant(self, loop_id: str, tool_name: str) -> bool:
        """Revoke a session-wide grant."""
        key = f"{loop_id}:{tool_name}"
        if key in self._grants:
            del self._grants[key]
            self._save()
            return True
        return False

    def get_status(self) -> Dict[str, Any]:
        """Get approval service status."""
        self.expire_pending()
        total = len(self._requests)
        pending = sum(1 for r in self._requests.values() if r.status == ApprovalStatus.PENDING)
        approved = sum(1 for r in self._requests.values() if r.status.is_approved)
        rejected = sum(1 for r in self._requests.values() if r.status == ApprovalStatus.REJECTED)
        expired = sum(1 for r in self._requests.values() if r.status == ApprovalStatus.EXPIRED)
        
        return {
            "total_requests": total,
            "pending": pending,
            "approved": approved,
            "rejected": rejected,
            "expired": expired,
            "active_grants": len(self._grants),
            "default_timeout_seconds": self._default_timeout,
        }


def get_approval_service() -> ApprovalService:
    """Get the global approval service instance."""
    if not hasattr(get_approval_service, "_instance"):
        get_approval_service._instance = ApprovalService()
    return get_approval_service._instance
