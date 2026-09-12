import React from "react";

export function formatBytes(bytes) {
  if (!bytes || bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

const actionTitles = {
  run_sfc_scan: "System File Checker (SFC)",
  run_dism_health_check: "DISM Component Store Health Check",
  clear_temp_files: "Clear Approved Temporary Files",
  disable_startup_app: "Disable Startup Application",
  apply_privacy_profile: "Apply Privacy Profile",
  remove_optional_app: "Remove Optional Application",
};

export function ExecutionView({ results, onExecute, onVerify, status, busy }) {
  if (status === "approved" && (!results || results.length === 0)) {
    return (
      <section className="panel execution-panel">
        <h2>Remediation Approved</h2>
        <p>The action plan is approved and ready for safe execution through the controlled adapter.</p>
        <button className="btn-primary" disabled={busy} onClick={onExecute}>
          {busy ? "Executing action..." : "Execute Approved Remediation"}
        </button>
      </section>
    );
  }

  if (!results || results.length === 0) return null;

  const hasExecutableResults = results.some(
    (res) => res.status !== "requires_elevation" && res.status !== "not_implemented"
  );

  return (
    <section className="panel execution-panel">
      <h2>Execution Results</h2>
      <div className="execution-list">
        {results.map((res, idx) => {
          const isStartup = res.action_id === "disable_startup_app";
          const title = actionTitles[res.action_id] || res.action_id;

          if (res.status === "requires_elevation") {
            return (
              <article className="execution-card elevation-card" key={idx} style={{ borderLeft: "4px solid #ffd166", padding: "16px", marginBottom: "16px", background: "rgba(255, 209, 102, 0.08)", borderRadius: "8px" }}>
                <div className="execution-header" style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <span className="status-badge warning" style={{ background: "#ffd166", color: "#111", padding: "4px 8px", borderRadius: "4px", fontWeight: "bold" }}>REQUIRES ELEVATION</span>
                  <h3 style={{ margin: 0 }}>🔒 Administrator Privileges Required</h3>
                </div>
                <p className="execution-message" style={{ marginTop: "10px" }}>
                  WinFix detected a recommended system repair, but this action requires Administrator privileges.
                </p>
                <div className="elevation-guidance" style={{ marginTop: "12px", background: "rgba(0,0,0,0.2)", padding: "12px", borderRadius: "6px" }}>
                  <div><strong>Recommended Action:</strong> {title}</div>
                  <div style={{ marginTop: "4px" }}><strong>Current Status:</strong> <span style={{ color: "#ffd166" }}>Not executed</span></div>
                  <div style={{ marginTop: "4px" }}><strong>How to proceed:</strong> Restart WinFix Agent with Administrator privileges.</div>
                </div>
              </article>
            );
          }

          if (res.status === "not_implemented") {
            return (
              <article className="execution-card unimplemented-card" key={idx} style={{ borderLeft: "4px solid #90e0ef", padding: "16px", marginBottom: "16px", background: "rgba(144, 224, 239, 0.08)", borderRadius: "8px" }}>
                <div className="execution-header" style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <span className="status-badge info" style={{ background: "#90e0ef", color: "#111", padding: "4px 8px", borderRadius: "4px", fontWeight: "bold" }}>NOT AVAILABLE</span>
                  <h3 style={{ margin: 0 }}>⚠️ Not Available in MVP</h3>
                </div>
                <p className="execution-message" style={{ marginTop: "10px" }}>
                  {res.message || "This remediation capability is intentionally disabled in the current controlled-execution version of WinFix."}
                </p>
              </article>
            );
          }

          return (
            <article className="execution-card" key={idx}>
              <div className="execution-header">
                <span className={`status-badge ${res.status}`}>{res.status.toUpperCase()}</span>
                <h3>{isStartup ? `DISABLE_STARTUP_APP (${res.details?.name ?? "Startup App"})` : title}</h3>
              </div>
              <p className="execution-message">{res.message}</p>
              {res.details && !isStartup && res.action_id === "clear_temp_files" && (
                <div className="execution-metrics">
                  <div className="metric-chip">
                    <small>Files Cleaned</small>
                    <strong>{res.details.files_deleted ?? 0}</strong>
                  </div>
                  <div className="metric-chip">
                    <small>Storage Reclaimed</small>
                    <strong>{formatBytes(res.details.bytes_reclaimed)}</strong>
                  </div>
                  <div className="metric-chip">
                    <small>Target Root</small>
                    <span className="root-path">{res.details.target_directory ?? "Default Demo Root"}</span>
                  </div>
                </div>
              )}
              {res.details && isStartup && (
                <div className="execution-metrics">
                  <div className="metric-chip">
                    <small>Target Entry</small>
                    <strong>{res.details.name ?? "N/A"}</strong>
                  </div>
                  <div className="metric-chip">
                    <small>State Before</small>
                    <strong style={{ color: "#ffd166" }}>{res.details.state_before ?? "ENABLED"}</strong>
                  </div>
                  <div className="metric-chip">
                    <small>State After</small>
                    <strong style={{ color: "#4ee6b6" }}>{res.details.state_after ?? "DISABLED"}</strong>
                  </div>
                  <div className="metric-chip">
                    <small>Active Startup Entries</small>
                    <strong>
                      {res.details.enabled_entries_before ?? 0} → {res.details.enabled_entries_after ?? 0}
                    </strong>
                  </div>
                </div>
              )}
            </article>
          );
        })}
      </div>
      {status === "verifying" && hasExecutableResults && (
        <div className="action-row" style={{ marginTop: "16px" }}>
          <button className="btn-primary" disabled={busy} onClick={onVerify}>
            {busy ? "Verifying..." : "Verify System State"}
          </button>
        </div>
      )}
      {status === "verifying" && !hasExecutableResults && (
        <div className="info-banner" style={{ marginTop: "16px", padding: "12px", background: "rgba(255,255,255,0.05)", borderRadius: "6px" }}>
          <p className="muted" style={{ margin: 0 }}>
            Execution was blocked due to privilege requirements or missing implementation. Verification is not applicable for unexecuted actions.
          </p>
        </div>
      )}
    </section>
  );
}

export default ExecutionView;
