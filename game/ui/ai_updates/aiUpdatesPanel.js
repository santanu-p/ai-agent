import { buildPatchNotes } from "./patchNotesFormatter.js";
import { emitTelemetry } from "./telemetry.js";

export function createAiUpdatesPanel({ metadata, rootElement }) {
  const notes = buildPatchNotes(metadata);

  rootElement.innerHTML = `
    <section class="ai-updates-panel" aria-label="AI updates panel">
      <header class="ai-updates-header">
        <h2>${notes.title}</h2>
        <p class="deployed-at">Deployed: ${notes.deployedAt}</p>
      </header>

      <div class="update-controls">
        <label>
          <input type="checkbox" data-pref="stable-only" ${metadata.preferences.stableOnly ? "checked" : ""}>
          Stable-only mode
        </label>
        <label>
          <input type="checkbox" data-pref="opt-out" ${metadata.preferences.personalizedUpdatesOptOut ? "checked" : ""}>
          Opt out of personalized AI updates
        </label>
      </div>

      <ul class="patch-notes">
        ${notes.lines.map((line) => `<li>${line}</li>`).join("")}
      </ul>

      <footer class="feedback-actions">
        <button data-feedback="helpful">Helpful</button>
        <button data-feedback="not_helpful">Not helpful</button>
        <button data-feedback="report_issue">Report issue</button>
      </footer>
    </section>
  `;

  rootElement.querySelector('[data-pref="stable-only"]').addEventListener("change", (event) => {
    emitTelemetry("stable_only_toggled", {
      enabled: event.target.checked,
      version: metadata.version,
    });
  });

  rootElement.querySelector('[data-pref="opt-out"]').addEventListener("change", (event) => {
    emitTelemetry("personalized_opt_out_toggled", {
      enabled: event.target.checked,
      version: metadata.version,
    });
  });

  rootElement.querySelectorAll("[data-feedback]").forEach((button) => {
    button.addEventListener("click", () => {
      emitTelemetry(`feedback_${button.dataset.feedback}`, {
        version: metadata.version,
      });
    });
  });
}
