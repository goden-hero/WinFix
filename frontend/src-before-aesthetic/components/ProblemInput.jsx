import React, { useState } from "react";

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

export default function ProblemInput({ value, onChange, onDiagnose }) {
  const [local, setLocal] = useState("");
  const text = value ?? local;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (text.trim()) onDiagnose(text);
  };

  return (
    <form className="problem-form" onSubmit={handleSubmit}>
      <label className="sr-only" htmlFor="problem-input">Describe your Windows problem</label>

      <div className="input-wrap">
        <span className="input-icon"><svg viewBox="0 0 32 32" aria-hidden="true"><path d="M6 8.5h20v14H12l-6 5v-5z" /></svg></span>
        <textarea
          id="problem-input"
          className="problem-input"
          rows={1}
          placeholder="My sound isn’t working..."
          value={text}
          onChange={(e) => (onChange ? onChange(e.target.value) : setLocal(e.target.value))}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              if (text.trim()) onDiagnose(text);
            }
          }}
        />
      </div>

      <button type="submit" className="btn btn-primary btn-lg" disabled={!text.trim()}>
        <SearchIcon />
        <span>Diagnose Problem</span>
        <ArrowIcon />
      </button>
    </form>
  );
}
