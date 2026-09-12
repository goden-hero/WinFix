const defaultHost = typeof window !== "undefined" && window.location.hostname ? window.location.hostname : "127.0.0.1";
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? `http://${defaultHost}:9000/api/v1`;

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail ?? "WinFix request failed");
  return response.json();
}

export const winfixApi = {
  createSession: (user_problem) => request("/sessions", { method: "POST", body: JSON.stringify({ user_problem }) }),
  diagnose: (sessionId, categories) => request(`/sessions/${sessionId}/diagnose`, { method: "POST", body: JSON.stringify({ categories: categories || ["performance", "windows_update"] }) }),
  approve: (sessionId, decisions) => request(`/sessions/${sessionId}/approve`, { method: "POST", body: JSON.stringify({ decisions }) }),
  executeSession: (sessionId) => request(`/sessions/${sessionId}/execute`, { method: "POST" }),
  verifySession: (sessionId) => request(`/sessions/${sessionId}/verify`, { method: "POST" }),
};
