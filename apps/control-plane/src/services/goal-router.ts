import { DomainName, GoalSpec } from "../types.js";

export interface RoutedGoal {
  goal: GoalSpec;
  primary_domain: DomainName;
  secondary_domains: DomainName[];
}

const priority: DomainName[] = ["dev", "social", "games"];

export function routeGoal(goal: GoalSpec): RoutedGoal {
  const ordered = [...goal.domains].sort(
    (a, b) => priority.indexOf(a) - priority.indexOf(b)
  );

  return {
    goal,
    primary_domain: ordered[0] ?? "dev",
    secondary_domains: ordered.slice(1)
  };
}

