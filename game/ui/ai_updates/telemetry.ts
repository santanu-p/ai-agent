import { FeedbackValue, UpdateMode } from "./types";

export const AI_UPDATE_TELEMETRY_EVENTS = {
  panelViewed: "ai_update_panel_viewed",
  modeChanged: "ai_update_mode_changed",
  feedbackSubmitted: "ai_update_feedback_submitted",
} as const;

export interface TelemetryClient {
  emit: (event: string, payload: Record<string, unknown>) => void;
}

export function trackModeChange(client: TelemetryClient, mode: UpdateMode): void {
  client.emit(AI_UPDATE_TELEMETRY_EVENTS.modeChanged, { mode });
}

export function trackFeedback(
  client: TelemetryClient,
  updateId: string,
  value: FeedbackValue,
): void {
  client.emit(AI_UPDATE_TELEMETRY_EVENTS.feedbackSubmitted, {
    updateId,
    feedback: value,
  });
}
