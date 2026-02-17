import { describe, expect, test } from "vitest";
import { enforcePolicy, simulatePolicyPatch } from "../src/services/policy-engine.js";

describe("policy engine", () => {
  test("denies overly long runtime", () => {
    const result = enforcePolicy({
      tool_allowances: ["shell.exec"],
      resource_limits: { max_cpu: "4", max_memory: "8Gi", max_runtime_seconds: 8000 },
      network_scope: "internet",
      data_scope: "standard",
      rollback_policy: "on_failure"
    });

    expect(result.allowed).toBe(false);
  });

  test("simulates policy patch with recommendation", () => {
    const result = simulatePolicyPatch({
      policy_patch: "tighten tool choice under incident pressure",
      traces: [
        {
          trace_id: "t1",
          goal_id: "g1",
          steps: ["a"],
          tool_calls: ["tool1"],
          model_calls: ["m1"],
          latency_ms: 1200,
          token_cost: 1.2,
          outcome: "success"
        }
      ]
    });

    expect(result.recommendation).toBe("approve");
  });
});

