export type ModelProvider = "openai" | "anthropic" | "local";

export interface RoutedModel {
  provider: ModelProvider;
  model: string;
  reason: string;
}

export function routeModel(intent: string, budget: number): RoutedModel {
  if (intent.toLowerCase().includes("code") || intent.toLowerCase().includes("deploy")) {
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

