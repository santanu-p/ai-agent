const EVENT_MAP = {
  stable_only_toggled: "ai_updates.preference.stable_only_toggled",
  personalized_opt_out_toggled: "ai_updates.preference.personalized_opt_out_toggled",
  feedback_helpful: "ai_updates.feedback.helpful",
  feedback_not_helpful: "ai_updates.feedback.not_helpful",
  feedback_report_issue: "ai_updates.feedback.report_issue",
};

export function mapTelemetryEvent(action) {
  return EVENT_MAP[action] ?? "ai_updates.unknown_action";
}

export function emitTelemetry(action, payload = {}, transport = console.log) {
  const eventName = mapTelemetryEvent(action);
  transport("telemetry", { eventName, payload, emittedAt: new Date().toISOString() });
}
