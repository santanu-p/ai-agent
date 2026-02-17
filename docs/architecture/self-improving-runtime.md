# Self-Improving Runtime Architecture

## Goal
Define a runtime architecture where an AI system can continuously improve gameplay while preserving engine integrity, determinism, and operational safety.

## Layered Runtime Split

### 1) Immutable Core Engine Layer
The core engine is read-only at runtime and updated only through trusted human-reviewed releases.

**Scope (examples):**
- Rendering pipeline and asset streaming.
- Physics simulation and collision system.
- Save-game format and migration framework.
- Networking protocol, replication model, and anti-cheat primitives.

**Properties:**
- Versioned independently as `core_version`.
- Cryptographically signed binaries/assets.
- No direct write path from AI systems.
- Owns authoritative game state transitions for safety-critical systems.

---

### 2) Mutable AI-Authored Gameplay Layer
AI can author and evolve gameplay logic and content under strict contracts.

**Scope (examples):**
- Quest templates and progression gates.
- NPC behavior trees / utility rules.
- Economy parameters (prices, sinks, drop rates).
- Dialogue graphs and localization-ready strings.
- Procedural content rules (spawn tables, encounter composition, map modifiers).

**Properties:**
- Packaged as signed, versioned "patch bundles".
- Data-driven first; script support allowed only inside sandbox.
- Activated per environment (dev/stage/prod) with canary rollout.
- Fully reversible to a previous known-good version.

---

### 3) Sandboxed Execution Boundary
All AI-generated executable logic runs in an isolated runtime (e.g., WASM or Lua sandbox) with explicit host bindings.

**Hard restrictions:**
- No direct filesystem access.
- No direct network/socket access.
- No process/thread spawning outside approved scheduler APIs.
- No arbitrary native FFI.

**Allowed capabilities (via host API):**
- Read-only access to whitelisted gameplay context.
- Emitting intent messages/events to core engine.
- Deterministic RNG service.
- Bounded CPU/memory/time budgets.

**Enforcement controls:**
- Capability-based API surface (deny-by-default).
- Per-script resource quotas and watchdog timeouts.
- Determinism checks in lockstep/networked contexts.
- Structured audit logging for every sandbox invocation.

## Explicit Contracts

### A) Data Schemas for AI Outputs
All AI-authored artifacts must conform to machine-validated schemas.

**Required metadata envelope:**
- `patch_id` (globally unique, immutable).
- `base_patch_id` (parent lineage for diff/rollback).
- `target_core_version` (compatibility pin).
- `schema_version` (for parser evolution).
- `author` (`ai/<model-id>` plus optional human approver).
- `created_at` (UTC timestamp).
- `content_hash` (integrity checksum).
- `signature` (signing authority).

**Artifact schema groups:**
1. `quest_bundle.schema.json`
   - Objective graph, prerequisites, rewards, fail states.
2. `npc_behavior.schema.json`
   - States, transitions, utility curves, action constraints.
3. `economy_tuning.schema.json`
   - Parameter ranges, confidence bands, max delta per rollout.
4. `dialogue_graph.schema.json`
   - Nodes, branches, tags, safety filters, fallback lines.
5. `procgen_rules.schema.json`
   - Rule weights, biome constraints, rarity budgets, exclusion sets.

**Contract rules:**
- Reject unknown top-level fields unless explicitly marked extensible.
- Strong typing for numeric ranges and enums.
- Referential integrity across IDs (e.g., quest reward item IDs must exist).
- Backward compatibility policy by `schema_version`.

### B) Validation Pipeline Before Activation
No AI patch can become active without passing all validation stages.

1. **Schema Validation**
   - JSON/bytecode shape validation against current schemas.
2. **Static Safety Checks**
   - Forbidden API detection, opcode/AST linting, dependency allowlist.
3. **Semantic Validation**
   - Domain rules (e.g., no negative currency generation exploit paths).
4. **Simulation & Regression**
   - Run deterministic test scenarios and gameplay simulations.
5. **Performance & Budget Checks**
   - CPU, memory, and latency budgets in sandbox stress tests.
6. **Canary Rollout**
   - Activate for a small shard/cohort; monitor SLOs and gameplay KPIs.
7. **Promotion Gate**
   - Automatic or human-in-the-loop approval based on policy.

**Activation requirement:**
- Patch transitions to `ACTIVE` only after all stages pass and signed promotion token is issued.

### C) Rollback Mechanism with Version IDs
Runtime must support immediate and deterministic rollback.

**Version model:**
- `core_version` for immutable engine.
- `patch_id` for each gameplay patch.
- `release_channel` (dev/stage/prod).
- `active_set` = ordered list of active `patch_id`s per channel.

**Rollback behavior:**
- Maintain append-only patch ledger with status transitions: `CREATED -> VALIDATED -> CANARY -> ACTIVE -> REVOKED`.
- Rollback by atomically switching `active_set` to prior snapshot (`rollback_to_patch_id` or snapshot ID).
- Preserve save compatibility through migration guards; block rollback if irreversible data mutation is detected unless explicit override policy exists.
- Emit rollback event with reason code and operator/automation identity.

### D) Runtime Kill-Switch for New AI Patches
Provide an immediate control to stop introduction of new AI-authored changes.

**Kill-switch controls:**
- `ai_patch_intake_enabled` (accept new generated patches).
- `ai_patch_activation_enabled` (allow promotion to active).
- `ai_patch_execution_enabled` (execute sandbox scripts from mutable layer).

**Operational semantics:**
- Kill-switch is globally replicated and strongly consistent.
- Changes require authenticated operator identity and are audit logged.
- Disabling intake/activation does not necessarily disable already-active safe patches.
- Emergency mode can force fallback to immutable baseline patch set only.

## Recommended Runtime Flow
1. AI generates candidate gameplay patch bundle.
2. Bundle is signed, stored, and assigned `patch_id`.
3. Validation pipeline executes and records evidence.
4. Canary activation occurs if policy permits.
5. Patch is promoted to `ACTIVE` or automatically rolled back.
6. Kill-switch can halt future patching at any point.

## Minimal API Surface (Illustrative)
- `submitPatch(bundle) -> patch_id`
- `validatePatch(patch_id) -> validation_report`
- `activatePatch(patch_id, channel) -> activation_id`
- `rollback(channel, target_snapshot_id) -> rollback_id`
- `setKillSwitch(flags) -> switch_version`
- `getRuntimeState() -> { core_version, active_set, kill_switch_flags }`

This split ensures the system can evolve rapidly in gameplay quality while keeping engine trust boundaries, operational control, and player safety intact.
