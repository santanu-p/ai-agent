export type ModelProvider = "openai" | "anthropic" | "local";

export interface RoutedModel {
  provider: ModelProvider;
  model: string;
  reason: string;
}

function hasCredential(value: string | undefined): boolean {
  return typeof value === "string" && value.trim().length > 0;
}

function shouldPreferLocalModel(provider: Exclude<ModelProvider, "local">): boolean {
  if (provider === "openai") {
    return !hasCredential(process.env.OPENAI_API_KEY);
  }
  return !hasCredential(process.env.ANTHROPIC_API_KEY);
}

function wantsOpenSourceRouting(normalizedIntent: string): boolean {
  return (
    normalizedIntent.includes("open source")
    || normalizedIntent.includes("opensource")
    || normalizedIntent.includes("qwen")
    || normalizedIntent.includes("glm")
  );
}

function wantsEnsembleRouting(normalizedIntent: string): boolean {
  return (
    normalizedIntent.includes("same time")
    || normalizedIntent.includes("at the same time")
    || normalizedIntent.includes("together")
    || normalizedIntent.includes("ensemble")
  );
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

  if (wantsOpenSourceRouting(normalizedIntent) && wantsEnsembleRouting(normalizedIntent)) {
    return {
      provider: "local",
      model: "glm-4.5 + qwen2.5-72b-instruct",
      reason: "open-source ensemble routing for higher-quality parallel reasoning"
    };
  }

  if (wantsOpenSourceRouting(normalizedIntent)) {
    return {
      provider: "local",
      model: normalizedIntent.includes("glm") ? "glm-4.5" : "qwen2.5-72b-instruct",
      reason: "explicit open-source model request"
    };
  }

  if (normalizedIntent.includes("code") || normalizedIntent.includes("deploy")) {
    if (shouldPreferLocalModel("openai")) {
      return {
        provider: "local",
        model: "qwen2.5-coder-32b-instruct",
        reason: "coding task routed to local fallback (OPENAI_API_KEY not set)"
      };
    }

    return {
      provider: "openai",
      model: "gpt-5",
      reason: "coding or deployment task"
    };
  }

  if (budget < 20) {
    return {
      provider: "local",
      model: "qwen2.5-14b-instruct",
      reason: "cost-sensitive path"
    };
  }

  if (shouldPreferLocalModel("anthropic")) {
    return {
      provider: "local",
      model: "glm-4.5-air",
      reason: "general orchestration workload routed locally (ANTHROPIC_API_KEY not set)"
    };
  }

  return {
    provider: "anthropic",
    model: "claude-sonnet-4",
    reason: "general orchestration workload"
  };
}
