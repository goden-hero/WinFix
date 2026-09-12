import React, { useState } from "react";

function formatBytes(bytes) {
  if (!bytes || bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

function ServiceBadge({ status, startupType }) {
  const isOk = status === "running";
  const isWarn = status === "stopped";
  const isBad = status === "disabled" || status === "missing";
  const badgeClass = isOk ? "status-ok" : isBad ? "status-bad" : "status-warn";

  return (
    <span className={`service-chip ${badgeClass}`}>
      <span className="svc-name">{status.toUpperCase()}</span>
      {startupType && startupType !== "unknown" && <small> ({startupType})</small>}
    </span>
  );
}

function EvidenceRow({ item }) {
  const [open, setOpen] = useState(false);

  const title = item.title || item.checked || "Diagnostic check";
  const description = item.description || item.result || "";
  const severity = item.severity || (item.status === "bad" ? "critical" : item.status === "warn" ? "warning" : "info");

  const statusClass = severity === "critical" ? "bad" : severity === "warning" ? "warn" : "good";
  const icon = statusClass === "bad" ? "✗" : statusClass === "warn" ? "⚠" : "✓";

  const data = item.data || {};
  const isWindowsUpdate = item.category === "windows_update" || data.services || data.pending_reboot !== undefined;

  return (
    <li className={`evidence-row ${statusClass}`}>
      <span className="evidence-icon" aria-hidden>{icon}</span>
      <div className="evidence-main">
        <div className="evidence-line">
          <strong className="evidence-title">{title}</strong>
          <span className={`evidence-badge ${statusClass}`}>{severity.toUpperCase()}</span>
        </div>
        <p className="evidence-description">{description}</p>

        {isWindowsUpdate && data.overall_service_health && (
          <div className="wu-status-summary">
            <span className={`health-pill ${data.overall_service_health}`}>
              Status: {data.overall_service_health.replace("_", " ").toUpperCase()}
            </span>
            {data.evidence_quality && (
              <small className="quality-tag">Quality: {data.evidence_quality.toUpperCase()}</small>
            )}
          </div>
        )}

        {open && (
          <div className="evidence-tech-details">
            {data.services && (
              <div className="wu-services-grid">
                <strong>Core Services Status:</strong>
                <ul>
                  {Object.entries(data.services).map(([key, svc]) => (
                    <li key={key} className="svc-row">
                      <span>{svc.display_name || key}:</span>
                      <ServiceBadge status={svc.status} startupType={svc.startup_type} />
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {data.pending_reboot !== undefined && (
              <div className="wu-reboot-info">
                <strong>Pending Reboot Status:</strong>{" "}
                <span className={data.pending_reboot ? "reboot-yes" : "reboot-no"}>
                  {data.status || (data.pending_reboot ? "REBOOT_PENDING" : "NO_REBOOT_PENDING")}
                </span>
                {data.reboot_reasons && data.reboot_reasons.length > 0 && (
                  <ul>
                    {data.reboot_reasons.map((reason, idx) => (
                      <li key={idx}>{reason}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}

            {data.cache_exists !== undefined && (
              <div className="wu-cache-info">
                <strong>Cache Metadata:</strong>
                <div>Path: <code>{data.target_directory || "Default"}</code></div>
                <div>Status: {data.cache_exists ? (data.cache_accessible ? "Accessible" : "Inaccessible") : "Does not exist"}</div>
                {data.cache_exists && (
                  <div>Size: {formatBytes(data.cache_size_bytes)} ({data.file_count || 0} files)</div>
                )}
              </div>
            )}

            {item.why && <p className="evidence-why">{item.why}</p>}
            <small className="muted-notice">Read-only diagnostic snapshot. No system changes were made.</small>
          </div>
        )}
      </div>
      <button type="button" className="tech-toggle" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        {open ? "▲ hide" : "▼ details"}
      </button>
    </li>
  );
}

export function EvidenceList({ evidence }) {
  if (!evidence || evidence.length === 0) return null;

  return (
    <section className="panel evidence-panel">
      <div className="panel-header">
        <h2>System Evidence Collected</h2>
        <span className="count-badge">{evidence.length} checks</span>
      </div>
      <ul className="evidence-list">
        {evidence.map((item, i) => (
          <EvidenceRow key={item.id || i} item={item} />
        ))}
      </ul>
    </section>
  );
}

export default EvidenceList;
