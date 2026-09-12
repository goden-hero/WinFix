import React, { useState } from "react";

function EvidenceRow({ item }) {
  const [open, setOpen] = useState(false);
  const statusClass = item.status || "good";
  const icon = statusClass === "bad" ? "✗" : statusClass === "warn" ? "⚠" : "✓";
  return (
    <li className={`evidence-row ${statusClass}`}>
      <span className="evidence-icon" aria-hidden>{icon}</span>
      <div className="evidence-main">
        <div className="evidence-line">
          <span className="evidence-checked">{item.checked}</span>
          <span className={`evidence-result ${statusClass}`}>{item.result}</span>
        </div>
        {open && <p className="evidence-why">{item.why}</p>}
      </div>
      <button type="button" className="tech-toggle" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        {open ? "▲" : "▼"} technical
      </button>
    </li>
  );
}

export default function EvidenceList({ evidence }) {
  return (
    <section className="card evidence-card">
      <div className="card-head">
        <h3>🔍 Evidence found</h3>
        <span className="card-count">{evidence.length} checks</span>
      </div>
      <ul className="evidence-list">
        {evidence.map((item, i) => (
          <EvidenceRow key={i} item={item} />
        ))}
      </ul>
    </section>
  );
}
