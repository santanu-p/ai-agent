# Self-Improving Runtime Architecture

## Purpose
This document defines a runtime architecture that allows AI-authored gameplay updates while preserving safety, determinism, and operator control.

---

## Layer Split

### 1) Immutable Core Engine Layer
The **core engine** is read-only at runtime and may only be updated through a normal trusted release process.

**Scope (non-exhaustive):**
- Rendering pipeline
- Physics simulation and collision system
- Save format and serialization compatibility rules
- Networking protocol and replication model
- Input system, memory allocator, scheduler, and platform abstraction

**Properties:**
- Versioned independently (e.g., `engine_version = 2.4.1`)
- No dynamic patching from AI outputs
- Provides stable APIs/host functions to gameplay layer

---

### 2) Mutable AI-Authored Gameplay Layer
The **gameplay layer** is data + scripted logic that may be generated or tuned by AI and activated at runtime after validation.

**Scope (non-exhaustive):**
- Quest definitions, branching objectives, and rewards
- NPC behavior trees/state machines and dialogue policies
- Economy parameters (prices, drop rates, sinks/sources)
- Dialogue content and localization-ready text assets
- Procedural content rules (spawn tables, generation constraints)

**Properties:**
- Delivered as signed patch bundles (e.g., `patch_id`, `parent_patch_id`, manifest)
- Strictly bound to schema and sandbox constraints
- Can be rolled forward/backward without modifying engine binaries

---

### 3) Sandboxed Execution Boundary
All AI-generated executable logic runs inside a **sandbox VM** (e.g., WASM or Lua sandbox).

**Hard restrictions:**
- No direct filesystem access
- No direct network socket access
- No process/thread spawning or shell execution
- No arbitrary native FFI

**Allowed interactions:**
- Host-provided deterministic API surface only (e.g., query entity state, enqueue gameplay events, request RNG from deterministic source)
- Bounded memory, instruction/time budgets, and per-tick quotas

**Enforcement mechanisms:**
- Capability-based host function exports
- Runtime fuel metering / instruction counters
- Wall-clock watchdog timeouts
- Memory limits and object count caps
- Structured logs for every sandbox fault/termination

---

## Explicit Contracts

## A) Data Schemas for AI Outputs
All AI outputs must conform to versioned schemas.

### Contract envelope
```json
{
  "schema_version": "1.0.0",
  "patch_id": "patch-2026-02-16-001",
  "parent_patch_id": "patch-2026-02-15-019",
  "created_at": "2026-02-16T10:23:00Z",
  "engine_compat": ">=2.4.0 <2.5.0",
  "author": { "type": "ai", "model": "...", "run_id": "..." },
  "content": {
    "quests": [],
    "npc_behaviors": [],
    "economy_tuning": {},
    "dialogue": [],
    "procgen_rules": [],
    "scripts": []
  },
  "signature": "base64-ed25519-signature"
}
```

### Schema requirements
- JSON Schema (or Protobuf/FlatBuffers with equivalent strict validation) must be versioned and immutable after publication.
- Unknown fields are rejected (or explicitly quarantined under `extensions`).
- Each domain object has:
  - Stable ID
  - Semantic version
  - Deterministic constraints (bounds, enums, references)
  - Optional migration hints from prior versions

### Example domain constraints
- Economy multipliers in bounded range (e.g., `0.25..4.0`)
- NPC action graphs must be acyclic where required
- Dialogue tokens must pass profanity/safety filters and localization placeholders validation
- Procedural rules must include hard caps (spawn counts, area density, recursion depth)

---

## B) Validation Pipeline Before Activation
No patch is activated directly from generation output. Activation requires passing every stage below:

1. **Integrity & authenticity checks**
   - Verify bundle hash and signature
   - Verify `parent_patch_id` lineage and monotonic version policy

2. **Schema and compatibility validation**
   - Validate against exact `schema_version`
   - Check `engine_compat` against current immutable engine version

3. **Static safety checks**
   - Script bytecode/module inspection (imports, forbidden opcodes/APIs)
   - Content policy linting (toxicity, banned terms, unsafe prompts)
   - Referential integrity checks across quests/NPC/items

4. **Determinism and budget checks**
   - Execute deterministic replay tests using fixed seeds
   - Verify performance budgets (tick time, memory, allocation counts)

5. **Simulation and canary stage**
   - Run in isolated shadow simulation or canary shard
   - Monitor regressions: crash rate, economy drift, quest completion anomalies

6. **Policy gate + activation**
   - Require policy decision (`auto` threshold or human approval)
   - Activate atomically with version pointer switch

If any stage fails, patch status is set to `rejected` with machine-readable reasons.

---

## C) Rollback Mechanism with Version IDs
Runtime tracks active gameplay versions via immutable IDs.

### Required version metadata
- `patch_id` (current)
- `parent_patch_id` (lineage)
- `activated_at`
- `activation_scope` (global, shard, cohort)
- `rollback_target_id`

### Rollback behavior
- Maintain an append-only activation ledger.
- Store prior N known-good patch bundles locally (and in durable remote storage).
- Rollback is a single atomic pointer update to prior known-good `patch_id`.
- Existing in-flight sessions:
  - Option A: sticky to old patch until session boundary
  - Option B: migrate using declared migration rules and compatibility checks
- Rollback event emits audit logs and operator alert.

### SLO target
- Recovery objective: rollback command to full effect in < 60 seconds for all online shards.

---

## D) Runtime Kill-Switch for New AI Patches
Provide a kill-switch that disables activation of newly generated/received AI patches without stopping the game service.

### Kill-switch requirements
- Global flag (e.g., `ai_patch_ingest_enabled=false`) configurable at runtime.
- When off:
  - New patch ingestion/activation is blocked.
  - Last active approved patch remains running.
  - Validation jobs may continue in dry-run mode (optional).
- Accessible via:
  - Secure admin API
  - Ops console control
  - Emergency config override at process start
- Changes must be audited with actor identity, timestamp, and reason.

### Fail-safe defaults
- On control-plane outage or config inconsistency, default to **deny new patch activation**.
- Manual override requires privileged role and MFA-backed action path.

---

## Recommended Operational Model
- Treat AI patching as **content deployment**, not engine deployment.
- Use staged rollout percentages (1% → 10% → 50% → 100%).
- Continuously monitor KPIs tied to gameplay integrity and player safety.
- Auto-rollback on threshold breaches (crash rate, economy inflation, moderation incidents).

## Minimal Runtime State Machine
`draft -> validated -> canary -> approved -> active -> superseded`

Terminal states:
- `rejected`
- `rolled_back`

Each transition must be logged with actor, reason, and evidence links.
