# AI Patch Policy Enforcement

Implements `ai/policy/` checks for AI-authored patches:
- allowed-modification policy (file paths + config domains)
- forbidden API scanning
- save compatibility checks
- performance budget checks (frame-time and memory ceilings)
- prompt-injection security checks on user content

Required gates:
1. schema validation
2. static lint/type checks
3. deterministic replay validation
4. backward save-load compatibility
5. canary telemetry threshold

Any gate failure triggers auto-revert (`git reset --hard HEAD`) and quarantine record creation at `.ai_policy/quarantine/<patch_id>.json`.
