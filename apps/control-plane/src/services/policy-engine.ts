import {
  ExecutionPolicy,
  PolicyDimensionScore,
  PolicyPatchMetadata,
  PolicyScoreDimension,
  PolicySimulationResult,
  TaskTrace
} from "../types.js";
import { v4 as uuidv4 } from "uuid";

export interface PolicySimulationInput {
  policy_patch: PolicyPatchMetadata;
  traces: TaskTrace[];
}

const NON_NEGOTIABLE_CONSTRAINTS = [
  "safety.no_save_corruption",
  "product.no_pay_to_win_drift",
  "fairness.no_hidden_nerfs"
] as const;

const MINIMUM_RELEASE_THRESHOLD = 0.7;
const DIMENSION_WEIGHTS: Record<PolicyScoreDimension, number> = {
  fairness: 0.25,
  latency: 0.2,
  exploit_risk: 0.2,
  economy_stability: 0.2,
  reliability: 0.15
};

function clampScore(value: number): number {
  return Math.max(0, Math.min(1, value));
}

function toFixedScore(value: number): number {
  return Number(clampScore(value).toFixed(4));
}

function average(values: number[]): number {
  return values.length === 0 ? 0 : values.reduce((acc, cur) => acc + cur, 0) / values.length;
}

function baselineDimensionScores(traces: TaskTrace[]): Record<PolicyScoreDimension, number> {
  if (traces.length === 0) {
    return {
      fairness: 0.8,
      latency: 0.8,
      exploit_risk: 0.8,
      economy_stability: 0.8,
      reliability: 0.8
    };
  }

  const successRate = average(
    traces.map((trace) => (trace.outcome === "success" ? 1 : trace.outcome === "partial" ? 0.5 : 0))
  );

  const latencyScore = average(
    traces.map((trace) => {
      if (trace.latency_ms <= 2_000) return 1;
      if (trace.latency_ms <= 6_000) return 0.9;
      if (trace.latency_ms <= 15_000) return 0.75;
      return 0.55;
    })
  );

  const exploitRiskScore = average(
    traces.map((trace) => {
      const dangerousToolWeight = trace.tool_calls.filter((tool) => /exec|shell|network|write/i.test(tool)).length;
      return clampScore(0.95 - dangerousToolWeight * 0.08);
    })
  );

  const economyStabilityScore = average(
    traces.map((trace) => clampScore(1 - trace.token_cost / 10))
  );

  const reliabilityScore = average(
    traces.map((trace) => {
      if (trace.outcome === "failure") return 0.35;
      if (trace.outcome === "partial") return 0.65;
      if (trace.steps.length > 8) return 0.8;
      return 0.95;
    })
  );

  const fairnessScore = clampScore(successRate * 0.8 + reliabilityScore * 0.2);

  return {
    fairness: fairnessScore,
    latency: latencyScore,
    exploit_risk: exploitRiskScore,
    economy_stability: economyStabilityScore,
    reliability: reliabilityScore
  };
}

function weightedComposite(scores: Record<PolicyScoreDimension, number>): number {
  return (Object.keys(DIMENSION_WEIGHTS) as PolicyScoreDimension[]).reduce(
    (acc, dimension) => acc + scores[dimension] * DIMENSION_WEIGHTS[dimension],
    0
  );
}

function validateNonNegotiables(policyPatch: PolicyPatchMetadata): string[] {
  const asserted = new Set(policyPatch.asserted_constraint_ids);
  return NON_NEGOTIABLE_CONSTRAINTS.filter((constraintId) => !asserted.has(constraintId));
}

function computePatchScores(
  baselineScores: Record<PolicyScoreDimension, number>,
  objectiveImpacts: Partial<Record<PolicyScoreDimension, number>>
): Record<PolicyScoreDimension, number> {
  return (Object.keys(DIMENSION_WEIGHTS) as PolicyScoreDimension[]).reduce(
    (scores, dimension) => {
      const impact = objectiveImpacts[dimension] ?? 0;
      scores[dimension] = clampScore(baselineScores[dimension] + impact);
      return scores;
    },
    {} as Record<PolicyScoreDimension, number>
  );
}

function buildDimensionScores(
  baselineScores: Record<PolicyScoreDimension, number>,
  patchScores: Record<PolicyScoreDimension, number>
): Record<PolicyScoreDimension, PolicyDimensionScore> {
  return (Object.keys(DIMENSION_WEIGHTS) as PolicyScoreDimension[]).reduce(
    (scores, dimension) => {
      const baseline = toFixedScore(baselineScores[dimension]);
      const patch = toFixedScore(patchScores[dimension]);
      scores[dimension] = {
        baseline,
        patch,
        delta: Number((patch - baseline).toFixed(4)),
        weight: DIMENSION_WEIGHTS[dimension]
      };
      return scores;
    },
    {} as Record<PolicyScoreDimension, PolicyDimensionScore>
  );
}

export function enforcePolicy(policy: ExecutionPolicy): { allowed: boolean; reasons: string[] } {
  const reasons: string[] = [];

  if (policy.resource_limits.max_runtime_seconds > 7200) {
    reasons.push("max_runtime_seconds exceeds guardrail limit");
  }
  if (policy.tool_allowances.length === 0) {
    reasons.push("at least one tool must be allowed");
  }
  if (!["internal", "internet"].includes(policy.network_scope)) {
    reasons.push("invalid network scope");
  }

  return {
    allowed: reasons.length === 0,
    reasons
  };
}

export function simulatePolicyPatch(input: PolicySimulationInput): PolicySimulationResult {
  const baselineDimension = baselineDimensionScores(input.traces);
  const patchDimension = computePatchScores(baselineDimension, input.policy_patch.objective_impacts);

  const baselineScore = weightedComposite(baselineDimension);
  const patchScore = weightedComposite(patchDimension);
  const projectedDelta = Number((patchScore - baselineScore).toFixed(4));

  const violatedConstraints = validateNonNegotiables(input.policy_patch);
  const blockers: string[] = [];

  if (projectedDelta < 0) {
    blockers.push("patch regresses simulated composite score");
  }
  if (patchScore < MINIMUM_RELEASE_THRESHOLD) {
    blockers.push("projected score below minimum release threshold");
  }
  if (violatedConstraints.length > 0) {
    blockers.push(`non-negotiable constraint violations: ${violatedConstraints.join(", ")}`);
  }

  return {
    simulation_id: uuidv4(),
    baseline_score: Number(baselineScore.toFixed(4)),
    patch_score: Number(patchScore.toFixed(4)),
    projected_delta: projectedDelta,
    dimension_scores: buildDimensionScores(baselineDimension, patchDimension),
    violated_constraints: violatedConstraints,
    blockers,
    recommendation: blockers.length === 0 ? "approve" : "reject"
  };
}
