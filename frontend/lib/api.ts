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

/** Multipart upload.
 *
 * Deliberately does NOT set Content-Type: the browser has to write it itself so
 * it can include the multipart boundary. Setting it here produces a body the
 * server cannot parse.
 */
async function upload<T>(path: string, file: File): Promise<T> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(BASE + path, {
    method: "POST",
    headers: { ...(token ? { Authorization: "Bearer " + token } : {}) },
    body: form,
  });
  const text = await res.text();
  const body = text ? JSON.parse(text) : null;
  if (!res.ok) throw Object.assign(new Error("upload failed"), { status: res.status, body });
  return body as T;
}

export const api = {
  authConfig: () => call<any>("/api/auth/config"),
  googleStart: () => call<any>("/api/auth/google/start"),
  login: (username: string, password: string) =>
    call<any>("/api/login", { method: "POST", body: JSON.stringify({ username, password }) }),
  logout: () => call<any>("/api/logout", { method: "POST" }),
  me: () => call<any>("/api/me"),

  conversations: () => call<any>("/api/conversations"),
  newConversation: () => call<any>("/api/conversations", { method: "POST" }),
  messages: (id: number) => call<any>("/api/conversations/" + id + "/messages"),
  truncate: (id: number, messageId: number) =>
    call<any>("/api/conversations/" + id + "/messages/" + messageId + "/truncate",
              { method: "POST" }),
  chat: (message: string, conversation_id?: number | null) =>
    call<any>("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message, conversation_id: conversation_id ?? null }),
    }),

  confirm: (id: number) =>
    call<any>("/api/confirmations/" + id + "/confirm", { method: "POST" }),
  cancel: (id: number) =>
    call<any>("/api/confirmations/" + id + "/cancel", { method: "POST" }),
  execute: (action_id: number) =>
    call<any>("/api/actions/execute", { method: "POST", body: JSON.stringify({ action_id }) }),

  // Admin Security Terminal - read only. No write endpoints exist.
  scanFile: (file: File, conversationId?: number | null) =>
    upload<any>("/api/files/scan" + (conversationId ? "?conversation_id=" + conversationId : ""),
                file),

  secOverview: () => call<any>("/api/admin/security/overview"),
  secEvents: (q = "") => call<any>("/api/admin/security/events" + q),
  secEvent: (id: number) => call<any>("/api/admin/security/events/" + id),
  secUsers: () => call<any>("/api/admin/security/users"),
  secTrajectory: (userId: number) =>
    call<any>("/api/admin/security/users/" + userId + "/trajectory"),
  secAudit: () => call<any>("/api/admin/security/audit"),
  secFiles: () => call<any>("/api/admin/security/files"),
  secSteering: () => call<any>("/api/admin/security/steering"),

  reset: () => call<any>("/api/demo/reset", { method: "POST" }),
};

export const DECISION_STYLE: Record<string, string> = {
  ALLOW: "text-emerald-300 border-emerald-500/40 bg-emerald-500/10",
  REQUIRE_CONFIRMATION: "text-amber-300 border-amber-500/40 bg-amber-500/10",
  BLOCK: "text-rose-300 border-rose-500/40 bg-rose-500/10",
};

export const BAND_STYLE: Record<string, string> = {
  NORMAL: "text-emerald-300 bg-emerald-500/10",
  RISKY: "text-amber-300 bg-amber-500/10",
  PRIVILEGED: "text-orange-300 bg-orange-500/10",
  FORBIDDEN: "text-rose-300 bg-rose-500/10",
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
