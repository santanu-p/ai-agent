export type UpdateCategory = "quests" | "balance" | "npc_behavior";

export interface ObjectiveTarget {
  metric: string;
  target: number;
  unit?: string;
}

export interface MetricDelta {
  metric: string;
  previous: number;
  current: number;
  objective?: ObjectiveTarget;
}

export interface ChangeEntry {
  category: UpdateCategory;
  title: string;
  summary: string;
  impactedSystems: string[];
}

export interface StructuredUpdateMetadata {
  id: string;
  deployedAtISO: string;
  changes: ChangeEntry[];
  metricDeltas: MetricDelta[];
}

export type UpdateMode = "adaptive" | "stable_only" | "opt_out";

export type FeedbackValue = "helpful" | "not_helpful";
