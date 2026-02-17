import Fastify from "fastify";
import cors from "@fastify/cors";
import swagger from "@fastify/swagger";
import swaggerUi from "@fastify/swagger-ui";
import { v4 as uuidv4 } from "uuid";
import { store } from "./store.js";
import {
  AgentExecuteSchema,
  AgentProfileSchema,
  ChangeSetCreateSchema,
  DomainProjectSchema,
  GoalSpecSchema,
  PolicySimulationSchema
} from "./schemas.js";
import { createGoalRun, executeGoal } from "./services/orchestrator.js";
import { enforcePolicy, simulatePolicyPatch } from "./services/policy-engine.js";
import { SecurityIncident } from "./types.js";
import {
  createChangeSet,
  evaluateCanary,
  promoteChangeSet
} from "./services/deployment-controller.js";

interface RuntimeDispatchResponse {
  trace: {
    trace_id: string;
    goal_id: string;
    steps: string[];
    tool_calls: string[];
    model_calls: string[];
    latency_ms: number;
    token_cost: number;
    outcome: string;
  };
  reflections: Array<{
    reflection_id: string;
    failure_class: string;
    root_cause: string;
    counterfactual: string;
    policy_patch: string;
    memory_patch: string;
  }>;
  memory_entries: Record<string, string[]>;
}

interface SecurityPlaneIncident {
  incident_id: string;
  signal_set: string[];
  severity: "low" | "medium" | "high" | "critical";
  blast_radius: "host" | "service" | "region" | "global";
  auto_actions: string[];
  verification_state: "pending" | "in_progress" | "completed" | "failed";
}

async function dispatchRuntime(agentId: string, payload: {
  intent: string;
  goal_id: string;
  domains: string[];
  policy: unknown;
}): Promise<RuntimeDispatchResponse | null> {
  const runtimeUrl = process.env.RUNTIME_PLANE_URL ?? "http://localhost:8101";
  const deadline = new Date(Date.now() + 86_400_000).toISOString();
  const body = {
    goal: {
      goal_id: payload.goal_id,
      intent: payload.intent,
      constraints: [],
      budget: 100,
      deadline,
      risk_tolerance: "medium",
      domains: payload.domains
    },
    policy: payload.policy,
    max_iterations: 2
  };

  try {
    const response = await fetch(`${runtimeUrl}/v1/runtime/execute`, {
      method: "POST",
      headers: { "content-type": "application/json", "x-agent-id": agentId },
      body: JSON.stringify(body)
    });
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as RuntimeDispatchResponse;
  } catch {
    return null;
  }
}

async function fetchSecurityIncidents(): Promise<SecurityPlaneIncident[]> {
  const securityUrl = process.env.SECURITY_PLANE_URL ?? "http://localhost:8103";
  try {
    const response = await fetch(`${securityUrl}/v1/security/incidents`);
    if (!response.ok) {
      return [];
    }
    const parsed = (await response.json()) as { incidents: SecurityPlaneIncident[] };
    return parsed.incidents;
  } catch {
    return [];
  }
}

async function ingestSecurityIncident(): Promise<SecurityPlaneIncident | null> {
  const securityUrl = process.env.SECURITY_PLANE_URL ?? "http://localhost:8103";
  try {
    const response = await fetch(`${securityUrl}/v1/security/incidents/ingest`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        signal_set: ["guardduty anomalous-api-call", "waf burst"],
        source: "control-plane-seed",
        metadata: { seeded: "true" }
      })
    });
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as SecurityPlaneIncident;
  } catch {
    return null;
  }
}

async function evaluateWithLearningPlane(
  baselineScore: number,
  candidateScore: number
): Promise<{ recommendation: string; reasons: string[]; projected_delta: number } | null> {
  const learningUrl = process.env.LEARNING_PLANE_URL ?? "http://localhost:8102";
  try {
    const response = await fetch(`${learningUrl}/v1/learning/evaluate-patch`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        baseline_score: baselineScore,
        candidate_score: candidateScore,
        observed_p95_latency_ms: 9000,
        error_budget_remaining: 0.8
      })
    });
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as { recommendation: string; reasons: string[]; projected_delta: number };
  } catch {
    return null;
  }
}

