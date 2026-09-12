import React from "react";

export default function Plan({ plan, onApprove }) {
  return (
    <section className="card plan-card">
      <div className="card-head">
        <h3>📋 Recommended repair plan</h3>
        <span className="card-count">{plan.length} steps</span>
      </div>
      <ol className="plan-list">
        {plan.map((p, i) => (
          <li key={i} className="plan-step">
            <span className="plan-num">{i + 1}</span>
            <span className="plan-text">{p.text}</span>
            <span className="plan-badges">
              {p.safe && <span className="badge safe">✓ Safe</span>}
              {p.admin && <span className="badge admin">⚠ Admin</span>}
              {p.restart && <span className="badge restart">🔄 Restart</span>}
            </span>
          </li>
        ))}
      </ol>
      <div className="plan-actions">
        <p className="plan-note">WinFix will not modify your system until you approve the repair.</p>
        <button type="button" className="btn btn-primary btn-lg" onClick={onApprove}>
          Approve &amp; Repair
        </button>
      </div>
    </section>
  );
}
