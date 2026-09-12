import React from "react";

export default function VerificationResult({ verification, sessionId, onRestart }) {
  const fixed = verification.status === "fixed";
  return (
    <section className={`card verify-card ${fixed ? "success" : "partial"}`}>
      <div className="verify-icon" aria-hidden>{fixed ? "✓" : "⚠"}</div>
      <h2 className="verify-title">{fixed ? "Fix successful" : "Partially resolved"}</h2>
      <p className="verify-message">{verification.message}</p>
      {sessionId && <p className="verify-session">Session {sessionId} · verification passed</p>}
      <button type="button" className="btn btn-primary btn-lg" onClick={onRestart}>
        Diagnose Another Problem
      </button>
    </section>
  );
}
