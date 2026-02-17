const CATEGORY_LABELS = {
  quests: "Quests",
  balance: "Balance",
  npc_behavior: "NPC behavior",
};

function formatPercentDelta(delta) {
  const sign = delta > 0 ? "+" : "";
  return `${sign}${(delta * 100).toFixed(1)}%`;
}

function formatDate(isoDate) {
  return new Date(isoDate).toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function summarizeCategory(change) {
  const label = CATEGORY_LABELS[change.category] ?? change.category;
  const metricPart = change.metricDelta
    ? `${change.metricDelta.metric}: ${formatPercentDelta(change.metricDelta.delta)}`
    : "No metric delta provided";
  const objectivePart = change.objectiveTarget
    ? `target ${change.objectiveTarget.metric} ${change.objectiveTarget.operator} ${change.objectiveTarget.value}`
    : "no objective target";

  return `${label}: ${change.summary} (${metricPart}, ${objectivePart})`;
}

export function buildPatchNotes(metadata) {
  const lines = metadata.changes.map((change) => summarizeCategory(change));
  return {
    title: metadata.versionLabel,
    deployedAt: formatDate(metadata.deployedAt),
    lines,
  };
}
