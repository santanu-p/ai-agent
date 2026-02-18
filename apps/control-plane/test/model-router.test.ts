import { describe, expect, test } from "vitest";

import { routeModel } from "../src/services/model-router.js";

function withEnv<T>(name: string, value: string | undefined, fn: () => T): T {
  const previous = process.env[name];

  if (value === undefined) {
    delete process.env[name];
  } else {
    process.env[name] = value;
  }

  try {
    return fn();
  } finally {
    if (previous === undefined) {
      delete process.env[name];
    } else {
      process.env[name] = previous;
    }
  }
}

describe("model router", () => {
  test("routes code intent to local coder model when OPENAI_API_KEY is missing", () => {
    const result = withEnv("OPENAI_API_KEY", undefined, () => routeModel("deploy code changes", 50));

    expect(result).toEqual({
      provider: "local",
      model: "qwen2.5-coder-32b-instruct",
      reason: "coding task routed to local fallback (OPENAI_API_KEY not set)"
    });
  });

  test("routes AI-only open-world intent to local open-world model", () => {
    const result = routeModel("improve the model it should behave like an open world but only for ai", 50);

    expect(result).toEqual({
      provider: "local",
      model: "aegis-openworld-ai",
      reason: "ai-only open-world simulation workload"
    });
  });

  test("routes code intent to gpt-5 when OPENAI_API_KEY is present", () => {
    const result = withEnv("OPENAI_API_KEY", "test-key", () => routeModel("deploy code changes", 50));
    expect(result.model).toBe("gpt-5");
  });

  test("routes general orchestration to local model when ANTHROPIC_API_KEY is missing", () => {
    const result = withEnv("ANTHROPIC_API_KEY", undefined, () => routeModel("plan sprint goals", 50));

    expect(result).toEqual({
      provider: "local",
      model: "glm-4.5-air",
      reason: "general orchestration workload routed locally (ANTHROPIC_API_KEY not set)"
    });
  });

  test("routes explicit open-source requests to GLM or Qwen", () => {
    expect(routeModel("use open source qwen for this task", 100).model).toBe("qwen2.5-72b-instruct");
    expect(routeModel("use glm for this task", 100).model).toBe("glm-4.5");
  });

  test("routes open-source same-time requests to ensemble", () => {
    const result = routeModel("use qwen and glm at the same time for better processing", 100);
    expect(result).toEqual({
      provider: "local",
      model: "glm-4.5 + qwen2.5-72b-instruct",
      reason: "open-source ensemble routing for higher-quality parallel reasoning"
    });
  });
});
