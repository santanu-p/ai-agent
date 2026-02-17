import { ExecutionPolicy, PolicySimulationResult, TaskTrace } from "../types.js";
import { v4 as uuidv4 } from "uuid";

export interface PolicySimulationInput {
  policy_patch: string;
  traces: TaskTrace[];
}

function scoreTrace(trace: TaskTrace): number {
  const outcomeScore = trace.outcome === "success" ? 1 : trace.outcome === "partial" ? 0.5 : 0;
  const latencyPenalty = trace.latency_ms > 15_000 ? 0.2 : 0;
  const costPenalty = trace.token_cost > 5 ? 0.2 : 0;
  return Math.max(0, outcomeScore - latencyPenalty - costPenalty);
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
  const baselineScore = input.traces.length === 0
    ? 0.8
    : input.traces.map(scoreTrace).reduce((acc, cur) => acc + cur, 0) / input.traces.length;

  const patchBoost = input.policy_patch.length > 0 ? 0.06 : -0.02;
  const patchScore = Math.min(1, baselineScore + patchBoost);
  const projectedDelta = Number((patchScore - baselineScore).toFixed(4));

  const blockers: string[] = [];
  if (patchScore < baselineScore) {
    blockers.push("patch regresses simulated composite score");
  }
  if (patchScore < 0.7) {
    blockers.push("projected score below minimum release threshold");
  }

  return {
    simulation_id: uuidv4(),
    baseline_score: Number(baselineScore.toFixed(4)),
    patch_score: Number(patchScore.toFixed(4)),
    projected_delta: projectedDelta,
    blockers,
    recommendation: blockers.length === 0 ? "approve" : "reject"
  };
}

