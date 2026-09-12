import React from "react";

export default function VerificationResult({ verification, sessionId, onRestart }) {
  const results = Array.isArray(verification) ? verification : [];
  const allVerified = results.length > 0 && results.every((r) => r.status === "verified");
  const hasElevation = results.some((r) => r.status === "requires_elevation");
  const hasNotImplemented = results.some((r) => r.status === "not_implemented");

  let cardClass = "partial";
  let icon = "⚠";
  let title = "Partially resolved";

  if (allVerified) {
    cardClass = "success";
    icon = "✓";
    title = "Remediation Action Verified";
  } else if (hasElevation) {
    cardClass = "warning";
    icon = "🔒";
    title = "Administrator Privileges Required";
  } else if (hasNotImplemented) {
    cardClass = "info";
    icon = "⚠️";
    title = "Not Available in MVP";
  }

  return (
    <section className={`card verify-card ${cardClass}`}>
      <div className="verify-icon" aria-hidden>{icon}</div>
      <h2 className="verify-title">{title}</h2>
      {hasElevation && (
        <p className="verify-message">
          WinFix completed diagnosis and checking, but Administrator privileges are required to perform the recommended repairs.
        </p>
      )}
      {hasNotImplemented && !hasElevation && (
        <p className="verify-message">
          The requested repair capability is disabled in this MVP release.
        </p>
      )}
      {allVerified && (
        <p className="verify-message">
          Independent verification confirmed the specific remediation action executed successfully.
        </p>
      )}
      {sessionId && <p className="verify-session">Session {sessionId}</p>}
      <button type="button" className="btn btn-primary btn-lg" onClick={onRestart}>
        Diagnose Another Problem
      </button>
    </section>
  );
}
