import React from "react";

const labels = {
  clear_temp_files: "Clear approved temporary files",
  disable_startup_app: "Disable startup application",
  remove_optional_app: "Remove optional application",
  apply_privacy_profile: "Apply privacy profile",
  run_sfc_scan: "Run System File Checker verification",
  run_dism_health_check: "Run DISM component store health check",
};

const scopeMap = {
  disable_startup_app: "Current Windows user (HKCU Run)",
  clear_temp_files: "Temporary file storage (%TEMP% / Windows Temp)",
  run_sfc_scan: "System file integrity (verify-only)",
  run_dism_health_check: "Component store health check (read-only)",
  apply_privacy_profile: "Privacy & telemetry profile (Disabled in MVP)",
  remove_optional_app: "Optional Windows App (Disabled in MVP)",
};

const rollbackMap = {
  disable_startup_app: "Supported (Backed up to RunDisabled)",
  clear_temp_files: "N/A (Temporary storage cleanup)",
  run_sfc_scan: "N/A (Read-only verification)",
  run_dism_health_check: "N/A (Read-only health check)",
  apply_privacy_profile: "Not available",
  remove_optional_app: "Not available",
};

const UNSUPPORTED_ACTIONS = new Set(["apply_privacy_profile", "remove_optional_app"]);

export function Plan({ actions = [], plan = [], approvedActions = {}, onApprove, busy }) {
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
            const isUnsupported = UNSUPPORTED_ACTIONS.has(actionId);
            const isApproved = approvedActions[actionId] === true;

            const appName = isStartup
              ? (action.parameters?.startup_entry_id ?? "").replace("hkcu_run:", "") || "Startup App"
              : null;
            const title = action.text || (isStartup ? `Disable Startup Application: ${appName}` : (labels[actionId] ?? actionId));
            const scope = scopeMap[actionId] || "Controlled Windows execution";
            const rollback = rollbackMap[actionId] || "Not applicable";

            return (
              <li key={actionId + i} className={`plan-step plan-item ${isUnsupported ? "unsupported-step" : ""}`}>
                <span className="plan-num">{i + 1}</span>
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", gap: "8px", alignItems: "center", marginBottom: "4px" }}>
                    <span className="risk severity warning">MEDIUM RISK</span>
                    <span className="badge safe" style={{ fontSize: "10px" }}>Target: {scope}</span>
                    {isUnsupported && (
                      <span className="badge danger" style={{ fontSize: "10px", background: "rgba(255,100,100,0.2)", color: "#ff8888" }}>
                        Not available in MVP
                      </span>
                    )}
                  </div>
                  <span className="plan-text" style={{ display: "block", fontWeight: 700, margin: "4px 0" }}>{title}</span>
                  <p className="muted" style={{ fontSize: "13px", margin: "4px 0" }}>{action.reason || action.description}</p>
                  <div style={{ display: "flex", gap: "14px", fontSize: "11px", color: "var(--text-dim)", marginTop: "4px" }}>
                    <span>Target Scope: {scope}</span>
                    <span>Rollback: {rollback}</span>
                  </div>
                </div>

                {isUnsupported ? (
                  <button type="button" className="btn btn-disabled" disabled style={{ opacity: 0.5, cursor: "not-allowed" }}>
                    Coming soon — execution disabled for safety
                  </button>
                ) : (
                  <button
                    type="button"
                    className={`btn ${isApproved ? "btn-secondary" : "btn-primary"}`}
                    disabled={busy || isApproved}
                    onClick={() => onApprove(actionId)}
                  >
                    {isApproved ? "✓ Approved" : "Approve Step"}
                  </button>
                )}
              </li>
            );
          })}
        </ol>
      )}

      <div className="plan-actions" style={{ marginTop: "16px", paddingTop: "12px", borderTop: "1px solid #26313c" }}>
        <p className="plan-note muted" style={{ fontSize: "12px" }}>
          WinFix will not modify your system until you explicitly approve each repair step.
        </p>
      </div>
    </section>
  );
}

export default Plan;
