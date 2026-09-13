import React, { useCallback, useMemo, useState } from "react";
import { winfixApi } from "./api/client.js";
import "./styles.css";

const PHASE = { IDLE: "idle", DIAGNOSING: "diagnosing", DIAGNOSIS: "diagnosis", REPAIRING: "repairing", VERIFIED: "verified" };
const ACTION_LABELS = {
  clear_temp_files: "Clear approved temporary files",
  disable_startup_app: "Disable a startup application",
  remove_optional_app: "Remove an optional application",
  apply_privacy_profile: "Apply a privacy profile",
  run_sfc_scan: "Run System File Checker",
  run_dism_health_check: "Run DISM health check",
};
const QUICK = [
  ["audio", "Audio", "My sound isn’t working..."],
  ["wifi", "WiFi problem", "My WiFi keeps disconnecting..."],
  ["slow", "PC slow", "My PC is running very slowly..."],
  ["apps", "Apps not responding", "My apps keep freezing..."],
  ["display", "Display problem", "My display has a problem..."],
];

function Icon({ name, size = 24, stroke = 2 }) {
  const p = { width: size, height: size, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: stroke, strokeLinecap: "round", strokeLinejoin: "round", "aria-hidden": true };
  const paths = {
    settings: <><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-1.42 1.42-.06-.06a1.7 1.7 0 0 0-1.88-.34 1.7 1.7 0 0 0-1.04 1.56V21h-2v-.48A1.7 1.7 0 0 0 12.36 19a1.7 1.7 0 0 0-1.88.34l-.06.06L9 17.98l.06-.06A1.7 1.7 0 0 0 9.4 16a1.7 1.7 0 0 0-1.56-1H7v-2h.84A1.7 1.7 0 0 0 9.4 12a1.7 1.7 0 0 0-.34-1.88L9 10.06 10.42 8.64l.06.06A1.7 1.7 0 0 0 12.36 9a1.7 1.7 0 0 0 1.04-1.56V7h2v.44A1.7 1.7 0 0 0 16.44 9a1.7 1.7 0 0 0 1.88-.34l.06-.06 1.42 1.42-.06.06A1.7 1.7 0 0 0 19.4 12a1.7 1.7 0 0 0 1.56 1H21v2h-.84A1.7 1.7 0 0 0 19.4 15Z"/></>,
    audio: <><path d="M11 5 6 9H3v6h3l5 4V5Z"/><path d="M15.5 8.5a5 5 0 0 1 0 7M18.5 5.5a9 9 0 0 1 0 13"/></>,
    wifi: <><path d="M3 8.5a14 14 0 0 1 18 0"/><path d="M6.5 12a9 9 0 0 1 11 0"/><path d="M10 15.5a4 4 0 0 1 4 0"/><circle cx="12" cy="19" r="1" fill="currentColor" stroke="none"/></>,
    slow: <><path d="M4 16a8 8 0 0 1 16 0"/><path d="M8 16c0-2.2 1.8-4 4-4s4 1.8 4 4"/><path d="M4 19h16"/></>,
    apps: <><rect x="5" y="4" width="14" height="16" rx="2"/><path d="M8 8h8M8 12h5M8 16h3"/></>,
    display: <><rect x="6" y="2.5" width="12" height="19" rx="2"/><path d="M10 18.5h4"/></>,
    arrow: <><path d="M5 12h14"/><path d="m13 6 6 6-6 6"/></>,
    back: <><path d="m15 18-6-6 6-6"/><path d="M9 12h10"/></>,
    link: <><path d="m9 15 6-6"/><path d="M7 17H5a3 3 0 0 1 0-6h3"/><path d="M17 7h2a3 3 0 0 1 0 6h-3"/></>,
    cube: <><path d="m12 3 8 4.5v9L12 21l-8-4.5v-9L12 3Z"/><path d="m4 7.5 8 4.5 8-4.5M12 12v9"/></>,
    chip: <><rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 9h6v6H9zM9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4"/></>,
    search: <><circle cx="10.8" cy="10.8" r="6.8"/><path d="m16 16 5 5"/></>,
    message: <path d="M4 5.5A2.5 2.5 0 0 1 6.5 3h11A2.5 2.5 0 0 1 20 5.5v7a2.5 2.5 0 0 1-2.5 2.5H10l-5 4v-4.7A2.5 2.5 0 0 1 4 12.5v-7Z"/>,
    check: <><circle cx="12" cy="12" r="9"/><path d="m8 12 2.5 2.5L16 9"/></>,
    eyeoff: <><path d="M3 3l18 18"/><path d="M10.6 10.6a2 2 0 0 0 2.8 2.8"/><path d="M9.9 4.3A10.7 10.7 0 0 1 12 4c5 0 8.5 4 9.5 6-.4.8-1.3 2.1-2.8 3.3M6.6 6.6C4.6 8 3.3 9.7 2.5 10c1 2 4.5 6 9.5 6 1 0 1.9-.2 2.7-.5"/></>,
    info: <><circle cx="12" cy="12" r="9"/><path d="M12 10v6M12 7h.01"/></>,
    save: <><path d="M5 4h12l2 2v14H5z"/><path d="M8 4v6h8V4M8 20v-6h8v6"/></>,
    sparkle: <><path d="m12 3 1.4 4.6L18 9l-4.6 1.4L12 15l-1.4-4.6L6 9l4.6-1.4L12 3Z"/><path d="m19 14 .7 2.3L22 17l-2.3.7L19 20l-.7-2.3L16 17l2.3-.7L19 14Z"/></>,
  };
  return <svg {...p}>{paths[name] ?? paths.settings}</svg>;
}

