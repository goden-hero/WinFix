import React from "react";

function ConfidenceMeter({ value }) {
  const filled = Math.round(value / 20);
  return (
    <div className="confidence">
      <div className="confidence-dots" aria-hidden>
        {[0, 1, 2, 3, 4].map((i) => (
          <span key={i} className={`conf-dot ${i < filled ? "on" : ""}`} />
        ))}
      </div>
      <span className="confidence-label">Confidence: {value}%</span>
    </div>
  );
}

export default function DiagnosisResult({ diagnosis }) {
  const sevClass = (diagnosis.severity || "Medium").toLowerCase();
  return (
    <section className="card result-card">
      <div className="result-head">
        <span className={`severity-badge ${sevClass}`}>{diagnosis.severity} severity</span>
        <span className="result-label">DIAGNOSIS</span>
      </div>
      <div className="result-body">
        <span className="result-icon" aria-hidden>⚠</span>
        <div>
          <h2 className="result-title">{diagnosis.title}</h2>
          <ConfidenceMeter value={diagnosis.confidenceValue} />
          <p className="result-explanation">{diagnosis.explanation}</p>
        </div>
      </div>
    </section>
  );
}
