import { FormEvent, useMemo, useState } from "react";

type GoalRun = {
  goal_id: string;
  status: string;
  risk_score: number;
  estimated_cost: number;
  traces: Array<{ trace_id: string; outcome: string; latency_ms: number }>;
};

type Incident = {
  incident_id: string;
  severity: string;
  signal_set: string[];
  auto_actions: string[];
  verification_state: string;
};

const apiBase = (import.meta.env.VITE_CONTROL_PLANE_URL as string) ?? "http://localhost:8100";

export function App() {
  const [goalId, setGoalId] = useState("");
  const [goalRun, setGoalRun] = useState<GoalRun | null>(null);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [error, setError] = useState("");

  const defaultPayload = useMemo(
    () => ({
      goal_id: crypto.randomUUID(),
      intent: "Create social launch campaign and deploy analytics service",
      constraints: ["stay under budget"],
      budget: 120,
      deadline: new Date(Date.now() + 86_400_000).toISOString(),
      risk_tolerance: "medium",
      domains: ["social", "dev"]
    }),
    []
  );

  async function createGoal(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const response = await fetch(`${apiBase}/v1/goals`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(defaultPayload)
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      const created = (await response.json()) as GoalRun;
      setGoalRun(created);
      setGoalId(created.goal_id);
    } catch (err) {
      setError(String(err));
    }
  }

  async function fetchGoal() {
    if (!goalId) {
      return;
    }
    setError("");
    try {
      const response = await fetch(`${apiBase}/v1/goals/${goalId}`);
      if (!response.ok) {
        throw new Error(await response.text());
      }
      setGoalRun((await response.json()) as GoalRun);
    } catch (err) {
      setError(String(err));
    }
  }

  async function refreshIncidents() {
    setError("");
    try {
      const response = await fetch(`${apiBase}/v1/incidents`);
      if (!response.ok) {
        throw new Error(await response.text());
      }
      const payload = (await response.json()) as { incidents: Incident[] };
      setIncidents(payload.incidents);
    } catch (err) {
      setError(String(err));
    }
  }

  async function seedIncident() {
    setError("");
    try {
      const response = await fetch(`${apiBase}/v1/incidents/_seed`, { method: "POST" });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      await refreshIncidents();
    } catch (err) {
      setError(String(err));
    }
  }

  return (
    <main className="layout">
      <header>
        <h1>AegisWorld Console</h1>
        <p>Control plane visibility for autonomous goal execution and incident posture.</p>
      </header>

      <section className="panel">
        <h2>Goals</h2>
        <form onSubmit={createGoal}>
          <button type="submit">Create Sample Goal</button>
        </form>
        <div className="inline">
          <input
            value={goalId}
            onChange={(e) => setGoalId(e.target.value)}
            placeholder="goal-id"
            aria-label="goal-id"
          />
          <button type="button" onClick={fetchGoal}>
            Fetch Goal
          </button>
        </div>
        {goalRun && (
          <pre>{JSON.stringify(goalRun, null, 2)}</pre>
        )}
      </section>

      <section className="panel">
        <h2>Incidents</h2>
        <div className="inline">
          <button type="button" onClick={refreshIncidents}>
            Refresh
          </button>
          <button type="button" onClick={seedIncident}>
            Seed Incident
          </button>
        </div>
        <pre>{JSON.stringify(incidents, null, 2)}</pre>
      </section>

      {error && <section className="error">{error}</section>}
    </main>
  );
}

