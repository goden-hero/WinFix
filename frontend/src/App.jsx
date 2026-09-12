import React, { useState, useCallback } from "react";
import { winfixApi } from "./api/client.js";

import ProblemInput from "./components/ProblemInput.jsx";
import QuickIssues from "./components/QuickIssues.jsx";
import DiagnosisProgress from "./components/DiagnosisProgress.jsx";
import DiagnosisResult from "./components/DiagnosisResult.jsx";
import EvidenceList from "./components/EvidenceList.jsx";
import Plan from "./components/Plan.jsx";
import ApprovalDialog from "./components/ApprovalDialog.jsx";
import RepairProgress from "./components/RepairProgress.jsx";
import VerificationResult from "./components/VerificationResult.jsx";

import "./styles.css";

const PHASE = {
  IDLE: "idle",
  DIAGNOSING: "diagnosing",
  DIAGNOSIS: "diagnosis",
  REPAIRING: "repairing",
  VERIFIED: "verified",
};

const ACTION_LABELS = {
  clear_temp_files: "Clear approved temporary files",
  disable_startup_app: "Disable a startup application",
  remove_optional_app: "Remove an optional application",
  apply_privacy_profile: "Apply a privacy profile",
  run_sfc_scan: "Run System File Checker",
  run_dism_health_check: "Run DISM health check",
};

function normalizeDiagnosis(diagnosis) {
  if (!diagnosis) return null;
  const causes = diagnosis.probable_causes ?? [];

  return {
    severity: "Medium",
    title: diagnosis.summary || "Windows system issue detected",
    confidenceValue: Math.round((diagnosis.overall_confidence ?? 0) * 100),
    explanation:
      causes.length > 0
        ? causes.map((cause) => `${cause.title}: ${cause.explanation}`).join(" ")
        : "WinFix analyzed the collected system evidence.",
  };
}

function normalizeEvidence(evidence = []) {
  return evidence.map((item) => {
    const severity = String(item.severity ?? "").toLowerCase();
    let status = "good";

    if (severity === "critical" || severity === "high") status = "bad";
    else if (severity === "medium" || severity === "warning" || severity === "warn") status = "warn";

    return {
      checked: item.title || item.category || "System check",
      result: String(item.severity || item.category || "CHECKED").toUpperCase(),
      why: item.description || item.source || "Evidence collected by WinFix.",
      status,
    };
  });
}

function normalizePlan(actions = []) {
  return actions.map((action) => ({
    action_id: action.action_id,
    text: ACTION_LABELS[action.action_id] ?? action.action_id,
    reason: action.reason,
    safe: true,
    admin: false,
    restart: false,
  }));
}

function getRepairSteps(status) {
  if (status === "approved") {
    return [
      { step: "Repair plan approved", detail: "Ready to execute", status: "done" },
      { step: "Execute approved remediation", detail: "Waiting for your confirmation", status: "running" },
    ];
  }

  if (status === "executing") {
    return [
      { step: "Repair plan approved", status: "done" },
      { step: "Executing approved remediation", detail: "WinFix agent is working", status: "running" },
      { step: "Verify system", status: "pending" },
    ];
  }

  if (status === "verifying") {
    return [
      { step: "Repair plan approved", status: "done" },
      { step: "Approved remediation executed", status: "done" },
      { step: "Verifying system state", detail: "Checking results", status: "running" },
    ];
  }

  return [];
}

function SearchIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="10.8" cy="10.8" r="6.4" />
      <path d="m16 16 5 5" />
    </svg>
  );
}

function ArrowIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 12h15" />
      <path d="m13 6 6 6-6 6" />
    </svg>
  );
}

function WindowIcon({ type }) {
  if (type === "min") return <span className="window-control min" />;
  if (type === "max") return <span className="window-control max" />;
  return <span className="window-control close" />;
}

