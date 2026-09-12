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
    title:
      diagnosis.summary ||
      "Windows system issue detected",
    confidenceValue: Math.round(
      (diagnosis.overall_confidence ?? 0) * 100
    ),
    explanation:
      causes.length > 0
        ? causes
            .map(
              (cause) =>
                `${cause.title}: ${cause.explanation}`
            )
            .join(" ")
        : "WinFix analyzed the collected system evidence.",
  };
}

function normalizeEvidence(evidence = []) {
  return evidence.map((item) => {
    const severity = String(
      item.severity ?? ""
    ).toLowerCase();

    let status = "good";

    if (
      severity === "critical" ||
      severity === "high"
    ) {
      status = "bad";
    } else if (
      severity === "medium" ||
      severity === "warning" ||
      severity === "warn"
    ) {
      status = "warn";
    }

    return {
      checked:
        item.title ||
        item.category ||
        "System check",

      result: String(
        item.severity ||
        item.category ||
        "CHECKED"
      ).toUpperCase(),

      why:
        item.description ||
        item.source ||
        "Evidence collected by WinFix.",

      status,
    };
  });
}

function normalizePlan(actions = []) {
  return actions.map((action) => ({
    action_id: action.action_id,

    text:
      ACTION_LABELS[action.action_id] ??
      action.action_id,

    reason: action.reason,

    safe: true,
    admin: false,
    restart: false,
  }));
}

function getRepairSteps(status) {
  if (status === "approved") {
    return [
      {
        step: "Repair plan approved",
        detail: "Ready to execute",
        status: "done",
      },
      {
        step: "Execute approved remediation",
        detail: "Waiting for your confirmation",
        status: "running",
      },
    ];
  }

  if (status === "executing") {
    return [
      {
        step: "Repair plan approved",
        status: "done",
      },
      {
        step: "Executing approved remediation",
        detail: "WinFix agent is working",
        status: "running",
      },
      {
        step: "Verify system",
        status: "pending",
      },
    ];
  }

  if (status === "verifying") {
    return [
      {
        step: "Repair plan approved",
        status: "done",
      },
      {
        step: "Approved remediation executed",
        status: "done",
      },
      {
        step: "Verifying system state",
        detail: "Checking results",
        status: "running",
      },
    ];
  }

  return [];
}