function normalizeDiagnosis(d) {
  if (!d) return null;
  const causes = d.probable_causes ?? [];
  return { severity: "Medium", title: d.summary || "Windows system issue detected", confidenceValue: Math.round((d.overall_confidence ?? 0) * 100), explanation: causes.length ? causes.map(c => `${c.title}: ${c.explanation}`).join(" ") : "WinFix analyzed the collected system evidence." };
}
function normalizeEvidence(items = []) {
  return items.map(i => {
    const sev = String(i.severity ?? "").toLowerCase();
    return { checked: i.title || i.category || "System check", result: String(i.severity || i.category || "CHECKED").toUpperCase(), why: i.description || i.source || "Evidence collected by WinFix.", status: ["critical", "high"].includes(sev) ? "bad" : ["medium", "warning", "warn"].includes(sev) ? "warn" : "good" };
  });
}
function normalizePlan(actions = []) { return actions.map(a => ({ action_id: a.action_id, text: ACTION_LABELS[a.action_id] ?? a.action_id, reason: a.reason })); }
function repairSteps(status) {
  if (status === "approved") return [{ step: "Repair plan approved", detail: "Ready to execute", status: "done" }, { step: "Execute approved remediation", detail: "Waiting for your confirmation", status: "running" }];
  if (status === "executing") return [{ step: "Repair plan approved", status: "done" }, { step: "Executing approved remediation", detail: "WinFix agent is working", status: "running" }, { step: "Verify system", status: "pending" }];
  if (status === "verifying") return [{ step: "Repair plan approved", status: "done" }, { step: "Approved remediation executed", status: "done" }, { step: "Verifying system state", detail: "Checking results", status: "running" }];
  return [];
}

