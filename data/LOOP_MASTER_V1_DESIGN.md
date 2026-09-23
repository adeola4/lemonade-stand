# Loop Master V1 — Production-Grade Architecture Design

**Version:** 1.0.0
**Date:** 2026-09-17
**Author:** TAN/Black Hole (Hermes Agent)
**Sources:** HKUDS/DeepCode, tommypj/agent-orchestrator

---

## 1. Architecture Overview

Loop Master V1 is a production-grade autonomous loop engine that manages hundreds of concurrent loops with full lifecycle control, budget guardrails, human-in-the-loop approval gates, and evidence-driven verification.

### Core Principles
1. **Immutable state snapshots** — never mutate in place
2. **Bounded loops** — every loop has max_iterations, max_tokens, max_wall_time
3. **Evidence chains** — every completion has verifiable evidence refs
4. **Human gates for destructive actions** — approval service for high-risk ops
5. **Compaction with legal boundaries** — never split tool-call pairs
6. **Cross-process safety** — file leases, epochs, heartbeats
7. **Graceful degradation** — orphaned work recovery, dead worker detection

---

## 2. Loop Lifecycle State Machine

### States
```
PENDING → PLANNING → EXECUTING → VERIFYING → COMPLETED | FAILED | PAUSED
```

### State Transitions
| From | To | Trigger |
|------|----|---------|
| PENDING | PLANNING | `loop-v1-start` command |
| PLANNING | EXECUTING | Plan approved (auto or human) |
| PLANNING | PAUSED | Human pause |
| EXECUTING | VERIFYING | Execution completed, awaiting verification |
| EXECUTING | FAILED | Error or budget exceeded |
| EXECUTING | PAUSED | Human pause |
| VERIFYING | COMPLETED | Verification passed |
| VERIFYING | EXECUTING | Verification failed, retry |
| VERIFYING | FAILED | Max retries exceeded |
| PAUSED | PLANNING | `loop-v1-start` resume |
| * | FAILED | Terminal error |

### State Properties
- `is_terminal`: COMPLETED, FAILED
- `can_pause`: PLANNING, EXECUTING
- `can_resume`: PAUSED
- `needs_human`: PLANNING (if requires_approval), VERIFYING (if verification fails)

---

## 3. Harness Layer

### Per-Loop Scoping
Each loop execution runs in an isolated harness with:
- **Budget guardrails**: max_tokens, max_wall_time, max_iterations
- **Filesystem scope**: workspace-only or unrestricted
- **Network scope**: allowed domains, blocked domains
- **Tool scope**: which tools are available to this loop
- **Context window**: max context size before compaction

### Budget Admission
Before a loop starts:
1. Check if estimated cost < remaining budget
2. Check if loop is not exceeding concurrency cap
3. Check if system resources are available
4. If all checks pass, admit and start

### Token Metering
- Track tokens used per loop iteration
- Track cumulative tokens per loop
- Track global token budget
- Trigger compaction at 90% of context window

---

## 4. Session Persistence

### Storage Model
```
~/tan-executive/loop_master/
├── loops.json              # Loop definitions
├── sessions/
│   ├── {session_id}.json   # Session state
│   └── {session_id}_history.json  # Compacted history
├── approvals.json          # Pending approvals
├── evidence/
│   └── {loop_id}/
│       └── {run_id}.json   # Evidence for each run
└── budget.json             # Budget ledger
```

### Compaction Strategy
- **Trigger**: at 90% of context budget
- **Method**: TailRetainingCompactionStrategy
  - Replace old history with summary checkpoint
  - Keep recent tail verbatim (60K chars)
  - Never split tool-call pairs
- **Summary prompt**: "Include EVERY file/command by name"
- **Summary prefix**: "This is your own earlier conversation, compacted..."

### Session Recovery
- Sessions persist across restarts
- On load, restore last known state
- If session was executing, mark as FAILED with reason "restart_during_execution"
- Orphaned work detection via heartbeat timeout

---

## 5. Scheduler

### Cron Scheduling
- Full 5-field cron: minute, hour, day-of-month, month, day-of-week
- Supports: `*`, ranges, steps, lists
- POSIX dom/dow rule
- Timezone-aware
- Minute-level dedup (no double-fire)

### Concurrency Control
- Global max concurrent loops (default: 10)
- Per-loop max concurrent runs (default: 1)
- Priority-based preemption for CRITICAL loops

### Retry with Backoff
- Exponential backoff: `base_delay * 2^attempt`
- Max attempts: 3 (configurable)
- Transient failures only (not logic errors)

---

## 6. Human-in-the-Loop Approval Gates

### Approval Categories
- COMMAND: Shell commands
- FILE_WRITE: File modifications
- NETWORK: External network calls
- EXTERNAL_TOOL: Third-party tool invocations
- DESTRUCTIVE: Irreversible operations

