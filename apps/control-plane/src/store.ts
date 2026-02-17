import { AgentProfile, AutonomousChangeSet, GoalRun, ReflectionRecord, SecurityIncident } from "./types.js";

export class InMemoryStore {
  private readonly goals = new Map<string, GoalRun>();
  private readonly agents = new Map<string, AgentProfile>();
  private readonly memories = new Map<string, string[]>();
  private readonly reflections = new Map<string, ReflectionRecord[]>();
  private readonly incidents = new Map<string, SecurityIncident>();
  private readonly changeSets = new Map<string, AutonomousChangeSet>();

  putGoal(goal: GoalRun): void {
    this.goals.set(goal.goal_id, goal);
  }

  getGoal(goalId: string): GoalRun | undefined {
    return this.goals.get(goalId);
  }

  putAgent(agent: AgentProfile): void {
    this.agents.set(agent.agent_id, agent);
  }

  getAgent(agentId: string): AgentProfile | undefined {
    return this.agents.get(agentId);
  }

  appendMemory(agentId: string, entry: string): void {
    const current = this.memories.get(agentId) ?? [];
    current.push(entry);
    this.memories.set(agentId, current.slice(-1000));
  }

  getMemories(agentId: string): string[] {
    return this.memories.get(agentId) ?? [];
  }

  addReflection(goalId: string, reflection: ReflectionRecord): void {
    const current = this.reflections.get(goalId) ?? [];
    current.push(reflection);
    this.reflections.set(goalId, current);
  }

  getReflections(goalId: string): ReflectionRecord[] {
    return this.reflections.get(goalId) ?? [];
  }

  putIncident(incident: SecurityIncident): void {
    this.incidents.set(incident.incident_id, incident);
  }

  listIncidents(): SecurityIncident[] {
    return Array.from(this.incidents.values());
  }

  putChangeSet(changeSet: AutonomousChangeSet): void {
    this.changeSets.set(changeSet.change_id, changeSet);
  }

  getChangeSet(changeId: string): AutonomousChangeSet | undefined {
    return this.changeSets.get(changeId);
  }

  listChangeSets(): AutonomousChangeSet[] {
    return Array.from(this.changeSets.values());
  }
}

export const store = new InMemoryStore();
