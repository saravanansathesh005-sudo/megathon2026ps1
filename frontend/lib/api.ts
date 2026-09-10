const BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

let token: string | null = null;

export function setToken(value: string | null) {
  token = value;
  if (typeof window !== "undefined") {
    if (value) window.localStorage.setItem("aegis_token", value);
    else window.localStorage.removeItem("aegis_token");
  }
}

export function loadToken(): string | null {
  if (typeof window === "undefined") return null;
  token = window.localStorage.getItem("aegis_token");
  return token;
}

async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(BASE + path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: "Bearer " + token } : {}),
      ...(init.headers || {}),
    },
  });
  const text = await res.text();
  const body = text ? JSON.parse(text) : null;
  if (!res.ok) throw Object.assign(new Error("request failed"), { status: res.status, body });
  return body as T;
}

export const api = {
  login: (username: string, password: string) =>
    call<any>("/api/login", { method: "POST", body: JSON.stringify({ username, password }) }),
  me: () => call<any>("/api/me"),
  chat: (message: string) =>
    call<any>("/api/chat", { method: "POST", body: JSON.stringify({ message }) }),
  analyze: (payload: any) =>
    call<any>("/api/actions/analyze", { method: "POST", body: JSON.stringify(payload) }),
  execute: (action_id: number) =>
    call<any>("/api/actions/execute", { method: "POST", body: JSON.stringify({ action_id }) }),
  actions: () => call<any>("/api/actions"),
  approvals: () => call<any>("/api/approvals"),
  approve: (id: number) => call<any>("/api/approvals/" + id + "/approve", { method: "POST" }),
  reject: (id: number, reason = "") =>
    call<any>("/api/approvals/" + id + "/reject", { method: "POST", body: JSON.stringify({ reason }) }),
  dashboard: () => call<any>("/api/dashboard"),
  audit: () => call<any>("/api/audit"),
  verifyAudit: () => call<any>("/api/audit/verify"),
  reset: () => call<any>("/api/demo/reset", { method: "POST" }),
};

export const DECISION_STYLE: Record<string, string> = {
  ALLOW: "text-emerald-300 border-emerald-500/40 bg-emerald-500/10",
  REQUIRE_CONFIRMATION: "text-amber-300 border-amber-500/40 bg-amber-500/10",
  REQUIRE_ADMIN_APPROVAL: "text-orange-300 border-orange-500/40 bg-orange-500/10",
  BLOCK: "text-rose-300 border-rose-500/40 bg-rose-500/10",
};

export const SEVERITY_STYLE: Record<string, string> = {
  LOW: "text-emerald-300",
  MODERATE: "text-amber-300",
  HIGH: "text-orange-300",
  CRITICAL: "text-rose-300",
  NORMAL: "text-emerald-300",
  ELEVATED: "text-amber-300",
  EXTREME: "text-rose-400",
};
