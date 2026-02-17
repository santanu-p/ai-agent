import { describe, expect, test } from "vitest";

import { routeModel } from "../src/services/model-router.js";

describe("model router", () => {
  test("routes AI-only open-world intent to local open-world model", () => {
    const result = routeModel("improve the model it should behave like an open world but only for ai", 50);

    expect(result).toEqual({
      provider: "local",
      model: "aegis-openworld-ai",
      reason: "ai-only open-world simulation workload"
    });
  });

  test("routes code intent to gpt-5", () => {
    const result = routeModel("deploy code changes", 50);
    expect(result.model).toBe("gpt-5");
  });
});

