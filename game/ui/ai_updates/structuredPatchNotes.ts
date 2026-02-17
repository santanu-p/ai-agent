import { MetricDelta, StructuredUpdateMetadata } from "./types";

function asSignedPercent(previous: number, current: number): string {
  if (previous === 0) {
    return "n/a";
  }

  const pct = ((current - previous) / previous) * 100;
  const sign = pct > 0 ? "+" : "";
  return `${sign}${pct.toFixed(1)}%`;
}

function formatDelta(metric: MetricDelta): string {
  const trend = asSignedPercent(metric.previous, metric.current);
  const targetSuffix = metric.objective
    ? ` (target ${metric.objective.target}${metric.objective.unit ?? ""})`
    : "";

  return `${metric.metric}: ${metric.previous} → ${metric.current} (${trend})${targetSuffix}`;
}

/**
 * Patch notes are generated from structured metadata (changes + metrics),
 * never from raw model output.
 */
export function buildConcisePatchNotes(metadata: StructuredUpdateMetadata): string[] {
  const changeNotes = metadata.changes.map(
    (change) => `• [${change.category}] ${change.title}: ${change.summary}`,
  );

  const topDeltas = metadata.metricDeltas.slice(0, 3).map((delta) => `• ${formatDelta(delta)}`);

  return [...changeNotes, ...topDeltas];
}
