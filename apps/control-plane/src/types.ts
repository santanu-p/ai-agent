export type DomainName = "social" | "dev" | "games";

export interface GoalSpec {
  goal_id: string;
  intent: string;
  constraints: string[];
  budget: number;
  deadline: string;
  risk_tolerance: "low" | "medium" | "high";
  domains: DomainName[];
}

export interface ExecutionPolicy {
  tool_allowances: string[];
  resource_limits: {
    max_cpu: string;
    max_memory: string;
    max_runtime_seconds: number;
  };
  network_scope: "internal" | "internet";
  data_scope: "restricted" | "standard" | "broad";
  rollback_policy: "never" | "on_failure" | "always";
}

export interface TaskTrace {
  trace_id: string;
  goal_id: string;
  steps: string[];
  tool_calls: string[];
  model_calls: string[];
  latency_ms: number;
  token_cost: number;
  outcome: "success" | "partial" | "failure";
}

export interface ReflectionRecord {
  reflection_id: string;
  failure_class: string;
  root_cause: string;
  counterfactual: string;
  policy_patch: string;
  memory_patch: string;
}

export interface SecurityIncident {
  incident_id: string;
  signal_set: string[];
  severity: "low" | "medium" | "high" | "critical";
  blast_radius: "host" | "service" | "region" | "global";
  auto_actions: string[];
  verification_state: "pending" | "in_progress" | "completed" | "failed";
}

export interface AutonomousChangeSet {
  change_id: string;
  target: string;
  diff: string;
  risk_score: number;
  canary_result: "pending" | "passed" | "failed";
  promotion_state: "staged" | "progressive" | "rolled_back" | "promoted";
}

export interface AgentProfile {
  agent_id: string;
  name: string;
  capabilities: string[];
  domains: DomainName[];
  created_at: string;
}

export interface GoalRun {
  goal_id: string;
  status: "queued" | "running" | "completed" | "failed";
  risk_score: number;
  estimated_cost: number;
  traces: TaskTrace[];
  created_at: string;
  updated_at: string;
}

export interface PolicySimulationResult {
  simulation_id: string;
  baseline_score: number;
  patch_score: number;
  projected_delta: number;
  blockers: string[];
  recommendation: "approve" | "reject" | "needs_review";
}

