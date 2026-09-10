export function formatBytes(bytes) {
  if (!bytes || bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

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

  return (
    <section className="panel execution-panel">
      <h2>Execution Results</h2>
      <div className="execution-list">
        {results.map((res, idx) => (
          <article className="execution-card" key={idx}>
            <div className="execution-header">
              <span className={`status-badge ${res.status}`}>{res.status.toUpperCase()}</span>
              <h3>{res.action_id === "clear_temp_files" ? "Clear Approved Temporary Files" : res.action_id}</h3>
            </div>
            <p className="execution-message">{res.message}</p>
            {res.details && (
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
          </article>
        ))}
      </div>
      {status === "verifying" && (
        <div className="action-row">
          <button className="btn-primary" disabled={busy} onClick={onVerify}>
            {busy ? "Verifying..." : "Verify System State"}
          </button>
        </div>
      )}
    </section>
  );
}
