import React from "react";

const QUICK_ISSUES = [
  { id: "slow", label: "PC is very slow", icon: "slow", supported: true },
  { id: "hogs", label: "High Resource Usage", icon: "cpu", supported: true },
  { id: "storage", label: "Low disk space", icon: "storage", supported: true },
  { id: "startup", label: "Slow startup", icon: "startup", supported: true },
  { id: "battery", label: "Check battery health", icon: "battery", supported: true },
  { id: "update", label: "Windows Update issue", icon: "update", supported: true },
  { id: "system", label: "System errors", icon: "system", supported: true },
];

function IssueIcon({ type }) {
  const common = { viewBox: "0 0 24 24", "aria-hidden": "true", fill: "none", stroke: "currentColor", strokeWidth: "2", strokeLinecap: "round", strokeLinejoin: "round" };

  if (type === "slow") return (
    <svg {...common}><circle cx="12" cy="12" r="9"/><polyline points="12 6 12 12 8 14"/></svg>
  );

  if (type === "cpu") return (
    <svg {...common}><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M9 1v3M15 1v3M9 20v3M15 20v3M20 9h3M20 15h3M1 9h3M1 15h3"/></svg>
  );

  if (type === "storage") return (
    <svg {...common}><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
  );

  if (type === "startup") return (
    <svg {...common}><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
  );

  if (type === "battery") return (
    <svg {...common}><rect x="2" y="7" width="16" height="10" rx="2" ry="2"/><line x1="22" y1="11" x2="22" y2="13"/></svg>
  );

  if (type === "update") return (
    <svg {...common}><path d="M21.5 2v6h-6"/><path d="M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
  );

  if (type === "system") return (
    <svg {...common}><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>
  );

  return (
    <svg {...common}><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
  );
}

export default function QuickIssues({ onSelect }) {
  return (
    <div className="quick-issues">
      <div className="quick-grid">
        {QUICK_ISSUES.map((q) => (
          <button
            key={q.id}
            type="button"
            className={`quick-chip ${!q.supported ? "disabled-chip" : ""}`}
            onClick={() => q.supported && onSelect(q.label)}
            disabled={!q.supported}
            title={q.supported ? `Diagnose: ${q.label}` : "Coming soon in future update"}
          >
            <span className="quick-icon"><IssueIcon type={q.icon} /></span>
            <span>{q.label}</span>
            {!q.supported && <span className="coming-soon-badge">Coming Soon</span>}
          </button>
        ))}
      </div>
    </div>
  );
}
