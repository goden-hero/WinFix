const labels = {
  clear_temp_files: "Clear approved temporary files",
  disable_startup_app: "Disable startup application",
  remove_optional_app: "Remove an optional application",
  apply_privacy_profile: "Apply a privacy profile",
  run_sfc_scan: "Run System File Checker",
  run_dism_health_check: "Run DISM health check",
};

export function Plan({ actions, onApprove, busy }) {
  return (
    <section className="panel">
      <h2>Remediation plan</h2>
      {actions.length === 0 ? (
        <p className="muted">No action is recommended from this snapshot. WinFix will not make a speculative change.</p>
      ) : (
        <div className="plan-list">
          {actions.map((action) => {
            const isStartup = action.action_id === "disable_startup_app";
            const appName = isStartup
              ? (action.parameters?.startup_entry_id ?? "").replace("hkcu_run:", "") || "Startup App"
              : null;

            return (
              <article className="plan-item" key={action.action_id}>
                <div>
                  <span className="risk">Medium risk</span>
                  <h3>
                    {isStartup ? `Disable Startup Entry: ${appName}` : (labels[action.action_id] ?? action.action_id)}
                  </h3>
                  {isStartup && (
                    <small style={{ display: "block", color: "#4ee6b6", marginBottom: "6px" }}>
                      Currently: Enabled (HKCU Run)
                    </small>
                  )}
                  <p>{action.reason}</p>
                </div>
                <button disabled={busy} onClick={() => onApprove(action.action_id)}>
                  Approve
                </button>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
