import { v4 as uuidv4 } from "uuid";
import { AutonomousChangeSet } from "../types.js";

export function createChangeSet(target: string, diff: string, riskScore: number): AutonomousChangeSet {
  return {
    change_id: uuidv4(),
    target,
    diff,
    risk_score: riskScore,
    canary_result: "pending",
    promotion_state: "staged"
  };
}

export function evaluateCanary(changeSet: AutonomousChangeSet): AutonomousChangeSet {
  const canaryPassed = changeSet.risk_score < 0.8;
  return {
    ...changeSet,
    canary_result: canaryPassed ? "passed" : "failed",
    promotion_state: canaryPassed ? "progressive" : "rolled_back"
  };
}

export function promoteChangeSet(changeSet: AutonomousChangeSet): AutonomousChangeSet {
  if (changeSet.canary_result !== "passed") {
    return {
      ...changeSet,
      promotion_state: "rolled_back"
    };
  }

  return {
    ...changeSet,
    promotion_state: "promoted"
  };
}

