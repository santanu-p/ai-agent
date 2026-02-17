# Self-Improvement Safety and Governance

## Purpose

This document defines mandatory safeguards for all AI-driven self-improvement or balance updates.

## Non-Negotiable Constraints

1. **No save corruption**: Any change that risks persistence incompatibility or data loss is automatically rejected.
2. **No pay-to-win drift**: Any change that materially increases monetization-linked power is automatically rejected.
3. **No unfair hidden nerfs**: Any player-impacting nerf must be transparent, documented, and fairness-reviewed.

## Objective Specification

All optimization must jointly balance:

- **Retention**
- **Challenge quality**
- **Fairness**
- **Performance**

Hard floors are enforced per objective, so retention gains cannot bypass fairness or runtime guarantees.

## Human Approval Gates (Required)

Human approval is mandatory before deployment for any change touching high-risk categories:

- Economy rewrites
- Combat balance swings
- Persistence migrations

## Human Override

A designated human operator may override an AI recommendation only with:

- Written rationale
- Scope-bounded rollback plan
- Timestamped approval record

## Emergency Stop

A global emergency stop must be available to disable AI-driven live tuning immediately when severe risk is detected.

Minimum expectations:

- One-step operator trigger
- Safe fallback configuration
- Verification that autonomous updates have halted

## Incident Response

If a harmful AI-driven change reaches users:

1. Trigger emergency stop.
2. Roll back to last known-good configuration.
3. Preserve logs and audit artifacts.
4. Open an incident report with timeline, impact, root cause, and corrective actions.
5. Add/expand red-team tests to prevent recurrence.

## Red-Team Testing Requirements

Every release candidate must run red-team scenarios covering:

- Exploit generation
- Griefing enablement
- Economy abuse and market manipulation

Any unresolved critical/high finding blocks release until mitigated and re-tested.
