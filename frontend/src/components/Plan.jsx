import React from "react";

const labels = {
  clear_temp_files: "Clear approved temporary files",
  disable_startup_app: "Disable startup application",
  remove_optional_app: "Remove an optional application (Disabled in MVP)",
  apply_privacy_profile: "Apply a privacy profile (Disabled in MVP)",
  run_sfc_scan: "Run System File Checker verification",
  run_dism_health_check: "Run DISM component store health check",
  restart_windows_explorer: "Restart Windows Explorer (explorer.exe)",
};

const scopeMap = {
  disable_startup_app: "Current Windows user (HKCU Run)",
  clear_temp_files: "Temporary file storage",
  run_sfc_scan: "System file integrity (verify-only)",
  run_dism_health_check: "Component store health check (read-only)",
  restart_windows_explorer: "Windows Explorer shell process (explorer.exe)",
};

const rollbackMap = {
  disable_startup_app: "Supported (Backed up to RunDisabled)",
  clear_temp_files: "N/A (Temporary storage cleanup)",
  run_sfc_scan: "N/A (Read-only verification)",
  run_dism_health_check: "N/A (Read-only health check)",
  restart_windows_explorer: "No separate rollback; verify Explorer process state after execution.",
};

export function Plan({ actions = [], plan = [], onApprove, busy }) {
  const items = actions.length > 0 ? actions : plan;

  return (
    <section className="panel card plan-card">
      <div className="card-head">
        <h3>📋 Recommended repair plan</h3>
        <span className="card-count">{items.length} steps</span>
      </div>

      {items.length === 0 ? (
        <p className="muted" style={{ padding: "16px 0" }}>
          No action is recommended from this snapshot. WinFix will not make a speculative change.
        </p>
      ) : (
        <ol className="plan-list">
          {items.map((action, i) => {
            const actionId = action.action_id || action.id || "action";
            const isStartup = actionId === "disable_startup_app";
            const appName = isStartup
              ? (action.parameters?.startup_entry_id ?? "").replace("hkcu_run:", "") || "Startup App"
              : null;
            const title = action.text || (isStartup ? `Disable Startup Application: ${appName}` : (labels[actionId] ?? actionId));
            const scope = scopeMap[actionId] || "Controlled Windows execution";
            const rollback = rollbackMap[actionId] || "Not applicable";

            return (
              <li key={actionId + i} className="plan-step plan-item">
                <span className="plan-num">{i + 1}</span>
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", gap: "8px", alignItems: "center", marginBottom: "4px" }}>
                    <span className="risk severity warning">MEDIUM RISK</span>
                    <span className="badge safe" style={{ fontSize: "10px" }}>Scope: {scope}</span>
                  </div>
                  <span className="plan-text" style={{ display: "block", fontWeight: 700, margin: "4px 0" }}>{title}</span>
                  <p className="muted" style={{ fontSize: "13px", margin: "4px 0" }}>{action.reason || action.description}</p>
                  <div style={{ display: "flex", gap: "14px", fontSize: "11px", color: "var(--text-dim)", marginTop: "4px" }}>
                    <span>Scope: {scope}</span>
                    <span>Rollback: {rollback}</span>
                  </div>
                </div>
                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={busy}
                  onClick={() => onApprove(actionId)}
                >
                  Approve Step
                </button>
              </li>
            );
          })}
        </ol>
      )}

      <div className="plan-actions" style={{ marginTop: "16px", paddingTop: "12px", borderTop: "1px solid #26313c" }}>
        <p className="plan-note muted" style={{ fontSize: "12px" }}>
          WinFix will not modify your system until you approve each repair step.
        </p>
      </div>
    </section>
  );
}

export default Plan;
