import { v4 as uuidv4 } from "uuid";
import { GoalRun, GoalSpec, TaskTrace } from "../types.js";
import { buildDomainExecution } from "./domain-packs.js";
import { routeGoal } from "./goal-router.js";
import { routeModel } from "./model-router.js";

export function createGoalRun(goal: GoalSpec): GoalRun {
  return {
    goal_id: goal.goal_id,
    status: "queued",
    risk_score: goal.risk_tolerance === "high" ? 0.8 : goal.risk_tolerance === "medium" ? 0.5 : 0.3,
    estimated_cost: Number((goal.budget * 0.65).toFixed(2)),
    traces: [],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  };
}

export function executeGoal(goal: GoalSpec): TaskTrace {
  const routed = routeGoal(goal);
  const model = routeModel(goal.intent, goal.budget);
  const domainPlan = buildDomainExecution(routed.primary_domain, goal.intent);

  return {
    trace_id: uuidv4(),
    goal_id: goal.goal_id,
    steps: [
      `goal routed to ${routed.primary_domain}`,
      ...domainPlan.execution_plan,
      `model selected: ${model.provider}/${model.model}`
    ],
    tool_calls: [
      "tool.registry.lookup",
      "tool.runtime.dispatch",
      "tool.observability.log"
    ],
    model_calls: [`${model.provider}:${model.model}`],
    latency_ms: 4_200,
    token_cost: 1.4,
    outcome: "success"
  };
}

