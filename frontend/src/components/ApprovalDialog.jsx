import React from "react";

export default function ApprovalDialog({ open, plan, onCancel, onConfirm }) {
  if (!open) return null;
  return (
    <div className="modal-overlay" role="dialog" aria-modal="true" aria-label="Approve repair">
      <div className="modal">
        <div className="modal-head">
          <h3>Ready to repair the system?</h3>
          <p>These changes will be made to your Windows machine:</p>
        </div>
        <ul className="modal-list">
          {plan.map((p, i) => (
            <li key={i}>
              <span className="modal-bullet">•</span> {p.text}
            </li>
          ))}
        </ul>
        <div className="modal-actions">
          <button type="button" className="btn btn-ghost" onClick={onCancel}>Cancel</button>
          <button type="button" className="btn btn-primary" onClick={onConfirm}>Approve Fix</button>
        </div>
      </div>
    </div>
  );
}
