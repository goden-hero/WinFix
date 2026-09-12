import React from "react";

const QUICK_ISSUES = [
  { id: "audio", label: "Audio", icon: "audio" },
  { id: "wifi", label: "WiFi problem", icon: "wifi" },
  { id: "slow", label: "PC slow", icon: "slow" },
  { id: "apps", label: "Apps not responding", icon: "document" },
  { id: "display", label: "display problem", icon: "display" },
];

function IssueIcon({ type }) {
  const common = { viewBox: "0 0 32 32", "aria-hidden": "true" };

  if (type === "audio") return (
    <svg {...common}><path d="M6 13h5l7-6v18l-7-6H6z" /><path d="M22 11.5c2 2 2 7 0 9M25 8.5c3.7 3.7 3.7 11.3 0 15" /></svg>
  );

  if (type === "wifi") return (
    <svg {...common}><path d="M4 12.5c4.8-4.6 19.2-4.6 24 0" /><path d="M8 17c3.1-3 12.9-3 16 0" /><path d="M12 21c1.6-1.5 6.4-1.5 8 0" /><circle cx="16" cy="25" r="1.4" fill="currentColor" stroke="none" /></svg>
  );

  if (type === "slow") return (
    <svg {...common}><path d="M4 24c1.4-6.4 5.2-9.6 10-9.6 3.7 0 6.4 1.7 8.1 4.7" /><path d="M22 19.1c2.1.1 4.1-.9 5.3-2.8" /><path d="M8 24c1.3-2.4 3.3-3.5 5.7-3.5 1.8 0 3.3.6 4.5 1.7" /><path d="M4 26h23" /></svg>
  );

  if (type === "document") return (
    <svg {...common}><path d="M9 4h10l5 5v19H9z" /><path d="M19 4v6h5M13 15h7M13 19h7M13 23h5" /></svg>
  );

  return (
    <svg {...common}><rect x="8" y="4" width="16" height="25" rx="2.5" /><path d="M12 8h8M14 25h4" /></svg>
  );
}

export default function QuickIssues({ onSelect }) {
  return (
    <div className="quick-issues">
      <div className="quick-grid">
        {QUICK_ISSUES.map((q) => (
          <button key={q.id} type="button" className="quick-chip" onClick={() => onSelect(q.label)}>
            <span className="quick-icon"><IssueIcon type={q.icon} /></span>
            <span>{q.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