export function createApp() {
  const app = Fastify({ logger: true });

  app.register(cors, { origin: true });
  app.register(swagger, {
    openapi: {
      info: {
        title: "AegisWorld Control Plane API",
        version: "0.1.0"
      }
    }
  });
  app.register(swaggerUi, {
    routePrefix: "/docs"
  });

  app.get("/healthz", async () => ({ status: "ok", service: "control-plane" }));

  app.post("/v1/goals", async (request, reply) => {
    const parsed = GoalSpecSchema.safeParse(request.body);
    if (!parsed.success) {
      return reply.status(400).send({ error: parsed.error.flatten() });
    }

    const run = createGoalRun(parsed.data);
    const trace = executeGoal(parsed.data);
    run.status = "completed";
    run.traces.push(trace);
    run.updated_at = new Date().toISOString();
    store.putGoal(run);

    return reply.status(201).send(run);
  });

  app.get("/v1/goals/:goalId", async (request, reply) => {
    const goalId = (request.params as { goalId: string }).goalId;
    const run = store.getGoal(goalId);
    if (!run) {
      return reply.status(404).send({ error: "goal not found" });
    }
    return run;
  });

  app.post("/v1/agents", async (request, reply) => {
    const parsed = AgentProfileSchema.safeParse(request.body);
    if (!parsed.success) {
      return reply.status(400).send({ error: parsed.error.flatten() });
    }

    const profile = {
      ...parsed.data,
      created_at: new Date().toISOString()
    };
    store.putAgent(profile);
    store.appendMemory(profile.agent_id, `agent ${profile.name} created`);
    return reply.status(201).send(profile);
  });

  app.post("/v1/agents/:agentId/execute", async (request, reply) => {
    const agentId = (request.params as { agentId: string }).agentId;
    const agent = store.getAgent(agentId);
    if (!agent) {
      return reply.status(404).send({ error: "agent not found" });
    }

    const parsed = AgentExecuteSchema.safeParse(request.body);
    if (!parsed.success) {
      return reply.status(400).send({ error: parsed.error.flatten() });
    }

    const policyResult = enforcePolicy(parsed.data.policy);
    if (!policyResult.allowed) {
      return reply.status(422).send({ error: "policy denied", reasons: policyResult.reasons });
    }

    const runtime = await dispatchRuntime(agentId, {
      intent: parsed.data.intent,
      goal_id: parsed.data.goal_id,
      domains: agent.domains,
      policy: parsed.data.policy
    });

    store.appendMemory(
      agentId,
      `executed intent "${parsed.data.intent}" for goal ${parsed.data.goal_id}`
    );
    return {
      agent_id: agentId,
      goal_id: parsed.data.goal_id,
      status: runtime ? "completed" : "accepted",
      dispatch: "runtime-plane",
      policy_check: "passed",
      runtime_result: runtime
    };
  });

  app.get("/v1/agents/:agentId/memory", async (request, reply) => {
    const agentId = (request.params as { agentId: string }).agentId;
    const agent = store.getAgent(agentId);
    if (!agent) {
      return reply.status(404).send({ error: "agent not found" });
    }
    return {
      agent_id: agentId,
      entries: store.getMemories(agentId)
    };
  });

  app.post("/v1/domain/social/projects", async (request, reply) => {
    const parsed = DomainProjectSchema.safeParse(request.body);
    if (!parsed.success) {
      return reply.status(400).send({ error: parsed.error.flatten() });
    }
    return reply.status(201).send({
      project_id: uuidv4(),
      domain: "social",
      project_name: parsed.data.project_name,
      workflow: ["campaign-planning", "asset-generation", "publishing", "analytics"],
      status: "scheduled"
    });
  });

  app.post("/v1/domain/games/projects", async (request, reply) => {
    const parsed = DomainProjectSchema.safeParse(request.body);
    if (!parsed.success) {
      return reply.status(400).send({ error: parsed.error.flatten() });
    }
    return reply.status(201).send({
      project_id: uuidv4(),
      domain: "games",
      project_name: parsed.data.project_name,
      workflow: ["sim-agent-runs", "telemetry-analysis", "balance-patch", "release-candidate"],
      status: "scheduled"
    });
  });

  app.post("/v1/domain/dev/pipelines", async (request, reply) => {
    const parsed = DomainProjectSchema.safeParse(request.body);
    if (!parsed.success) {
      return reply.status(400).send({ error: parsed.error.flatten() });
    }
    return reply.status(201).send({
      pipeline_id: uuidv4(),
      domain: "dev",
      project_name: parsed.data.project_name,
      stages: ["plan", "code", "test", "deploy", "progressive-rollout"],
      status: "queued"
    });
  });

  app.get("/v1/incidents", async () => {
    const remoteIncidents = await fetchSecurityIncidents();
    return {
      incidents: [...store.listIncidents(), ...remoteIncidents]
    };
  });

  app.post("/v1/incidents/_seed", async () => {
    const seeded: SecurityIncident = {
      incident_id: uuidv4(),
      signal_set: ["guardduty:anomalous-api-call", "waf:blocked-burst"],
      severity: "high",
      blast_radius: "service",
      auto_actions: ["rotate-credentials", "quarantine-workload"],
      verification_state: "completed"
    };
    store.putIncident(seeded);
    const remote = await ingestSecurityIncident();
    return { local: seeded, remote };
  });

  app.post("/v1/policies/simulate", async (request, reply) => {
    const parsed = PolicySimulationSchema.safeParse(request.body);
    if (!parsed.success) {
      return reply.status(400).send({ error: parsed.error.flatten() });
    }
    const local = simulatePolicyPatch(parsed.data);
    const learning = await evaluateWithLearningPlane(local.baseline_score, local.patch_score);
    return {
      local,
      learning
    };
  });

  app.post("/v1/deployments/changesets", async (request, reply) => {
    const parsed = ChangeSetCreateSchema.safeParse(request.body);
    if (!parsed.success) {
      return reply.status(400).send({ error: parsed.error.flatten() });
    }

    const staged = createChangeSet(parsed.data.target, parsed.data.diff, parsed.data.risk_score);
    const canaryEvaluated = evaluateCanary(staged);
    store.putChangeSet(canaryEvaluated);
    return reply.status(201).send(canaryEvaluated);
  });

  app.post("/v1/deployments/changesets/:changeId/promote", async (request, reply) => {
    const changeId = (request.params as { changeId: string }).changeId;
    const existing = store.getChangeSet(changeId);
    if (!existing) {
      return reply.status(404).send({ error: "changeset not found" });
    }

    const promoted = promoteChangeSet(existing);
    store.putChangeSet(promoted);
    return promoted;
  });

  app.get("/v1/deployments/changesets", async () => {
    return { changesets: store.listChangeSets() };
  });

  return app;
}
