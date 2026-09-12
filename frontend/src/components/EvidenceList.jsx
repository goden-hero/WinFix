import React, { useState } from "react";

function EvidenceRow({ item }) {
  const [open, setOpen] = useState(false);
  const statusClass = item.status || "good";
  const icon = statusClass === "bad" ? "✗" : statusClass === "warn" ? "⚠" : "✓";
  const topHogs = item.top_resource_consumers || [];

  return (
    <li className={`evidence-row ${statusClass}`}>
      <span className="evidence-icon" aria-hidden>{icon}</span>
      <div className="evidence-main">
        <div className="evidence-line">
          <span className="evidence-checked">{item.checked}</span>
          <span className={`evidence-result ${statusClass}`}>{item.result}</span>
        </div>
        {open && (
          <div className="evidence-details">
            <p className="evidence-why">{item.why}</p>
            {topHogs.length > 0 && (
              <div className="resource-hog-box">
                <div className="resource-hog-table">
                  <div className="resource-hog-header">
                    <span>Application</span>
                    <span>Procs</span>
                    <span>Raw CPU</span>
                    <span>RAM</span>
                    <span>Impact</span>
                  </div>
                  {topHogs.map((app, idx) => (
                    <div key={idx} className={`resource-hog-row impact-${(app.impact || "low").toLowerCase()}`}>
                      <span className="app-name"><strong>{app.name}</strong></span>
                      <span className="app-count">{app.process_count}</span>
                      <span className="app-cpu">{app.raw_cpu_percent}%</span>
                      <span className="app-ram">{app.memory_mb} MB ({app.memory_percent}%)</span>
                      <span className={`impact-badge impact-${(app.impact || "low").toLowerCase()}`}>
                        {app.impact_score} [{app.impact}]
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
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
