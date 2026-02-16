# Self-Improvement Safety Playbook

This document defines mandatory controls for any AI-driven change that can affect player progression, game balance, economy, persistence, or live service reliability.

## 1) Human Override (Always Available)

- A designated human operator can block, pause, or roll back any AI-proposed change without waiting for automated consensus.
- Override controls must be available in the deployment path and in the live operations dashboard.
- AI systems must treat human override decisions as final and non-bypassable.

## 2) Emergency Stop (Kill Switch)

- Every AI-driven rollout must include a tested emergency stop that can disable further policy actions in real time.
- Emergency stop actions must:
  - Halt new AI-authored adjustments.
  - Revert to last known safe configuration.
  - Preserve forensic logs for incident analysis.
- Emergency stop activation should be executable within minutes by on-call operations staff.

## 3) Incident Response

### Trigger Conditions

Initiate incident response when any of the following occur:

- Save integrity risk (corruption, invalid migrations, irreversible loss).
- Economy instability (unexpected inflation/deflation, exploit-driven wealth concentration).
- Fairness regression (hidden nerfs, systematically worse outcomes for protected cohorts).
- Reliability degradation beyond agreed SLOs.

### Response Procedure

1. **Contain**: Trigger emergency stop and freeze additional AI rollouts.
2. **Triage**: Classify severity, scope player impact, and identify affected systems.
3. **Mitigate**: Apply rollback or compensating controls; protect player assets.
4. **Communicate**: Publish internal incident updates and external player messaging as needed.
5. **Recover**: Validate stabilization with red-team checks and guardrail metrics.
6. **Review**: Run post-incident review with corrective actions and ownership.

## 4) Mandatory High-Risk Human Approval

The following change categories require explicit human approval before production release:

- Economy rewrites.
- Combat balance swings.
- Persistence migrations.

No automated policy can self-approve these categories.

## 5) Non-Negotiable Product/Safety Rules

All AI-driven changes must comply with these hard constraints:

- **No save corruption**: never risk irreversible player data loss.
- **No pay-to-win drift**: no monetization-linked power advantages in core outcomes.
- **No unfair hidden nerfs**: no materially negative balance changes without transparent disclosure.
