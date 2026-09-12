import React from "react";

export default function RepairProgress({ steps, status, busy }) {
  const isExecuting = (busy && status === "approved") || status === "executing";
  const isVerifying = busy && status === "verifying";

  let title = "Repair Plan Approved";
  let subtitle = "Your approved repair plan is ready. Click below to execute.";
  let tag = "⏳ Waiting for your confirmation";
  let dotClass = "pulse-dot";

  if (isExecuting) {
    title = "Repairing your system…";
    subtitle = "Applying approved repair plan";
    tag = "🔧 Executing repair plan";
    dotClass = "pulse-dot orange";
  } else if (isVerifying) {
    title = "Verifying system state…";
    subtitle = "Checking independent system verification metrics";
    tag = "🔍 Verifying system";
    dotClass = "pulse-dot orange";
  } else if (status === "verifying") {
    title = "Remediation Applied";
    subtitle = "Repair completed. Click below to verify system state.";
    tag = "✓ Ready to verify";
    dotClass = "pulse-dot";
  }

  return (
    <section className="card progress-card repair">
      <div className="progress-head">
        <div className="progress-title-row">
          <span className={dotClass} aria-hidden />
          <h2>{title}</h2>
        </div>
        <p className="progress-problem">{subtitle}</p>
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
        <span className="agent-tag">{tag}</span>
      </div>
    </section>
  );
}
