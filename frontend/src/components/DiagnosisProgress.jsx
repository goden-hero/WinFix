import React from "react";

export default function DiagnosisProgress({ steps, problem }) {
  return (
    <section className="card progress-card">
      <div className="progress-head">
        <div className="progress-title-row">
          <span className="pulse-dot" aria-hidden />
          <h2>WinFix is diagnosing…</h2>
        </div>
        <p className="progress-problem">“{problem}”</p>
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
            <span className="step-text">Connecting to Windows machine…</span>
          </li>
        )}
      </ol>
      <div className="progress-foot">
        <span className="agent-tag">🤖 Agent working autonomously</span>
      </div>
    </section>
  );
}
