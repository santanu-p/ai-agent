import { useEffect, useMemo, useState } from "react";

import { buildConcisePatchNotes } from "./structuredPatchNotes";
import {
  AI_UPDATE_TELEMETRY_EVENTS,
  TelemetryClient,
  trackFeedback,
  trackModeChange,
} from "./telemetry";
import { FeedbackValue, StructuredUpdateMetadata, UpdateMode } from "./types";

interface AIUpdatesPanelProps {
  metadata: StructuredUpdateMetadata;
  telemetry: TelemetryClient;
  initialMode?: UpdateMode;
}

function formatDeploymentTime(deployedAtISO: string): string {
  return new Date(deployedAtISO).toLocaleString();
}

export function AIUpdatesPanel({
  metadata,
  telemetry,
  initialMode = "adaptive",
}: AIUpdatesPanelProps): JSX.Element {
  const [mode, setMode] = useState<UpdateMode>(initialMode);
  const notes = useMemo(() => buildConcisePatchNotes(metadata), [metadata]);

  useEffect(() => {
    telemetry.emit(AI_UPDATE_TELEMETRY_EVENTS.panelViewed, {
      updateId: metadata.id,
      mode,
    });
  }, [metadata.id, mode, telemetry]);

  const onModeChange = (nextMode: UpdateMode): void => {
    setMode(nextMode);
    trackModeChange(telemetry, nextMode);
  };

  const onFeedback = (value: FeedbackValue): void => {
    trackFeedback(telemetry, metadata.id, value);
  };

  return (
    <section aria-label="AI updates" data-update-id={metadata.id}>
      <header>
        <h2>AI Update</h2>
        <p>Deployed: {formatDeploymentTime(metadata.deployedAtISO)}</p>
      </header>

      <div>
        <h3>What changed</h3>
        <ul>
          {metadata.changes.map((change) => (
            <li key={`${metadata.id}-${change.category}-${change.title}`}>
              <strong>{change.title}</strong> ({change.category.replace("_", " ")}): {change.summary}
            </li>
          ))}
        </ul>
      </div>

      <div>
        <h3>Why it changed</h3>
        <ul>
          {metadata.metricDeltas.map((delta) => (
            <li key={`${metadata.id}-${delta.metric}`}>
              {delta.metric}: {delta.previous} → {delta.current}
              {delta.objective ? ` (target ${delta.objective.target}${delta.objective.unit ?? ""})` : ""}
            </li>
          ))}
        </ul>
      </div>

      <div>
        <h3>Patch notes (concise)</h3>
        <ul>
          {notes.map((note, index) => (
            <li key={`${metadata.id}-note-${index}`}>{note}</li>
          ))}
        </ul>
      </div>

      <fieldset>
        <legend>Update delivery mode</legend>
        <label>
          <input
            type="radio"
            name="ai-update-mode"
            checked={mode === "adaptive"}
            onChange={() => onModeChange("adaptive")}
          />
          Adaptive
        </label>
        <label>
          <input
            type="radio"
            name="ai-update-mode"
            checked={mode === "stable_only"}
            onChange={() => onModeChange("stable_only")}
          />
          Stable-only
        </label>
        <label>
          <input
            type="radio"
            name="ai-update-mode"
            checked={mode === "opt_out"}
            onChange={() => onModeChange("opt_out")}
          />
          Opt-out of AI-driven updates
        </label>
      </fieldset>

      <div>
        <h3>Feedback</h3>
        <button type="button" onClick={() => onFeedback("helpful")}>
          This update helped
        </button>
        <button type="button" onClick={() => onFeedback("not_helpful")}>
          Needs work
        </button>
      </div>
    </section>
  );
}
