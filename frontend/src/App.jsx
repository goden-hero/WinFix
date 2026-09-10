import { useState } from "react";
import { winfixApi } from "./api/client";
import { EvidenceList } from "./components/EvidenceList";
import { Plan } from "./components/Plan";
import { ExecutionView } from "./components/ExecutionView";
import { VerificationView } from "./components/VerificationView";
import "./styles.css";

const steps = ["Problem", "Investigation", "Diagnosis", "Plan", "Approval", "Execution", "Verification"];

function getActiveStepIndex(session, busy) {
  if (!session) return 0;
  if (busy && session.status === "created") return 1;
  switch (session.status) {
    case "created": return 0;
    case "diagnosing": return 1;
    case "diagnosed":
    case "awaiting_approval": return 3;
    case "approved": return 4;
    case "executing": return 5;
    case "verifying": return 5;
    case "completed": return 6;
    default: return 3;
  }
}

export default function App() {
  const [problem, setProblem] = useState("My PC is slow");
  const [session, setSession] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function startInvestigation(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const created = await winfixApi.createSession(problem);
      setSession(await winfixApi.diagnose(created.session_id));
    } catch (cause) {
      setError(cause.message);
    } finally {
      setBusy(false);
    }
  }

  async function approve(actionId) {
    setBusy(true);
    setError("");
    try {
      setSession(await winfixApi.approve(session.session_id, [{ action_id: actionId, approved: true }]));
    } catch (cause) {
      setError(cause.message);
    } finally {
      setBusy(false);
    }
  }

  async function execute() {
    if (!session) return;
    setBusy(true);
    setError("");
    try {
      const updated = await winfixApi.executeSession(session.session_id);
      setSession(updated);
    } catch (cause) {
      setError(cause.message);
    } finally {
      setBusy(false);
    }
  }

  async function verify() {
    if (!session) return;
    setBusy(true);
    setError("");
    try {
      const updated = await winfixApi.verifySession(session.session_id);
      setSession(updated);
    } catch (cause) {
      setError(cause.message);
    } finally {
      setBusy(false);
    }
  }

  const diagnosis = session?.diagnosis;
  const activeStep = getActiveStepIndex(session, busy);

  return (
    <main>
      <header>
        <div className="brand">
          <span>W</span>
          <div>
            <strong>WinFix Agent</strong>
            <small>Windows system intelligence</small>
          </div>
        </div>
        <div className="status-dot">
          {session ? `Session: ${session.status.toUpperCase()}` : "Local session"}
        </div>
      </header>

      <nav aria-label="Workflow">
        {steps.map((step, index) => (
          <div className={index <= activeStep ? "active" : ""} key={step}>
            <b>{String(index + 1).padStart(2, "0")}</b>
            {step}
          </div>
        ))}
      </nav>

      <section className="hero">
        <p className="eyebrow">SYSTEM DIAGNOSTICS & REMEDIATION</p>
        <h1>What's wrong with your PC?</h1>
        <p>Describe the issue. WinFix gathers evidence, explains likely causes, and asks before executing safe, verified remediations.</p>
        <form onSubmit={startInvestigation}>
          <textarea
            value={problem}
            onChange={(event) => setProblem(event.target.value)}
            aria-label="Describe your Windows issue"
          />
          <button disabled={busy}>{busy ? "Investigating..." : "Investigate system"}</button>
        </form>
        {error && <p className="error">{error}</p>}
      </section>

      {busy && (
        <section className="investigating">
          <span className="pulse" />
          <div>
            <b>Processing workflow</b>
            <p>Gathering evidence, evaluating safety rules, or performing bounded system operations.</p>
          </div>
        </section>
      )}

      {diagnosis && (
        <section className="results">
          <section className="panel diagnosis">
            <span className="confidence">{Math.round(diagnosis.overall_confidence * 100)}% confidence</span>
            <h2>{diagnosis.summary}</h2>
            <div className="causes">
              {diagnosis.probable_causes.map((cause) => (
                <article key={cause.title}>
                  <h3>{cause.title}</h3>
                  <p>{cause.explanation}</p>
                </article>
              ))}
            </div>
            <p className="muted">Analysis: {diagnosis.generated_by}</p>
          </section>

          <EvidenceList evidence={session.evidence} />

          <Plan actions={diagnosis.recommended_actions} onApprove={approve} busy={busy} />

          <ExecutionView
            results={session.execution_results}
            onExecute={execute}
            onVerify={verify}
            status={session.status}
            busy={busy}
          />

          <VerificationView results={session.verification_results} />
        </section>
      )}
    </main>
  );
}
