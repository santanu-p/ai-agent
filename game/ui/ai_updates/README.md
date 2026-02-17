# AI Updates UI

This module renders concise in-game AI patch notes from structured metadata.

## Data contract

`createAiUpdatesPanel` expects metadata with:

- `changes[]`: category, summary, metricDelta, objectiveTarget
- `deployedAt`: ISO deployment timestamp
- `preferences`: `stableOnly` and `personalizedUpdatesOptOut`

Patch notes are generated with `buildPatchNotes(metadata)` and never display raw model output.

## Telemetry actions

Feedback and preference controls emit mapped telemetry events via `emitTelemetry`:

- `ai_updates.preference.stable_only_toggled`
- `ai_updates.preference.personalized_opt_out_toggled`
- `ai_updates.feedback.helpful`
- `ai_updates.feedback.not_helpful`
- `ai_updates.feedback.report_issue`
