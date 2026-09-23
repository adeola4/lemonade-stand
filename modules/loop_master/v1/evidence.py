"""
Loop Master V1 — Evidence-Driven Verification

Evidence collection, completion certificates, and verification.
Inspired by DeepCode's GoalEvidence and verification loop.
"""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Dict, List, Optional


class EvidenceKind(StrEnum):
    """Types of evidence that can be collected."""
    TOOL_CALL = "tool_call"
    FILE_CHANGE = "file_change"
    COMMAND_EXECUTION = "command_execution"
    TEST_RESULT = "test_result"
    ARTIFACT = "artifact"
    CHECKPOINT = "checkpoint"
    OBSERVATION = "observation"


class VerificationStatus(StrEnum):
    """Status of verification."""
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    INCONCLUSIVE = "inconclusive"


@dataclass
class Evidence:
    """A single piece of evidence from loop execution."""
    id: str = field(default_factory=lambda: f"evd_{uuid.uuid4().hex[:12]}")
    loop_id: str = ""
    run_id: str = ""
    kind: EvidenceKind = EvidenceKind.OBSERVATION
    status: str = "success"  # success, failure, skipped
    summary: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tool_name: Optional[str] = None
    tool_call_id: Optional[str] = None
    file_path: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "loop_id": self.loop_id,
            "run_id": self.run_id,
            "kind": self.kind.value,
            "status": self.status,
            "summary": self.summary,
            "details": self.details,
            "created_at": self.created_at,
            "tool_name": self.tool_name,
            "tool_call_id": self.tool_call_id,
            "file_path": self.file_path,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Evidence":
        data["kind"] = EvidenceKind(data.get("kind", "observation"))
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class CompletionCertificate:
    """A certificate of loop completion with evidence."""
    id: str = field(default_factory=lambda: f"cert_{uuid.uuid4().hex[:12]}")
    loop_id: str = ""
    run_id: str = ""
    session_id: str = ""
    status: str = "completed"  # completed, failed
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    reason: str = ""
    budget_remaining_fraction: float = 1.0
    turns_used: int = 0
    tokens_used: int = 0
    duration_seconds: float = 0.0
    verified_by: str = "system"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    verification_status: VerificationStatus = VerificationStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "loop_id": self.loop_id,
            "run_id": self.run_id,
            "session_id": self.session_id,
            "status": self.status,
            "evidence": self.evidence,
            "reason": self.reason,
            "budget_remaining_fraction": self.budget_remaining_fraction,
            "turns_used": self.turns_used,
            "tokens_used": self.tokens_used,
            "duration_seconds": self.duration_seconds,
            "verified_by": self.verified_by,
            "created_at": self.created_at,
            "verification_status": self.verification_status.value,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CompletionCertificate":
        data["verification_status"] = VerificationStatus(data.get("verification_status", "pending"))
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class EvidenceStore:
    """Persistent storage for evidence and completion certificates."""

    STORAGE_PATH = os.path.expanduser("~/tan-executive/loop_master/v1/evidence.json")

    def __init__(self):
        self.evidence: Dict[str, Evidence] = {}
        self.certificates: Dict[str, CompletionCertificate] = {}
        self._load()

    def _load(self):
        if os.path.exists(self.STORAGE_PATH):
            try:
                with open(self.STORAGE_PATH, "r") as f:
                    data = json.load(f)
                for edata in data.get("evidence", []):
                    ev = Evidence.from_dict(edata)
                    self.evidence[ev.id] = ev
                for cdata in data.get("certificates", []):
                    cert = CompletionCertificate.from_dict(cdata)
                    self.certificates[cert.id] = cert
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        os.makedirs(os.path.dirname(self.STORAGE_PATH), exist_ok=True)
        with open(self.STORAGE_PATH, "w") as f:
            json.dump({
                "evidence": [e.to_dict() for e in self.evidence.values()],
                "certificates": [c.to_dict() for c in self.certificates.values()],
                "saved_at": datetime.now(timezone.utc).isoformat()
            }, f, indent=2, default=str)

    def add_evidence(self, evidence: Evidence) -> Evidence:
        self.evidence[evidence.id] = evidence
        self._save()
        return evidence

    def get_evidence(self, evidence_id: str) -> Optional[Evidence]:
        return self.evidence.get(evidence_id)

    def list_for_run(self, run_id: str) -> List[Evidence]:
        return [e for e in self.evidence.values() if e.run_id == run_id]

    def list_for_loop(self, loop_id: str) -> List[Evidence]:
        return [e for e in self.evidence.values() if e.loop_id == loop_id]

    def create_certificate(self, cert: CompletionCertificate) -> CompletionCertificate:
        self.certificates[cert.id] = cert
        self._save()
        return cert

    def get_certificate(self, cert_id: str) -> Optional[CompletionCertificate]:
        return self.certificates.get(cert_id)

    def list_certificates(self, loop_id: Optional[str] = None) -> List[CompletionCertificate]:
        certs = list(self.certificates.values())
        if loop_id:
            certs = [c for c in certs if c.loop_id == loop_id]
        return sorted(certs, key=lambda c: c.created_at, reverse=True)

    def verify_completion(self, loop_id: str, run_id: str) -> CompletionCertificate:
        """
        Verify a loop completion by reviewing evidence.
        Creates a completion certificate with verification status.
        """
        evidence_list = self.list_for_run(run_id)
        
        # Check if evidence supports completion
        has_successful_actions = any(
            e.status == "success" for e in evidence_list
            if e.kind in {EvidenceKind.TOOL_CALL, EvidenceKind.FILE_CHANGE, EvidenceKind.TEST_RESULT}
        )
        
        has_failures = any(
            e.status == "failure" for e in evidence_list
        )
        
        # Determine verification status
        if has_successful_actions and not has_failures:
            verification_status = VerificationStatus.PASSED
            status = "completed"
            reason = "Evidence supports successful completion"
        elif has_failures:
            verification_status = VerificationStatus.FAILED
            status = "failed"
            reason = "Evidence contains failures"
        elif len(evidence_list) == 0:
            verification_status = VerificationStatus.INCONCLUSIVE
            status = "completed"
            reason = "No evidence collected; inconclusive verification"
        else:
            verification_status = VerificationStatus.INCONCLUSIVE
            status = "completed"
            reason = "Insufficient evidence for strong verification"

        cert = CompletionCertificate(
            loop_id=loop_id,
            run_id=run_id,
            status=status,
            evidence=[e.to_dict() for e in evidence_list],
            reason=reason,
            verification_status=verification_status,
            verified_by="evidence_verifier_v1",
        )
        
        self.certificates[cert.id] = cert
        self._save()
        return cert

    def get_summary(self) -> Dict[str, Any]:
        """Get evidence summary."""
        total = len(self.evidence)
        by_kind = {}
        for ev in self.evidence.values():
            kind = ev.kind.value
            by_kind[kind] = by_kind.get(kind, 0) + 1
        
        total_certs = len(self.certificates)
        verified = sum(1 for c in self.certificates.values() if c.verification_status == VerificationStatus.PASSED)
        failed = sum(1 for c in self.certificates.values() if c.verification_status == VerificationStatus.FAILED)
        
        return {
            "total_evidence": total,
            "by_kind": by_kind,
            "total_certificates": total_certs,
            "verified": verified,
            "failed": failed,
        }


def get_evidence_store() -> EvidenceStore:
    """Get the global evidence store."""
    if not hasattr(get_evidence_store, "_instance"):
        get_evidence_store._instance = EvidenceStore()
    return get_evidence_store._instance
