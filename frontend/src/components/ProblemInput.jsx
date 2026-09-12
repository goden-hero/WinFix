import React, { useState } from "react";

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
      <textarea
        id="problem-input"
        className="problem-input"
        rows={3}
        placeholder="My sound isn't working..."
        value={text}
        onChange={(e) => (onChange ? onChange(e.target.value) : setLocal(e.target.value))}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            if (text.trim()) onDiagnose(text);
          }
        }}
      />
      <button type="submit" className="btn btn-primary btn-lg" disabled={!text.trim()}>
        ⚡ Diagnose Problem
      </button>
    </form>
  );
}
