import React from "react";

export default function RepairProgress({ steps }) {
  return (
    <section className="card progress-card repair">
      <div className="progress-head">
        <div className="progress-title-row">
          <span className="pulse-dot orange" aria-hidden />
          <h2>Repairing your system…</h2>
        </div>
        <p className="progress-problem">Applying approved repair plan</p>
      </div>
      <ol className="step-list">
        {steps.map((s, i) => (
          <li key={i} className={`step ${s.status || "pending"}`}>
            <span className="step-icon" aria-hidden>
              {s.status === "done" ? "✓" : s.status === "running" ? "⏳" : "○"}
            </span>
            <span className="step-text">{s.step}</span>
            {s.detail && <span className="step-detail">{s.detail}</span>}
          </li>
        ))}
        {steps.length === 0 && (
          <li className="step running">
            <span className="step-icon" aria-hidden>⏳</span>
            <span className="step-text">Creating system restore point…</span>
          </li>
        )}
      </ol>
      <div className="progress-foot">
        <span className="agent-tag">🔧 Executing repair plan</span>
      </div>
    </section>
  );
}
