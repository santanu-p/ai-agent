export type ModelProvider = "openai" | "anthropic" | "local";

export interface RoutedModel {
  provider: ModelProvider;
  model: string;
  reason: string;
}

export function routeModel(intent: string, budget: number): RoutedModel {
  const normalizedIntent = intent.toLowerCase();

  if (normalizedIntent.includes("open world") && normalizedIntent.includes("ai")) {
    return {
      provider: "local",
      model: "aegis-openworld-ai",
      reason: "ai-only open-world simulation workload"
    };
  }

  if (normalizedIntent.includes("code") || normalizedIntent.includes("deploy")) {
    return {
      provider: "openai",
      model: "gpt-5",
      reason: "coding or deployment task"
    };
  }
  if (budget < 20) {
    return {
      provider: "local",
      model: "llama-3.1-70b",
      reason: "cost-sensitive path"
    };
  }
  return {
    provider: "anthropic",
    model: "claude-sonnet-4",
    reason: "general orchestration workload"
  };
}