### Approval Flow
1. Loop attempts action that requires approval
2. Action is PENDING in approval queue
3. Human reviews via `loop-v1-approve` command
4. If APPROVED: action proceeds, grant recorded for session
5. If DENIED: action blocked, loop continues with alternative
6. If EXPIRED: action auto-denied after timeout

### Approval Grants
- Thread-scoped (per-loop)
- Cannot widen policy
- Cannot bypass deny
- Recorded for audit trail

---

## 7. Evidence-Driven Verification

### Evidence Model
```json
{
  "item_id": "item_abc123",
  "turn_id": "turn_def456",
  "kind": "tool_call|file_change|test_result|artifact",
  "status": "success|failure|skipped",
  "summary": "Brief description of what was done"
}
```

### Completion Certificate
```json
{
  "loop_id": "loop_xyz",
  "run_id": "run_abc",
  ​​"status": "completed|failed",
  "evidence": [...],
  "reason": "Human-readable completion reason",
  "budget_remaining": 0.95,
  "turns_used": 12,
  "tokens_used": 45000,
  "duration_seconds": 120,
  "verified_by": "verifier_agent_id",
  "verified_at": "2026-09-17T12:00:00Z"
}
```

### Verification Process
1. Loop execution completes
2. Verifier agent reviews evidence
3. If evidence supports completion claim → COMPLETED
4. If evidence insufficient → back to EXECUTING for retry
5. If max retries exceeded → FAILED

---

## 8. Multi-Agent Orchestration

### Agent Roles
1. **Goal-Setter**: Defines what the loop should achieve
2. **Planner**: Breaks goal into executable steps
3. **Executor**: Runs each step, collects evidence
4. **Verifier**: Independently verifies completion

### Role Interaction
```
Goal-Setter → defines goal + completion criteria
     ↓
Planner → creates plan with steps
     ↓
Executor → runs steps, collects evidence
     ↓
Verifier → reviews evidence, certifies completion
     ↓
COMPLETED or back to Planner for retry
```

---

## 9. CLI Commands (V1)

| Command | Description |
|---------|-------------|
| `loop-v1-create` | Create goal-driven loop with completion criteria |
| `loop-v1-start` | Start loop with harness + budget |
| `loop-v1-status` | Show session state + evidence |
| `loop-v1-approve` | Approve/reject pending gates |
| `loop-v1-verify` | Manual verification trigger |
| `loop-v1-sessions` | List active sessions with history |
| `loop-v1-compact` | Manual context compaction |
| `loop-v1-budget` | Show budget status |
| `loop-v1-evidence` | Show evidence for a loop run |

---

## 10. Dashboard Sections (V1)

1. **Stats Bar**: Total loops, running, paused, failed, budget remaining
2. **Loop List**: All loops with status, priority, budget
3. **Sessions Panel**: Active sessions with history, compaction status
4. **Evidence Panel**: Recent evidence, verification status
5. **Budget Panel**: Token usage, cost tracking, budget remaining
6. **Approval Queue**: Pending human decisions
7. **Scheduler Panel**: Cron schedules, next fire times

---

## 11. Backward Compatibility

All existing V0.32 commands continue to work:
- `loop-master status|list|create|get|update|delete|start|stop|pause|freeze|resume|run-now`
- `loop-gen`, `loop-adaptive`, `loop-deps`, `loop-notify`, `loop-heal`, `loop-metrics`, `loop-templates`, `loop-scheduler`, `loop-resources`

V1 commands are additive and do not conflict with V0.32.

---

## 12. Integration with QLA Methodology

- **Knowledge Brain**: Loop goals reference QLA knowledge base
- **2979 Peña Action Items**: Loops can be created from action items
- **Deal Sourcing**: Loops monitor deal flow and trigger outreach
- **Paperworkman**: Loops generate documents from templates
- **Executive Loop**: V1 engine powers the executive loop iterations

---

## 13. File Structure

```
modules/loop_master/
├── __init__.py              # Updated exports
├── engine.py                # V0.32 engine (backward compat)
├── v1/
│   ├── __init__.py          # V1 exports
│   ├── state_machine.py     # Loop lifecycle state machine
│   ├── harness.py           # Per-loop scoping + budget
│   ├── session.py           # Session persistence + compaction
│   ├── scheduler.py         # Cron + concurrency control
│   ├── approval.py          # Human-in-the-loop gates
│   ├── evidence.py          # Evidence-driven verification
│   ├── budget.py            # Budget guardrails
│   ├── agents.py            # Multi-agent orchestration
│   └── cli.py               # V1 CLI commands
├── cli_handler.py           # V0.32 CLI (backward compat)
├── module_commands.py       # V0.32 module commands
└── ...existing modules...
```

---

## 14. Implementation Priority

1. **Phase 1**: State machine + harness + budget (core)
2. **Phase 2**: Session persistence + compaction
3. **Phase 3**: Scheduler + concurrency control
4. **Phase 4**: Approval gates + evidence verification
5. **Phase 5**: Multi-agent orchestration
6. **Phase 6**: CLI + dashboard integration
