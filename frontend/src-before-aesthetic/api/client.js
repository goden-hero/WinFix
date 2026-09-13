function getApiBase() {
  if (typeof window === "undefined") return "http://127.0.0.1:9000/api/v1";
  const stored = window.localStorage.getItem("winfix_api_base");
  if (stored) return stored;
  const defaultHost = window.location.hostname ? window.location.hostname : "127.0.0.1";
  return import.meta.env.VITE_API_BASE_URL ?? `http://${defaultHost}:9000/api/v1`;
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
  getActions: () => request("/actions"),

  getSystemStatus: () => request("/system/status"),

  createSession: (user_problem) =>
    request("/sessions", {
      method: "POST",
      body: JSON.stringify({ user_problem }),
    }),

  diagnose: (sessionId, categories) =>
    request(`/sessions/${sessionId}/diagnose`, {
      method: "POST",
      body: JSON.stringify({
        categories: categories || [
          "performance",
          "startup",
          "storage",
          "battery",
          "resource_hog",
          "system_health",
          "windows_update",
        ],
      }),
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