export default function App() {
  const [phase, setPhase] = useState(PHASE.IDLE);
  const [problem, setProblem] = useState("");
  const [session, setSession] = useState(null);
  const [diagSteps, setDiagSteps] = useState([]);
  const [showApproval, setShowApproval] =
    useState(false);
  const [error, setError] = useState(null);

  const isWorking =
    phase === PHASE.DIAGNOSING ||
    phase === PHASE.REPAIRING;

  const handleDiagnose = useCallback(
    async (text) => {
      const value = (text ?? problem).trim();

      if (!value || isWorking) return;

      setError(null);
      setProblem(value);
      setSession(null);
      setDiagSteps([]);
      setShowApproval(false);
      setPhase(PHASE.DIAGNOSING);

      setDiagSteps([
        {
          step: "Connecting to Windows machine…",
          status: "running",
        },
      ]);

      try {
        const created =
          await winfixApi.createSession(value);

        setDiagSteps([
          {
            step: "Session created",
            detail: "WinFix agent connected",
            status: "done",
          },
          {
            step: "Gathering system evidence",
            detail: "Analyzing Windows state",
            status: "running",
          },
        ]);

        const diagnosed =
          await winfixApi.diagnose(
            created.session_id
          );

        setDiagSteps([
          {
            step: "Session created",
            detail: "WinFix agent connected",
            status: "done",
          },
          {
            step: "Gathering system evidence",
            status: "done",
          },
          {
            step: "Evaluating probable causes",
            status: "done",
          },
          {
            step: "Diagnosis complete",
            status: "done",
          },
        ]);

        setSession(diagnosed);
        setPhase(PHASE.DIAGNOSIS);
      } catch (err) {
        setError(
          err.message || "Diagnosis failed"
        );
        setPhase(PHASE.IDLE);
      }
    },
    [problem, isWorking]
  );

  const handleApprove = useCallback(
    async () => {
      if (!session) return;

      const actions =
        session.diagnosis
          ?.recommended_actions ?? [];

      if (actions.length === 0) {
        setShowApproval(false);
        return;
      }

      setShowApproval(false);
      setError(null);
      setPhase(PHASE.REPAIRING);

      try {
        const decisions = actions.map(
          (action) => ({
            action_id: action.action_id,
            approved: true,
          })
        );

        const updated =
          await winfixApi.approve(
            session.session_id,
            decisions
          );

        setSession(updated);
      } catch (err) {
        setError(
          err.message || "Approval failed"
        );
        setPhase(PHASE.DIAGNOSIS);
      }
    },
    [session]
  );

  const handleExecute = useCallback(
    async () => {
      if (!session || isWorking) return;

      setError(null);
      setPhase(PHASE.REPAIRING);

      try {
        const updated =
          await winfixApi.executeSession(
            session.session_id
          );

        setSession(updated);
      } catch (err) {
        setError(
          err.message || "Repair failed"
        );
        setPhase(PHASE.DIAGNOSIS);
      }
    },
    [session, isWorking]
  );

  const handleVerify = useCallback(
    async () => {
      if (!session || isWorking) return;

      setError(null);
      setPhase(PHASE.REPAIRING);

      try {
        const updated =
          await winfixApi.verifySession(
            session.session_id
          );

        setSession(updated);

        if (updated.status === "completed") {
          setPhase(PHASE.VERIFIED);
        }
      } catch (err) {
        setError(
          err.message || "Verification failed"
        );
      }
    },
    [session, isWorking]
  );

  const handleReset = useCallback(() => {
    setPhase(PHASE.IDLE);
    setProblem("");
    setSession(null);
    setDiagSteps([]);
    setShowApproval(false);
    setError(null);
  }, []);

  const diagnosis = normalizeDiagnosis(
    session?.diagnosis
  );

  const evidence = normalizeEvidence(
    session?.evidence ?? []
  );

  const plan = normalizePlan(
    session?.diagnosis
      ?.recommended_actions ?? []
  );

  const repairStatus =
    session?.status;

  return (
    <div
      className={`app phase-${phase}`}
    >
      <div
        className="ambient ambient-cyan"
        aria-hidden="true"
      />

      <div
        className="ambient ambient-violet"
        aria-hidden="true"
      />

      <div
        className="ambient ambient-blue"
        aria-hidden="true"
      />

      <div
        className="grid-glow"
        aria-hidden="true"
      />

      <div
        className="network network-left"
        aria-hidden="true"
      >
        <i />
        <i />
        <i />
        <i />
      </div>

      <div
        className="network network-right"
        aria-hidden="true"
      >
        <i />
        <i />
        <i />
        <i />
      </div>

      <header className="topbar">
        <div className="brand">
          <img
            className="brand-logo"
            src="/winfix-logo.png"
            alt="WinFix"
          />

          <span className="brand-tag">
            AI-powered Windows Diagnostics
          </span>
        </div>

        <div className="topbar-right">
          {session?.session_id && (
            <span className="session-chip">
              SESSION {session.session_id}
            </span>
          )}

          <span
            className={`status-pill online ${
              isWorking ? "working" : ""
            }`}
          >
            <span className="status-dot" />

            {isWorking
              ? "AGENT ACTIVE"
              : "SYSTEM ONLINE"}
          </span>
        </div>
      </header>

      <main className="main">

        {error && (
          <div
            className="error-banner"
            role="alert"
          >
            <span>⚠</span>

            {error}

            <button
              className="error-close"
              onClick={() =>
                setError(null)
              }
              aria-label="Dismiss"
            >
              ✕
            </button>
          </div>
        )}

        {phase === PHASE.IDLE && (
          <section className="card landing">

            <div className="hero-kicker">
              <span className="kicker-line" />

              AUTONOMOUS WINDOWS AGENT

              <span className="kicker-line" />
            </div>

            <div className="landing-head">
              <h1>
                What is wrong with your{" "}
                <span>Windows PC?</span>
              </h1>

              <p className="subtitle">
                Describe the problem and let WinFix
                diagnose, plan, and repair it.
              </p>
            </div>

            <ProblemInput
              value={problem}
              onChange={setProblem}
              onDiagnose={handleDiagnose}
            />

            <QuickIssues
              onSelect={handleDiagnose}
            />

            <div className="trust-strip">
              <span>
                <b>01</b> Detect
              </span>

              <span>
                <b>02</b> Diagnose
              </span>

              <span>
                <b>03</b> Repair
              </span>

              <span>
                <b>04</b> Verify
              </span>
            </div>

          </section>
        )}

        {phase === PHASE.DIAGNOSING && (
          <DiagnosisProgress
            steps={diagSteps}
            problem={problem}
          />
        )}

        {phase === PHASE.DIAGNOSIS &&
          diagnosis && (
            <>
              <DiagnosisResult
                diagnosis={diagnosis}
              />

              <EvidenceList
                evidence={evidence}
              />

              <Plan
                plan={plan}
                onApprove={() =>
                  setShowApproval(true)
                }
              />

              <ApprovalDialog
                open={showApproval}
                plan={plan}
                onCancel={() =>
                  setShowApproval(false)
                }
                onConfirm={handleApprove}
              />
            </>
          )}

        {phase === PHASE.REPAIRING && (
          <>
            <RepairProgress
              steps={getRepairSteps(
                repairStatus
              )}
            />

            <section className="card plan-card">
              <div className="plan-actions">

                {repairStatus ===
                  "approved" && (
                  <>
                    <p className="plan-note">
                      Your approved repair plan
                      is ready to execute.
                    </p>

                    <button
                      type="button"
                      className="btn btn-primary btn-lg"
                      onClick={handleExecute}
                    >
                      🔧 Execute Approved Repair
                    </button>
                  </>
                )}

                {repairStatus ===
                  "executing" && (
                  <p className="plan-note">
                    ⚙ WinFix is executing the
                    approved remediation...
                  </p>
                )}

                {repairStatus ===
                  "verifying" && (
                  <>
                    <p className="plan-note">
                      ✓ Repair completed. WinFix
                      is ready to verify the system.
                    </p>

                    <button
                      type="button"
                      className="btn btn-primary btn-lg"
                      onClick={handleVerify}
                    >
                      ✓ Verify System
                    </button>
                  </>
                )}

              </div>
            </section>
          </>
        )}

        {phase === PHASE.VERIFIED && (
          <VerificationResult
            verification={{
              status: "fixed",
              title: "Fix successful",
              message:
                "WinFix completed the approved repair and verification workflow.",
            }}
            sessionId={
              session?.session_id
            }
            onRestart={handleReset}
          />
        )}

      </main>

      <footer className="footer">
        <span className="footer-dot" />

        WinFix · Autonomous Windows
        troubleshooting agent
      </footer>
    </div>
  );
}