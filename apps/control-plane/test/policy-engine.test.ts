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

  test("approves policy patch when objective dimensions improve without constraint violations", () => {
    const result = simulatePolicyPatch({
      policy_patch: {
        summary: "Tune scheduler fairness and reduce exploit surface",
        asserted_constraint_ids: [
          "safety.no_save_corruption",
          "product.no_pay_to_win_drift",
          "fairness.no_hidden_nerfs"
        ],
        objective_impacts: {
          fairness: 0.08,
          latency: 0.03,
          exploit_risk: 0.04,
          economy_stability: 0.02,
          reliability: 0.05
        }
      },
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
    expect(result.projected_delta).toBeGreaterThan(0);
    expect(result.violated_constraints).toEqual([]);
    expect(result.dimension_scores.fairness.delta).toBeGreaterThan(0);
  });

  test("rejects policy patch when non-negotiable constraints are violated despite score gains", () => {
    const result = simulatePolicyPatch({
      policy_patch: {
        summary: "Aggressive optimization patch",
        asserted_constraint_ids: ["safety.no_save_corruption"],
        objective_impacts: {
          fairness: 0.05,
          latency: 0.07,
          exploit_risk: 0.06,
          economy_stability: 0.04,
          reliability: 0.05
        }
      },
      traces: [
        {
          trace_id: "t2",
          goal_id: "g2",
          steps: ["a", "b"],
          tool_calls: ["tool1"],
          model_calls: ["m1"],
          latency_ms: 1800,
          token_cost: 2.5,
          outcome: "success"
        }
      ]
    });

    expect(result.projected_delta).toBeGreaterThan(0);
    expect(result.violated_constraints).toEqual([
      "product.no_pay_to_win_drift",
      "fairness.no_hidden_nerfs"
    ]);
    expect(result.recommendation).toBe("reject");
    expect(result.blockers.join(" ")).toContain("non-negotiable constraint violations");
  });
});
