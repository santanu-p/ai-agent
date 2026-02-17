export const sampleAiUpdateMetadata = {
  version: "ai-update-2026.02.16",
  versionLabel: "AI Update 2026.02.16",
  deployedAt: "2026-02-16T11:30:00Z",
  preferences: {
    stableOnly: false,
    personalizedUpdatesOptOut: false,
  },
  changes: [
    {
      category: "quests",
      summary: "Reduced escort quest pathing stalls in crowded hubs.",
      metricDelta: {
        metric: "quest_completion_rate",
        delta: 0.072,
      },
      objectiveTarget: {
        metric: "quest_abandon_rate",
        operator: "<=",
        value: "11%",
      },
    },
    {
      category: "balance",
      summary: "Adjusted late-game healer mana scaling to reduce burst dominance.",
      metricDelta: {
        metric: "class_win_rate_variance",
        delta: -0.041,
      },
      objectiveTarget: {
        metric: "match_duration",
        operator: "between",
        value: "14-18m",
      },
    },
    {
      category: "npc_behavior",
      summary: "Improved civilian panic response to avoid doorway clustering.",
      metricDelta: {
        metric: "navigation_failures",
        delta: -0.183,
      },
      objectiveTarget: {
        metric: "city_performance_fps",
        operator: ">=",
        value: "58",
      },
    },
  ],
};