export default function App() {
  const [phase, setPhase] = useState(PHASE.IDLE);
  const [view, setView] = useState("home");
  const [problem, setProblem] = useState("");
  const [session, setSession] = useState(null);
  const [diagSteps, setDiagSteps] = useState([]);
  const [showApproval, setShowApproval] = useState(false);
  const [error, setError] = useState(null);
  const [prefs, setPrefs] = useState(() => ({ provider: localStorage.getItem("winfix-provider") || "OpenAI", apiKey: localStorage.getItem("winfix-api-key") || "", model: localStorage.getItem("winfix-model") || "GPT-4o", gpu: localStorage.getItem("winfix-gpu") || "NVIDIA GeForce RTX 4060", gpuEnabled: localStorage.getItem("winfix-gpu-enabled") !== "false" }));
  const [saved, setSaved] = useState(false);

  const isWorking = phase === PHASE.DIAGNOSING || phase === PHASE.REPAIRING;
  const diagnosis = normalizeDiagnosis(session?.diagnosis);
  const evidence = normalizeEvidence(session?.evidence ?? []);
  const plan = normalizePlan(session?.diagnosis?.recommended_actions ?? []);

  const savePrefs = () => {
    localStorage.setItem("winfix-provider", prefs.provider); localStorage.setItem("winfix-api-key", prefs.apiKey); localStorage.setItem("winfix-model", prefs.model); localStorage.setItem("winfix-gpu", prefs.gpu); localStorage.setItem("winfix-gpu-enabled", String(prefs.gpuEnabled));
    setSaved(true); setTimeout(() => setSaved(false), 1800);
  };

  const diagnose = useCallback(async (text) => {
    const value = (text ?? problem).trim(); if (!value || isWorking) return;
    setError(null); setProblem(value); setSession(null); setDiagSteps([{ step: "Connecting to Windows machine…", status: "running" }]); setView("home"); setPhase(PHASE.DIAGNOSING);
    try {
      const created = await winfixApi.createSession(value);
      setDiagSteps([{ step: "Connected to Windows machine", status: "done" }, { step: "Checking system information", status: "done" }, { step: "Inspecting Windows services", status: "running" }]);
      const diagnosed = await winfixApi.diagnose(created.session_id);
      setDiagSteps([{ step: "Connected to Windows machine", status: "done" }, { step: "Checking system information", status: "done" }, { step: "Inspecting Windows services", status: "done" }, { step: "Analyzing possible causes", status: "done" }, { step: "Diagnosis complete", status: "done" }]);
      setSession(diagnosed); setPhase(PHASE.DIAGNOSIS);
    } catch (e) { setError(e.message || "Diagnosis failed"); setPhase(PHASE.IDLE); }
  }, [problem, isWorking]);

  const approve = useCallback(async () => {
    if (!session) return;
    const actions = session.diagnosis?.recommended_actions ?? [];
    setShowApproval(false); setError(null);
    try { const updated = await winfixApi.approve(session.session_id, actions.map(a => ({ action_id: a.action_id, approved: true }))); setSession(updated); setPhase(PHASE.REPAIRING); }
    catch (e) { setError(e.message || "Approval failed"); }
  }, [session]);
  const execute = useCallback(async () => { if (!session) return; setError(null); setPhase(PHASE.REPAIRING); try { setSession(await winfixApi.executeSession(session.session_id)); } catch (e) { setError(e.message || "Repair failed"); } }, [session]);
  const verify = useCallback(async () => { if (!session) return; setError(null); try { const u = await winfixApi.verifySession(session.session_id); setSession(u); if (u.status === "completed") setPhase(PHASE.VERIFIED); } catch (e) { setError(e.message || "Verification failed"); } }, [session]);
  const reset = () => { setPhase(PHASE.IDLE); setView("home"); setProblem(""); setSession(null); setDiagSteps([]); setError(null); };

  const title = useMemo(() => phase === PHASE.IDLE ? "home" : phase, [phase]);

  return <div className={`app phase-${title}`}>
    <div className="orb orb-a"/><div className="orb orb-b"/><div className="orb orb-c"/><div className="orb orb-d"/>
    <header className="topbar">
      <div className="brand"><div className="brand-mark"><img src="/winfix-header-mark.png" alt="WinFix" /></div><div className="brand-divider"/><div><div className="brand-name">WinFix</div><div className="brand-tag">AI powered windows system diagnostics</div></div></div>
      <div className="topbar-right"><div className="connected"><span className="connected-dot"/>connected</div><div className="window-controls"><span>—</span><span>□</span><span>×</span></div></div>
    </header>

    <div className="shell">
      <aside className="sidebar">
        <button className={`settings-tile ${view === "settings" ? "active" : ""}`} onClick={() => { setView("settings"); setPhase(PHASE.IDLE); }}><Icon name="settings" size={33}/><span><b>Settings</b><small>API, GPU and model preferences</small></span><Icon name="arrow" size={22}/></button>
        <div className="side-heading">Common Problems</div>
        <nav className="issue-list">{QUICK.map(([id,label,text], i) => <button key={id} className={`issue ${i === 0 ? "active" : ""}`} onClick={() => diagnose(text)}><Icon name={id} size={29}/><span>{label}</span></button>)}</nav>
        <div className="sidebar-quote"><br/><br/><div/></div>
      </aside>

      <main className="content">
        {error && <div className="error-banner"><span>⚠ {error}</span><button onClick={() => setError(null)}>×</button></div>}
        {view === "settings" && <Settings prefs={prefs} setPrefs={setPrefs} onBack={() => setView("home")} onSave={savePrefs} saved={saved}/>} 
        {view === "home" && phase === PHASE.IDLE && <Home problem={problem} setProblem={setProblem} diagnose={diagnose}/>} 
        {view === "home" && phase === PHASE.DIAGNOSING && <Diagnosing steps={diagSteps} problem={problem}/>} 
        {view === "home" && phase === PHASE.DIAGNOSIS && diagnosis && <Diagnosis diagnosis={diagnosis} evidence={evidence} plan={plan} onApprove={() => setShowApproval(true)} onReset={reset}/>} 
        {view === "home" && phase === PHASE.REPAIRING && <Repair status={session?.status} steps={repairSteps(session?.status)} execute={execute} verify={verify}/>} 
        {view === "home" && phase === PHASE.VERIFIED && <Verified onReset={reset}/>} 
      </main>
    </div>

    {showApproval && <Approval plan={plan} onCancel={() => setShowApproval(false)} onConfirm={approve}/>} 
  </div>;
}

