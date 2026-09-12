import React from "react";

const actionMeta = {
  clear_temp_files: {
    name: "Clear approved temporary files",
    target: "Temporary storage (%TEMP% & C:\\Windows\\Temp)",
    change: "Removes unneeded temporary cache files to free disk space",
    rollback: "N/A (Temporary storage cleanup)",
    risk: "MEDIUM",
  },
  disable_startup_app: {
    name: "Disable startup application",
    target: "Current User Startup Registry (HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run)",
    change: "Moves startup entry to HKCU RunDisabled registry key so it won't launch on boot",
    rollback: "Supported (Restorable from RunDisabled key)",
    risk: "MEDIUM",
  },
  run_sfc_scan: {
    name: "Run System File Checker (SFC)",
    target: "Protected Windows System Files",
    change: "Scans and verifies integrity of protected Windows system files",
    rollback: "N/A (Read-only integrity check)",
    risk: "MEDIUM",
  },
  run_dism_health_check: {
    name: "Run DISM Component Store Health Check",
    target: "Windows Component Store (WinSxS)",
    change: "Checks component store health and repairs corrupted system packages",
    rollback: "N/A (Read-only health check)",
    risk: "MEDIUM",
  },
  apply_privacy_profile: {
    name: "Apply Privacy Profile",
    target: "Windows Telemetry & Privacy Settings",
    change: "Execution disabled in current MVP release for safety",
    rollback: "Not available",
    risk: "DISABLED",
  },
  remove_optional_app: {
    name: "Remove Optional Application",
    target: "Windows Optional Features",
    change: "Execution disabled in current MVP release for safety",
    rollback: "Not available",
    risk: "DISABLED",
  },
};

export default function ApprovalDialog({ open, plan = [], onCancel, onConfirm }) {
  if (!open) return null;

  const validSteps = plan.filter(
    (item) => item.action_id !== "apply_privacy_profile" && item.action_id !== "remove_optional_app"
  );

  return (
    <div className="modal-overlay" role="dialog" aria-modal="true" aria-label="Review and approve repair steps">
      <div className="modal" style={{ maxWidth: "680px", width: "90%" }}>
        <div className="modal-head">
          <h3>Confirm Repair Plan Execution</h3>
          <p>Review the exact technical changes WinFix will make to your system:</p>
        </div>

        <ul className="modal-list" style={{ display: "flex", flexDirection: "column", gap: "12px", margin: "16px 0" }}>
          {validSteps.map((item, i) => {
            const id = item.action_id || item.id || "action";
            const meta = actionMeta[id] || {
              name: item.text || id,
              target: "Controlled Windows execution",
              change: item.reason || item.description || "System repair step",
              rollback: "N/A",
              risk: "MEDIUM",
            };

            const isStartup = id === "disable_startup_app";
            const targetDetails = isStartup
              ? `HKCU Run Registry Key -> ${item.parameters?.startup_entry_id ?? meta.target}`
              : meta.target;

            return (
              <li key={i}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                  <strong style={{ fontSize: "var(--font-md)", color: "#e8edf6" }}>
                    {i + 1}. {meta.name}
                  </strong>
                  <span className="severity-badge warning">
                    {meta.risk} RISK
                  </span>
                </div>
                <div style={{ fontSize: "var(--font-sm)", color: "#a0aec0", display: "flex", flexDirection: "column", gap: "4px" }}>
                  <div><strong>Target:</strong> {targetDetails}</div>
                  <div><strong>What will change:</strong> {item.reason || meta.change}</div>
                  <div><strong>Rollback Info:</strong> {meta.rollback}</div>
                </div>
              </li>
            );
          })}
        </ul>

        <div className="modal-actions">
          <button type="button" className="btn btn-ghost" onClick={onCancel}>
            Cancel
          </button>
          <button type="button" className="btn btn-primary" onClick={onConfirm}>
            Approve & Execute Fix ({validSteps.length} steps)
          </button>
        </div>
      </div>
    </div>
  );
}