function SettingsPanel({ settings, onChange, onClose }) {
  return (
    <div className="settings-overlay" role="dialog" aria-modal="true" aria-label="WinFix settings">
      <div className="settings-panel">
        <div className="settings-head">
          <div>
            <span className="settings-eyebrow">WINFIX CONFIGURATION</span>
            <h2>Settings</h2>
            <p>Choose how WinFix connects to your local agent.</p>
          </div>
          <button type="button" className="settings-close" onClick={onClose} aria-label="Close settings">×</button>
        </div>

        <div className="settings-section">
          <label>API endpoint</label>
          <div className="settings-field">
            <span className="field-status" />
            <input
              value={settings.api}
              onChange={(e) => onChange("api", e.target.value)}
              spellCheck="false"
            />
          </div>
        </div>

        <div className="settings-grid">
          <label className="settings-select">
            <span>GPU</span>
            <select value={settings.gpu} onChange={(e) => onChange("gpu", e.target.value)}>
              <option>Auto detect</option>
              <option>NVIDIA GPU</option>
              <option>AMD GPU</option>
              <option>Intel GPU</option>
              <option>CPU only</option>
            </select>
          </label>

          <label className="settings-select">
            <span>Model</span>
            <select value={settings.model} onChange={(e) => onChange("model", e.target.value)}>
              <option>WinFix Auto</option>
              <option>Fast</option>
              <option>Balanced</option>
              <option>Deep diagnosis</option>
            </select>
          </label>
        </div>

        <div className="settings-footer">
          <span><i /> Changes are saved for this session</span>
          <button type="button" className="settings-done" onClick={onClose}>Done</button>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const [phase, setPhase] = useState(PHASE.IDLE);
  const [problem, setProblem] = useState("");
  const [session, setSession] = useState(null);
  const [diagSteps, setDiagSteps] = useState([]);
  const [showApproval, setShowApproval] = useState(false);
  const [error, setError] = useState(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settings, setSettings] = useState({
    api:
      typeof window !== "undefined"
        ? window.localStorage.getItem("winfix_api_base") ||
          import.meta.env.VITE_API_BASE_URL ||
          "http://127.0.0.1:9000/api/v1"
        : import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:9000/api/v1",
    gpu: "Auto detect",
    model: "WinFix Auto",
  });

  const isWorking = phase === PHASE.DIAGNOSING || phase === PHASE.REPAIRING;

  const handleDiagnose = useCallback(async (text) => {
    const value = (text ?? problem).trim();
    if (!value || isWorking) return;

    setError(null);
    setProblem(value);
    setSession(null);
    setDiagSteps([{ step: "Connecting to Windows machine…", status: "running" }]);
    setShowApproval(false);
    setPhase(PHASE.DIAGNOSING);

    try {
      const created = await winfixApi.createSession(value);

      setDiagSteps([
        { step: "Session created", detail: "WinFix agent connected", status: "done" },
        { step: "Gathering system evidence", detail: "Analyzing Windows state", status: "running" },
      ]);

      const diagnosed = await winfixApi.diagnose(created.session_id);

      setDiagSteps([
        { step: "Session created", detail: "WinFix agent connected", status: "done" },
        { step: "Gathering system evidence", status: "done" },
        { step: "Evaluating probable causes", status: "done" },
        { step: "Diagnosis complete", status: "done" },
      ]);

      setSession(diagnosed);
      setPhase(PHASE.DIAGNOSIS);
    } catch (err) {
      setError(err.message || "Diagnosis failed");
      setPhase(PHASE.IDLE);
    }
  }, [problem, isWorking]);

  const handleApprove = useCallback(async () => {
    if (!session) return;

    const actions = session.diagnosis?.recommended_actions ?? [];
    if (actions.length === 0) {
      setShowApproval(false);
      return;
    }

    setShowApproval(false);
    setError(null);
    setPhase(PHASE.REPAIRING);

    try {
      const decisions = actions.map((action) => ({
        action_id: action.action_id,
        approved: true,
      }));

      const updated = await winfixApi.approve(session.session_id, decisions);
      setSession(updated);
    } catch (err) {
      setError(err.message || "Approval failed");
      setPhase(PHASE.DIAGNOSIS);
    }
  }, [session]);

  const handleExecute = useCallback(async () => {
    if (!session || isWorking) return;
    setError(null);
    setPhase(PHASE.REPAIRING);

    try {
      const updated = await winfixApi.executeSession(session.session_id);
      setSession(updated);
    } catch (err) {
      setError(err.message || "Repair failed");
      setPhase(PHASE.DIAGNOSIS);
    }
  }, [session, isWorking]);

  const handleVerify = useCallback(async () => {
    if (!session || isWorking) return;
    setError(null);
    setPhase(PHASE.REPAIRING);

    try {
      const updated = await winfixApi.verifySession(session.session_id);
      setSession(updated);
      if (updated.status === "completed") setPhase(PHASE.VERIFIED);
    } catch (err) {
      setError(err.message || "Verification failed");
    }
  }, [session, isWorking]);

  const handleReset = useCallback(() => {
    setPhase(PHASE.IDLE);
    setProblem("");
    setSession(null);
    setDiagSteps([]);
    setShowApproval(false);
    setError(null);
  }, []);

  const diagnosis = normalizeDiagnosis(session?.diagnosis);
  const evidence = normalizeEvidence(session?.evidence ?? []);
  const plan = normalizePlan(session?.diagnosis?.recommended_actions ?? []);
  const repairStatus = session?.status;

  const updateSetting = (key, value) => {
    setSettings((current) => ({ ...current, [key]: value }));
    if (key === "api" && typeof window !== "undefined") {
      window.localStorage.setItem("winfix_api_base", value.trim());
    }
  };

  return (
    <div className={`app phase-${phase}`}>
      <div className="window-shell">
        <div className="decor-orb orb-top" aria-hidden="true" />
        <div className="decor-orb orb-left" aria-hidden="true" />
        <div className="decor-orb orb-bottom" aria-hidden="true" />

        <header className="topbar">
          <div className="brand">
            <div className="brand-mark" aria-hidden="true">
              <svg viewBox="0 0 64 64">
                <path d="M12 16 28 32 12 48" fill="none" stroke="currentColor" strokeWidth="7" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M52 16 36 32 52 48" fill="none" stroke="currentColor" strokeWidth="7" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M17 11 53 47" fill="none" stroke="currentColor" strokeWidth="7" strokeLinecap="round"/>
                <path d="m45 13 7-2-2 7" fill="none" stroke="currentColor" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M19 51 9 55l4-10" fill="none" stroke="currentColor" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <div className="brand-divider" />
            <div className="brand-copy">
              <div className="brand-name">WinFix</div>
              <div className="brand-tag">AI powered windows system diagnostics</div>
            </div>
          </div>

          <div className="topbar-right">
            <span className="status-pill">
              <span className="status-dot" />
              connected
            </span>
            <div className="window-controls" aria-hidden="true">
              <WindowIcon type="min" />
              <WindowIcon type="max" />
              <WindowIcon type="close" />
            </div>
          </div>
        </header>

        <div className="workspace">
          <aside className="sidebar">
            <div className="sidebar-title">Common Problem</div>

            <QuickIssues onSelect={handleDiagnose} />

            <button type="button" className={`settings-nav ${settingsOpen ? "active" : ""}`} onClick={() => setSettingsOpen(true)}>
              <span className="settings-nav-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24"><path d="M12 8.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7Z"/><path d="m19.4 15 .1.1a1.8 1.8 0 0 1-2.5 2.5l-.1-.1a1.8 1.8 0 0 0-3 .9v.2a1.8 1.8 0 0 1-3.6 0v-.2a1.8 1.8 0 0 0-3-.9l-.1.1a1.8 1.8 0 0 1-2.5-2.5l.1-.1a1.8 1.8 0 0 0-.9-3h-.2a1.8 1.8 0 0 1 0-3.6H4a1.8 1.8 0 0 0 .9-3l-.1-.1a1.8 1.8 0 0 1 2.5-2.5l.1.1a1.8 1.8 0 0 0 3-.9v-.2a1.8 1.8 0 0 1 3.6 0V4a1.8 1.8 0 0 0 3 .9l.1-.1a1.8 1.8 0 0 1 2.5 2.5l-.1.1a1.8 1.8 0 0 0 .9 3h.2a1.8 1.8 0 0 1 0 3.6h-.2a1.8 1.8 0 0 0-.9 3Z"/></svg>
              </span>
              Settings
            </button>
          </aside>

          <main className="main">
            {error && (
              <div className="error-banner" role="alert">
                <span>⚠</span>
                {error}
                <button className="error-close" onClick={() => setError(null)} aria-label="Dismiss">✕</button>
              </div>
            )}

            {phase === PHASE.IDLE && (
              <section className="landing">
                <div className="landing-head">
                  <h1>What can we fix today?</h1>
                  <p className="subtitle">Describe your problem and WinFix will find the right solution</p>
                </div>

                <ProblemInput value={problem} onChange={setProblem} onDiagnose={handleDiagnose} />

                <div className="landing-spacer" />
              </section>
            )}

            {phase === PHASE.DIAGNOSING && (
              <DiagnosisProgress steps={diagSteps} problem={problem} />
            )}

            {phase === PHASE.DIAGNOSIS && diagnosis && (
              <>
                <DiagnosisResult diagnosis={diagnosis} />
                <EvidenceList evidence={evidence} />
                <Plan plan={plan} onApprove={() => setShowApproval(true)} />
              </>
            )}

            {phase === PHASE.REPAIRING && (
              <>
                <RepairProgress steps={getRepairSteps(repairStatus)} />
                {repairStatus === "approved" && (
                  <div className="action-bar">
                    <button type="button" className="btn btn-primary btn-lg" onClick={handleExecute} disabled={isWorking}>
                      Execute Approved Repair
                      <ArrowIcon />
                    </button>
                  </div>
                )}
                {repairStatus === "executing" && (
                  <div className="action-bar">
                    <button type="button" className="btn btn-primary btn-lg" onClick={handleVerify} disabled={isWorking}>
                      Verify System
                      <ArrowIcon />
                    </button>
                  </div>
                )}
              </>
            )}

            {phase === PHASE.VERIFIED && session?.verification_results && (
              <VerificationResult
                verification={session.verification_results}
                sessionId={session.session_id}
                onRestart={handleReset}
              />
            )}

            {session?.status === "failed" && (
              <div className="card">
                <h2>WinFix could not complete the requested operation.</h2>
                <button type="button" className="btn btn-ghost" onClick={handleReset}>Start again</button>
              </div>
            )}
          </main>
        </div>
      </div>

      <ApprovalDialog
        open={showApproval}
        plan={plan}
        onCancel={() => setShowApproval(false)}
        onConfirm={handleApprove}
      />

      {settingsOpen && (
        <SettingsPanel
          settings={settings}
          onChange={updateSetting}
          onClose={() => setSettingsOpen(false)}
        />
      )}
    </div>
  );
}
