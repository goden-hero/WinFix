import React from "react";

const labels = {
  clear_temp_files: "Clear approved temporary files",
  disable_startup_app: "Disable startup application",
  remove_optional_app: "Remove an optional application",
  apply_privacy_profile: "Apply a privacy profile",
  run_sfc_scan: "Run System File Checker",
  run_dism_health_check: "Run DISM health check",
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
            const title = action.text || (isStartup ? `Disable Startup Entry: ${appName}` : (labels[actionId] ?? actionId));

            return (
              <li key={actionId + i} className="plan-step plan-item">
                <span className="plan-num">{i + 1}</span>
                <div style={{ flex: 1 }}>
                  <span className="risk severity warning">Medium risk</span>
                  <span className="plan-text" style={{ display: "block", fontWeight: 700, margin: "4px 0" }}>{title}</span>
                  {isStartup && (
                    <small style={{ display: "block", color: "#4ee6b6", marginBottom: "6px" }}>
                      Currently: Enabled (HKCU Run)
                    </small>
                  )}
                  <p className="muted" style={{ fontSize: "13px", margin: 0 }}>{action.reason || action.description}</p>
                </div>
                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={busy}
                  onClick={() => onApprove(actionId)}
                >
                  Approve
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
