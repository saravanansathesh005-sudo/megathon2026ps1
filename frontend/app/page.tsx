"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { api, loadToken, setToken } from "@/lib/api";

/** Normal user interface. Contains no security navigation, by design. */

const DEMO_ACCOUNTS = [
  { u: "user", p: "user123", label: "Uma User" },
  { u: "user2", p: "user2123", label: "Ravi Second" },
];

type Msg = {
  id: number | string;
  role: "user" | "assistant";
  content: string;
  kind?: string;
  action_id?: number | null;
  confirmation?: any;
  decision?: string;
  proposal?: any;
  done?: boolean;
};

export default function Assistant() {
  const [me, setMe] = useState<any>(null);
  const [cfg, setCfg] = useState<any>({ google: false, password: true });
  const [convos, setConvos] = useState<any[]>([]);
  const [convoId, setConvoId] = useState<number | null>(null);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottom = useRef<HTMLDivElement>(null);

  const refreshConvos = useCallback(async () => {
    try { setConvos((await api.conversations()).conversations); } catch { /* signed out */ }
  }, []);

  useEffect(() => {
    api.authConfig().then(setCfg).catch(() => {});
    const t = loadToken();
    if (t) api.me().then((u) => { setMe(u); refreshConvos(); }).catch(() => setToken(null));
  }, [refreshConvos]);

  useEffect(() => { bottom.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs]);

  async function signInWithGoogle() {
    setError(null);
    try {
      const { authorization_url } = await api.googleStart();
      window.location.href = authorization_url;
    } catch (e: any) {
      setError(e?.body?.detail || "Google sign-in is not configured on this server.");
    }
  }

  async function signInWithPassword(u: string, p: string) {
    setError(null);
    try {
      setToken((await api.login(u, p)).token);
      setMe(await api.me());
      await refreshConvos();
    } catch { setError("Sign-in failed."); }
  }

  async function openConversation(id: number) {
    setConvoId(id);
    const { messages } = await api.messages(id);
    setMsgs(messages);
  }

  function newChat() { setConvoId(null); setMsgs([]); setInput(""); }

  async function send() {
    const text = input.trim();
    if (!text || busy) return;
    setInput(""); setBusy(true); setError(null);
    setMsgs((m) => [...m, { id: "tmp-" + Date.now(), role: "user", content: text }]);
    try {
      const r = await api.chat(text, convoId);
      setConvoId(r.conversation_id);
      setMsgs((m) => [...m, {
        id: "a-" + r.action_id, role: "assistant", content: r.message,
        kind: r.kind, action_id: r.action_id, confirmation: r.confirmation,
        decision: r.decision, proposal: r.proposal,
      }]);
      if (r.decision === "ALLOW" && r.action_id) await run(r.action_id);
      await refreshConvos();
    } catch (e: any) {
      setError(e?.status === 401 ? "Your session expired. Sign in again."
        : "Something went wrong. Please try again.");
    }
    setBusy(false);
  }

  async function run(actionId: number) {
    try {
      const out = await api.execute(actionId);
      const line = out.commit_status === "rolled_back"
        ? "Verification failed, so I rolled it back. Nothing was changed."
        : out.execution_status === "executed" ? "✓ Done." : "That didn't complete.";
      setMsgs((m) => [...m, { id: "r-" + actionId, role: "assistant", content: line, kind: "result" }]);
    } catch (e: any) {
      const d = e?.body?.detail;
      setMsgs((m) => [...m, {
        id: "e-" + actionId, role: "assistant", kind: "blocked",
        content: "Action blocked. " + (d?.reason || d?.error || "The security policy prevented this."),
      }]);
    }
  }

  async function confirmAction(msg: Msg) {
    if (!msg.confirmation || !msg.action_id) return;
    setBusy(true);
    try {
      await api.confirm(msg.confirmation.id);
      await run(msg.action_id);
      setMsgs((m) => m.map((x) => (x.id === msg.id ? { ...x, done: true } : x)));
    } catch (e: any) {
      const d = e?.body?.detail;
      setError(typeof d === "string" ? d : d?.error || "Confirmation was refused.");
    }
    setBusy(false);
  }

  async function cancelAction(msg: Msg) {
    if (!msg.confirmation) return;
    try { await api.cancel(msg.confirmation.id); } catch { /* already resolved */ }
    setMsgs((m) => m.map((x) => (x.id === msg.id ? { ...x, done: true } : x))
      .concat({ id: "c-" + msg.id, role: "assistant", content: "Cancelled — nothing was changed." }));
  }

  // ------------------------------------------------------------------ sign in
  if (!me) {
    return (
      <main className="flex min-h-screen items-center justify-center px-4">
        <div className="w-full max-w-sm">
          <div className="mb-8 text-center">
            <div className="text-3xl font-semibold tracking-tight text-slate-100">AEGIS</div>
            <p className="mt-2 text-sm text-slate-500">Your AI assistant</p>
          </div>
          <button onClick={signInWithGoogle}
            className="mb-3 flex w-full items-center justify-center gap-3 rounded-lg border border-slate-700 bg-slate-900 px-4 py-3 text-sm font-medium text-slate-100 transition hover:border-slate-500">
            <svg width="17" height="17" viewBox="0 0 48 48" aria-hidden="true">
              <path fill="#4285F4" d="M45 24c0-1.6-.1-2.7-.4-3.9H24v7.1h12c-.2 1.9-1.5 4.7-4.4 6.6l6.7 5.2C42.2 35.5 45 30.3 45 24z" />
              <path fill="#34A853" d="M24 46c5.9 0 10.9-2 14.5-5.3l-6.9-5.4c-1.9 1.3-4.4 2.2-7.6 2.2-5.8 0-10.7-3.8-12.5-9.1l-7.1 5.5C8.1 41 15.4 46 24 46z" />
              <path fill="#FBBC05" d="M11.5 28.4c-.5-1.4-.8-2.9-.8-4.4s.3-3 .7-4.4l-7.1-5.5C2.8 17 2 20.4 2 24s.8 7 2.3 9.9l7.2-5.5z" />
              <path fill="#EA4335" d="M24 10.7c4.1 0 6.9 1.8 8.5 3.3l6.2-6C34.9 4.5 29.9 2 24 2 15.4 2 8.1 7 4.3 14.1l7.2 5.5c1.8-5.3 6.7-8.9 12.5-8.9z" />
            </svg>
            Continue with Google
          </button>
          {!cfg.google && (
            <p className="mb-5 text-center text-xs text-slate-600">
              Google sign-in needs server credentials. Use a demo account below.
            </p>
          )}
          {cfg.password && (
            <div className="border-t border-slate-800 pt-5">
              <p className="mb-3 text-center text-[11px] uppercase tracking-widest text-slate-600">
                Demo accounts
              </p>
              {DEMO_ACCOUNTS.map((d) => (
                <button key={d.u} onClick={() => signInWithPassword(d.u, d.p)}
                  className="mb-2 w-full rounded-lg border border-slate-800 px-4 py-2.5 text-left text-sm text-slate-300 hover:border-slate-600">
                  {d.label} <span className="text-slate-600">· {d.u}</span>
                </button>
              ))}
            </div>
          )}
          {error && <div className="mt-4 rounded-lg bg-rose-500/10 p-3 text-xs text-rose-300">{error}</div>}
        </div>
      </main>
    );
  }

  // --------------------------------------------------------------- assistant
  return (
    <main className="flex h-screen">
      <aside className="hidden w-64 shrink-0 flex-col border-r border-slate-800 bg-slate-950 p-3 md:flex">
        <div className="px-2 py-3 text-lg font-semibold tracking-tight text-slate-100">AEGIS</div>
        <button onClick={newChat}
          className="mb-4 rounded-lg border border-slate-700 px-3 py-2 text-left text-sm text-slate-200 hover:border-slate-500">
          + New chat
        </button>
        <div className="flex-1 overflow-y-auto">
          {convos.map((c) => (
            <button key={c.id} onClick={() => openConversation(c.id)}
              className={"mb-1 block w-full truncate rounded-lg px-3 py-2 text-left text-[13px] " +
                (convoId === c.id ? "bg-slate-800 text-slate-100" : "text-slate-400 hover:bg-slate-900")}>
              {c.title}
            </button>
          ))}
          {convos.length === 0 && <p className="px-3 text-xs text-slate-600">No conversations yet.</p>}
        </div>
        <div className="border-t border-slate-800 pt-3">
          <div className="px-2 text-sm text-slate-300">{me.display_name || me.username}</div>
          <div className="px-2 text-xs text-slate-600">{me.email || me.username}</div>
          <button onClick={async () => { try { await api.logout(); } catch {} setToken(null); setMe(null); setMsgs([]); setConvos([]); }}
            className="mt-2 w-full rounded-lg px-2 py-1.5 text-left text-xs text-slate-500 hover:text-slate-300">
            Log out
          </button>
        </div>
      </aside>

      <section className="flex flex-1 flex-col">
        <div className="flex-1 overflow-y-auto px-4 py-8">
          <div className="mx-auto max-w-2xl space-y-5">
            {msgs.length === 0 && (
              <div className="pt-16 text-center">
                <h1 className="text-2xl font-semibold text-slate-200">How can I help?</h1>
                <div className="mx-auto mt-6 grid max-w-md gap-2">
                  {["Create a project called Megathon", "Show me my projects",
                    "Delete the project Portfolio"].map((s) => (
                    <button key={s} onClick={() => setInput(s)}
                      className="rounded-lg border border-slate-800 px-4 py-2.5 text-left text-sm text-slate-400 hover:border-slate-600 hover:text-slate-200">
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {msgs.map((m) => (
              <div key={m.id}>
                {m.role === "user" ? (
                  <div className="flex justify-end">
                    <div className="max-w-[80%] rounded-2xl bg-slate-800 px-4 py-2.5 text-sm text-slate-100">
                      {m.content}
                    </div>
                  </div>
                ) : m.kind === "blocked" ? (
                  <div className="rounded-xl border border-rose-900/60 bg-rose-500/5 p-4">
                    <div className="mb-1 text-sm font-semibold text-rose-300">Action blocked</div>
                    <p className="text-sm text-slate-300">{m.content.replace(/^Action blocked\.\s*/, "")}</p>
                    <p className="mt-2 text-xs text-slate-600">AEGIS made this decision automatically.</p>
                  </div>
                ) : m.kind === "confirm" && !m.done ? (
                  <div className="rounded-xl border border-amber-900/60 bg-amber-500/5 p-4">
                    <div className="mb-1 text-sm font-semibold text-amber-300">Confirmation required</div>
                    <p className="text-sm text-slate-300">{m.content}</p>
                    {m.proposal && (
                      <p className="mt-2 text-xs text-slate-500">
                        Action: <span className="text-slate-300">{m.proposal.action}</span>
                        {m.proposal.parameters?.name ? " · " + m.proposal.parameters.name : ""}
                      </p>
                    )}
                    <div className="mt-3 flex gap-2">
                      <button onClick={() => confirmAction(m)} disabled={busy}
                        className="rounded-lg bg-amber-500/20 px-4 py-1.5 text-xs font-semibold text-amber-200 hover:bg-amber-500/30 disabled:opacity-40">
                        Confirm
                      </button>
                      <button onClick={() => cancelAction(m)}
                        className="rounded-lg border border-slate-700 px-4 py-1.5 text-xs text-slate-400 hover:text-slate-200">
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm leading-relaxed text-slate-200">{m.content}</p>
                )}
              </div>
            ))}
            {busy && <p className="text-sm text-slate-600">Thinking…</p>}
            {error && <p className="text-sm text-rose-400">{error}</p>}
            <div ref={bottom} />
          </div>
        </div>

        <div className="border-t border-slate-800 px-4 py-4">
          <div className="mx-auto flex max-w-2xl gap-2">
            <input value={input} onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
              disabled={busy} placeholder="Message AEGIS…"
              className="flex-1 rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-slate-100 outline-none placeholder:text-slate-600 focus:border-slate-500 disabled:opacity-50" />
            <button onClick={send} disabled={busy || !input.trim()}
              className="rounded-xl bg-slate-100 px-5 text-sm font-semibold text-slate-900 disabled:opacity-30">
              Send
            </button>
          </div>
        </div>
      </section>
    </main>
  );
}
