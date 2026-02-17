import { describe, expect, test } from "vitest";
import {
  createChangeSet,
  evaluateCanary,
  promoteChangeSet
} from "../src/services/deployment-controller.js";

describe("deployment controller", () => {
  test("promotes low risk change after canary pass", () => {
    const staged = createChangeSet("runtime-plane", "increase replicas", 0.3);
    const canary = evaluateCanary(staged);
    const promoted = promoteChangeSet(canary);
    expect(promoted.promotion_state).toBe("promoted");
  });

  test("rolls back high risk change on canary failure", () => {
    const staged = createChangeSet("security-plane", "new remediator", 0.95);
    const canary = evaluateCanary(staged);
    const promoted = promoteChangeSet(canary);
    expect(promoted.promotion_state).toBe("rolled_back");
  });
});