function Home({ problem, setProblem, diagnose }) { return <section className="home-page"><div className="home-copy"><h1>What can we fix <span>today?</span></h1><p>Describe your problem and WinFix will find the right solution</p></div><form className="home-form" onSubmit={e => { e.preventDefault(); diagnose(problem); }}><div className="input-wrap"><Icon name="message" size={31}/><textarea value={problem} onChange={e => setProblem(e.target.value)} placeholder="My sound isn’t working..." aria-label="Describe your Windows problem" /></div><button className="primary-cta" disabled={!problem.trim()}><Icon name="search" size={30}/><b>Diagnose Problem</b><Icon name="arrow" size={31}/></button></form></section>; }
function Diagnosing({ steps }) { return <section className="state-page diagnosing"><div className="state-title"><h1>Diagnosing<span>...</span></h1><p>WinFix is analysing your system. This may take a few moments.</p></div><div className="diagnose-layout"><div className="windows-ring"><div>▦</div></div><div className="activity">{steps.map((s,i)=><div className={`activity-row ${s.status}`} key={i}><span>{s.status === "done" ? "✓" : s.status === "running" ? "" : "○"}</span>{s.step}</div>)}</div></div><div className="tip"><Icon name="sparkle" size={22}/><span><b>Tip</b><small>You can continue using your PC while WinFix diagnoses the issue.</small></span></div></section>; }
function Diagnosis({ diagnosis, evidence, plan, onApprove }) { return <section className="state-page result-page"><div className="back-line"><Icon name="back" size={25}/> Back to Home</div><h1>Solution <span>Found</span></h1><p className="lead">We’ve analysed your issue and found the best solution.</p><div className="result-grid"><div className="solution-card"><div className="solution-top"><div className="round-icon"><Icon name="audio" size={31}/></div><div className="solution-title"><h2>{diagnosis.title}</h2><p>{diagnosis.explanation}</p></div><span className="severity">⚠ {diagnosis.severity}</span></div><div className="divider"/><h3>Recommended Fix</h3><ol className="repair-list">{plan.slice(0,4).map((p,i)=><li key={p.action_id || i}><span>{i+1}</span><div><b>{p.text}</b><small>{p.reason || "WinFix will safely apply this recommended remediation."}</small></div></li>)}</ol><div className="result-actions"><button className="primary-cta compact" onClick={onApprove}><span>▶</span><b>Apply Fix</b><small>Let WinFix handle it for you</small></button><button className="secondary-cta"><span>☷</span> View Details</button></div></div><aside className="insight-card"><Icon name="sparkle" size={31}/><h3>AI Insight</h3><p>{diagnosis.explanation || "This issue was identified from system evidence collected during diagnosis."}</p></aside></div></section>; }
function Repair({ status, steps, execute, verify }) { return <section className="state-page repair-page"><div className="back-line"><Icon name="back" size={25}/> Back to Home</div><h1>Applying <span>Fix...</span></h1><p className="lead">WinFix is now applying the selected repair plan.</p><div className="repair-card">{steps.map((s,i)=><div className={`repair-row ${s.status}`} key={i}><span className="repair-status">{s.status === "done" ? "✓" : s.status === "running" ? "" : i+1}</span><div><b>{s.step}</b><small>{s.detail || (s.status === "pending" ? "Pending" : "Completed")}</small></div><em>{s.status === "done" ? "Completed" : s.status === "running" ? "In progress..." : "Pending"}</em></div>)}</div>{status === "approved" && <button className="primary-cta" onClick={execute}>🔧 Execute Approved Repair <Icon name="arrow" size={27}/></button>}{status === "verifying" && <button className="primary-cta" onClick={verify}>✓ Verify System <Icon name="arrow" size={27}/></button>}</section>; }
function Verified({ onReset }) { return <section className="state-page verified-page"><div className="success-ring"><Icon name="check" size={56}/></div><h1>Fix <span>Successful</span></h1><p>The issue has been resolved and your system is working properly.</p><button className="primary-cta" onClick={onReset}>Diagnose Another Problem <Icon name="arrow" size={27}/></button></section>; }
function Approval({ plan, onCancel, onConfirm }) { return <div className="modal-backdrop"><div className="approval-modal"><h2>Ready to repair the system?</h2><p>These changes will be made to your Windows machine:</p><ul>{plan.map((p,i)=><li key={i}>✓ {p.text}</li>)}</ul><div><button className="secondary-cta" onClick={onCancel}>Cancel</button><button className="primary-cta" onClick={onConfirm}>Approve Fix <Icon name="arrow" size={22}/></button></div></div></div>; }
function Settings({ prefs, setPrefs, onBack, onSave, saved }) { return <section className="settings-page"><div className="settings-head"><div><button className="back-link" onClick={onBack}><Icon name="back" size={24}/> Back to Home</button><h1>Settings</h1><p>Configure your AI, GPU and model preferences</p></div><div className="personalise"><Icon name="settings" size={32}/><span><b>Personalise WinFix</b><small>Set your preferences for a better experience</small></span></div></div><div className="setting-card api-card"><div className="setting-title"><Icon name="link" size={34}/><span><b>API Configuration</b><small>Connect your preferred API provider</small></span></div><div className="api-row"><select value={prefs.provider} onChange={e => setPrefs({...prefs, provider:e.target.value})}><option>OpenAI</option><option>Local API</option><option>Custom Provider</option></select><div className="key-wrap"><input type="password" placeholder="Enter your API key" value={prefs.apiKey} onChange={e => setPrefs({...prefs, apiKey:e.target.value})}/><Icon name="eyeoff" size={22}/></div><button className="test-btn" onClick={() => setPrefs({...prefs})}>Test Connection</button></div><div className="privacy-note"><Icon name="info" size={16}/> Your API key is stored locally and never shared.</div></div><div className="setting-card model-card"><div className="setting-title"><Icon name="cube" size={34}/><span><b>Model Preferences</b><small>Choose the model you want to run</small></span></div><div className="model-grid"><select value={prefs.model} onChange={e => setPrefs({...prefs, model:e.target.value})}><option>GPT-4o</option><option>GPT-4.1</option><option>Local model</option></select><div className="model-info"><b>{prefs.model}</b><p>Best balance of speed, accuracy and reasoning.</p><span>General Use</span><span>Fast</span><span>Reliable</span></div></div></div><div className="setting-card gpu-card"><div className="setting-title"><Icon name="chip" size={34}/><span><b>GPU Acceleration (Optional)</b><small>Enable GPU acceleration for faster local processing</small></span><button className={`toggle ${prefs.gpuEnabled ? "on" : ""}`} onClick={() => setPrefs({...prefs, gpuEnabled:!prefs.gpuEnabled})}><i/></button></div><div className="gpu-grid"><select value={prefs.gpu} onChange={e => setPrefs({...prefs, gpu:e.target.value})}><option>NVIDIA GeForce RTX 4060</option><option>Auto-detect</option><option>CPU only</option></select><div className="gpu-note"><Icon name="info" size={24}/><span>GPU acceleration can speed up local model inference and system analysis.</span></div></div></div><div className="save-row"><button className="primary-cta save" onClick={onSave}><Icon name="save" size={24}/><b>{saved ? "Preferences Saved" : "Save Preferences"}</b><Icon name="arrow" size={24}/></button></div></section>; }
