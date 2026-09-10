import { formatBytes } from "./ExecutionView";

export function VerificationView({ results }) {
  if (!results || results.length === 0) return null;

  return (
    <section className="panel verification-panel">
      <h2>Independent Verification</h2>
      <p className="panel-subtitle">Independent filesystem inspection comparing baseline before execution with current state.</p>
      <div className="verification-list">
        {results.map((res, idx) => {
          const reclaimedBytes = Math.max(0, (res.before?.bytes ?? 0) - (res.after?.bytes ?? 0));
          return (
            <article className="verification-card" key={idx}>
              <div className="verification-header">
                <span className={`verification-badge ${res.status}`}>{res.status.toUpperCase()}</span>
                <h3>Temporary Storage Metrics</h3>
              </div>

              <div className="before-after-grid">
                <div className="state-box before">
                  <small>BEFORE EXECUTION</small>
                  <div className="metric-val">{formatBytes(res.before?.bytes)}</div>
                  <div className="metric-sub">{res.before?.files ?? 0} files</div>
                </div>

                <div className="arrow-divider">→</div>

                <div className="state-box after">
                  <small>AFTER EXECUTION</small>
                  <div className="metric-val">{formatBytes(res.after?.bytes)}</div>
                  <div className="metric-sub">{res.after?.files ?? 0} files</div>
                </div>
              </div>

              <div className="verification-summary">
                <span className="success-tag">✓ {formatBytes(reclaimedBytes)} reclaimed</span>
                <p>{res.summary}</p>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
