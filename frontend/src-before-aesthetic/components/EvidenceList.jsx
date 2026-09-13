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
  const topHogs = item.top_resource_consumers || data.top_resource_consumers || [];

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
          <div className="evidence-tech-details evidence-details">
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

            {(item.kind === "BATTERY_DIAGNOSIS" || data.kind === "BATTERY_DIAGNOSIS" || item.category === "battery") && data && (
              <div className="battery-details-box" style={{ marginTop: "10px", padding: "10px", background: "rgba(0,0,0,0.2)", borderRadius: "6px" }}>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", fontSize: "0.85rem" }}>
                  <div><strong>Power Source:</strong> {data.power_source ? data.power_source.toUpperCase() : "Unknown"}</div>
                  <div><strong>Charge Level:</strong> {data.charge_percent != null ? `${data.charge_percent}%` : "Unavailable"}</div>
                  <div><strong>Status:</strong> {data.is_charging === true ? "⚡ Charging" : data.is_charging === false ? "Discharging" : "Unknown"}</div>
                  <div><strong>Battery Saver:</strong> {data.battery_saver_enabled === true ? "Enabled" : data.battery_saver_enabled === false ? "Disabled" : "Unavailable"}</div>
                  {data.battery_health?.health_percent != null && (
                    <div><strong>Battery Health:</strong> {data.battery_health.health_percent}%</div>
                  )}
                  {data.power_plan && (
                    <div><strong>Power Plan:</strong> {data.power_plan}</div>
                  )}
                </div>
                {data.warnings && data.warnings.length > 0 && (
                  <div style={{ marginTop: "8px", fontSize: "0.82rem", color: "#f59e0b" }}>
                    <strong>Warnings:</strong>
                    <ul style={{ margin: "4px 0 0 16px", padding: 0 }}>
                      {data.warnings.map((w, idx) => (
                        <li key={idx}>{w}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {data.limitations && data.limitations.length > 0 && (
                  <div style={{ marginTop: "6px", fontSize: "0.8rem", opacity: 0.7 }}>
                    <strong>Limitations:</strong> {data.limitations.join("; ")}
                  </div>
                )}
              </div>
            )}
            {topHogs.length > 0 && (
              <div className="resource-hog-box">
                <div className="resource-hog-table">
                  <div className="resource-hog-header">
                    <span>Application</span>
                    <span>Procs</span>
                    <span>Raw CPU</span>
                    <span>RAM</span>
                    <span>Impact</span>
                  </div>
                  {topHogs.map((app, idx) => (
                    <div key={idx} className={`resource-hog-row impact-${(app.impact || "low").toLowerCase()}`}>
                      <span className="app-name"><strong>{app.name}</strong></span>
                      <span className="app-count">{app.process_count}</span>
                      <span className="app-cpu">{app.raw_cpu_percent}%</span>
                      <span className="app-ram">{app.memory_mb} MB ({app.memory_percent}%)</span>
                      <span className={`impact-badge impact-${(app.impact || "low").toLowerCase()}`}>
                        {app.impact_score} [{app.impact}]
                      </span>
                    </div>
                  ))}
                </div>
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
