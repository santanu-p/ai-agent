import { z } from "zod";

export const DomainSchema = z.enum(["social", "dev", "games"]);

export const GoalSpecSchema = z.object({
  goal_id: z.string().uuid(),
  intent: z.string().min(3),
  constraints: z.array(z.string()).default([]),
  budget: z.number().positive(),
  deadline: z.string().datetime(),
  risk_tolerance: z.enum(["low", "medium", "high"]),
  domains: z.array(DomainSchema).min(1)
});

export const ExecutionPolicySchema = z.object({
  tool_allowances: z.array(z.string()).default([]),
  resource_limits: z.object({
    max_cpu: z.string().default("4"),
    max_memory: z.string().default("8Gi"),
    max_runtime_seconds: z.number().int().positive()
  }),
  network_scope: z.enum(["internal", "internet"]),
  data_scope: z.enum(["restricted", "standard", "broad"]),
  rollback_policy: z.enum(["never", "on_failure", "always"])
});

export const AgentProfileSchema = z.object({
  agent_id: z.string().uuid(),
  name: z.string().min(2),
  capabilities: z.array(z.string()).default([]),
  domains: z.array(DomainSchema).min(1)
});

export const AgentExecuteSchema = z.object({
  intent: z.string().min(3),
  goal_id: z.string().uuid(),
  policy: ExecutionPolicySchema
});

export const PolicySimulationSchema = z.object({
  policy_patch: z.string().min(1),
  traces: z.array(
    z.object({
      trace_id: z.string(),
      goal_id: z.string(),
      steps: z.array(z.string()),
      tool_calls: z.array(z.string()),
      model_calls: z.array(z.string()),
      latency_ms: z.number(),
      token_cost: z.number(),
      outcome: z.enum(["success", "partial", "failure"])
    })
  )
});

export const DomainProjectSchema = z.object({
  project_name: z.string().min(2),
  objective: z.string().min(4),
  autonomous_mode: z.boolean().default(true)
});

export const ChangeSetCreateSchema = z.object({
  target: z.string().min(2),
  diff: z.string().min(3),
  risk_score: z.number().min(0).max(1)
});
