import React from "react";

const QUICK_ISSUES = [
  { id: "slow", icon: "🐌", label: "PC is very slow" },
  { id: "battery", icon: "🔋", label: "Check battery health" },
  { id: "update", icon: "🔄", label: "Windows Update issue" },
  { id: "startup", icon: "⚡", label: "Slow startup" },
  { id: "storage", icon: "💾", label: "Low disk space" },
  { id: "apps", icon: "📦", label: "Apps not responding" },
  { id: "system", icon: "🛠️", label: "System errors" },
  { id: "explorer", icon: "💻", label: "Check Windows Explorer / taskbar" },
];

export default function QuickIssues({ onSelect }) {
  return (
    <div className="quick-issues">
      <span className="quick-label">
        Or try a common problem:
      </span>

      <div className="quick-grid">
        {QUICK_ISSUES.map((q) => (
          <button
            key={q.id}
            type="button"
            className="quick-chip"
            onClick={() => onSelect(q.label)}
          >
            <span className="quick-icon">
              {q.icon}
            </span>

            {q.label}
          </button>
        ))}
      </div>
    </div>
  );
}