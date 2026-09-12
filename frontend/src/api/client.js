const DEFAULT_API_BASE =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:9000/api/v1";

function getApiBase() {
  if (typeof window === "undefined") return DEFAULT_API_BASE;
  return window.localStorage.getItem("winfix_api_base") || DEFAULT_API_BASE;
}

async function request(path, options = {}) {
  const response = await fetch(`${getApiBase()}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });

  if (!response.ok) {
    throw new Error(
      (await response.json().catch(() => ({}))).detail ??
        "WinFix request failed"
    );
  }

  return response.json();
}

export const winfixApi = {
  createSession: (user_problem) =>
    request("/sessions", {
      method: "POST",
      body: JSON.stringify({ user_problem }),
    }),

  diagnose: (sessionId) =>
    request(`/sessions/${sessionId}/diagnose`, {
      method: "POST",
      body: JSON.stringify({ categories: ["performance"] }),
    }),

  approve: (sessionId, decisions) =>
    request(`/sessions/${sessionId}/approve`, {
      method: "POST",
      body: JSON.stringify({ decisions }),
    }),

  executeSession: (sessionId) =>
    request(`/sessions/${sessionId}/execute`, { method: "POST" }),

  verifySession: (sessionId) =>
    request(`/sessions/${sessionId}/verify`, { method: "POST" }),
};
