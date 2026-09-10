"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { api, loadToken, setToken } from "@/lib/api";

/** Normal user interface. Contains no security navigation, by design. */

const DEMO_ACCOUNTS = [
  { u: "user", p: "user123", label: "Uma User" },
  { u: "user2", p: "user2123", label: "Ravi Second" },
];

const SEV: Record<string, string> = {
  CRITICAL: "bg-rose-500/15 text-rose-300",
  HIGH: "bg-orange-500/15 text-orange-300",
  MEDIUM: "bg-amber-400/15 text-amber-300",
  LOW: "bg-sky-500/15 text-sky-300",
  INFO: "bg-slate-500/15 text-slate-400",
};

const SUGGESTIONS = [
  "Create a project called Megathon",
  "Show me my projects",
  "Delete the project Portfolio",
  "Analyse this code: eval(user_input)",
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
  review?: any;
  done?: boolean;
};

function Shield({ size = 20 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M12 3l7 3v5.5c0 4.2-2.9 7.9-7 9-4.1-1.1-7-4.8-7-9V6l7-3z"
        stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
      <path d="M12 8.5v4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <circle cx="12" cy="15.2" r="0.9" fill="currentColor" />
    </svg>
  );
}

function GoogleMark() {
  return (
    <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true">
      <path fill="#4285F4" d="M45 24c0-1.6-.1-2.7-.4-3.9H24v7.1h12c-.2 1.9-1.5 4.7-4.4 6.6l6.7 5.2C42.2 35.5 45 30.3 45 24z" />
      <path fill="#34A853" d="M24 46c5.9 0 10.9-2 14.5-5.3l-6.9-5.4c-1.9 1.3-4.4 2.2-7.6 2.2-5.8 0-10.7-3.8-12.5-9.1l-7.1 5.5C8.1 41 15.4 46 24 46z" />
      <path fill="#FBBC05" d="M11.5 28.4c-.5-1.4-.8-2.9-.8-4.4s.3-3 .7-4.4l-7.1-5.5C2.8 17 2 20.4 2 24s.8 7 2.3 9.9l7.2-5.5z" />
      <path fill="#EA4335" d="M24 10.7c4.1 0 6.9 1.8 8.5 3.3l6.2-6C34.9 4.5 29.9 2 24 2 15.4 2 8.1 7 4.3 14.1l7.2 5.5c1.8-5.3 6.7-8.9 12.5-8.9z" />
    </svg>
  );
}

/** Ambient teal wash behind both screens. */
function Glow() {
  return (
    <div aria-hidden="true" className="pointer-events-none fixed inset-0 -z-10"
      style={{
        background:
          "radial-gradient(70% 55% at 50% 0%, rgba(20,150,150,.16), transparent 70%)," +
          "radial-gradient(45% 40% at 0% 100%, rgba(16,140,140,.14), transparent 70%)," +
          "radial-gradient(45% 40% at 100% 100%, rgba(16,140,140,.12), transparent 70%)," +
          "#080B10",
      }} />
  );
}

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
  const box = useRef<HTMLTextAreaElement>(null);

  const refreshConvos = useCallback(async () => {
    try { setConvos((await api.conversations()).conversations); } catch { /* signed out */ }
  }, []);

  useEffect(() => {
    api.authConfig().then(setCfg).catch(() => {});
    const t = loadToken();
    if (t) api.me().then((u) => { setMe(u); refreshConvos(); }).catch(() => setToken(null));
  }, [refreshConvos]);

  useEffect(() => { bottom.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs]);

  /** Grow the composer with its content, up to a ceiling, then scroll inside. */
  function autosize() {
    const el = box.current;
    if (!el) return;
    el.style.height = "0px";
    el.style.height = Math.min(el.scrollHeight, 200) + "px";
  }
  useEffect(autosize, [input]);

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
        id: "a-" + (r.action_id ?? Date.now()), role: "assistant", content: r.message,
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
      const review = out.tool_result?.findings ? out.tool_result : null;
      const line = out.commit_status === "rolled_back"
        ? "Verification failed, so I rolled it back. Nothing was changed."
        : out.execution_status === "executed"
          ? (review ? review.summary : "Done.")
          : "That didn't complete.";
      setMsgs((m) => [...m, {
        id: "r-" + actionId, role: "assistant", content: line,
        kind: review ? "review" : "result", review,
      }]);
    } catch (e: any) {
      const d = e?.body?.detail;
      setMsgs((m) => [...m, {
        id: "e-" + actionId, role: "assistant", kind: "blocked",
        content: d?.reason || d?.error || "The security policy prevented this.",
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

  const font = "font-['Outfit',ui-sans-serif,system-ui,sans-serif]";

  // ================================================================== sign in
  if (!me) {
    return (
      <main className={"relative flex min-h-screen items-center justify-center px-5 py-12 " + font}>
        <Glow />
        <div className="w-full max-w-[440px] text-center">
          <div className="mx-auto mb-6 grid h-[52px] w-[52px] place-items-center rounded-2xl border border-cyan-400/20 bg-cyan-400/10 text-cyan-300">
            <Shield size={24} />
          </div>

          <div className="text-[15px] font-semibold tracking-[0.42em] text-slate-200">
            AEGIS
          </div>

          <h1 className="mx-auto mt-6 max-w-[380px] text-[32px] font-bold leading-[1.18] tracking-tight text-white">
            Your intelligent workspace, powered by AI
          </h1>
          <p className="mt-3 text-[14px] text-slate-400">
            Work smarter. Automate faster. Stay in control.
          </p>

          <div className="mt-9 rounded-2xl border border-white/[0.07] bg-white/[0.02] p-5">
            <button onClick={signInWithGoogle}
              className="flex w-full items-center justify-center gap-3 rounded-xl border border-white/[0.08] bg-white/[0.04] px-4 py-3.5 text-[14px] font-semibold text-white transition hover:border-cyan-400/30 hover:bg-white/[0.07] focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-400">
              <GoogleMark />
              Continue with Google
            </button>
            {!cfg.google && (
              <p className="mt-3 text-[11.5px] leading-relaxed text-slate-500">
                Google sign-in needs server credentials. Use a demo account below.
              </p>
            )}

            {cfg.password && (
              <>
                <div className="my-5 flex items-center gap-3">
                  <span className="h-px flex-1 bg-white/[0.07]" />
                  <span className="text-[10px] font-medium uppercase tracking-[0.18em] text-slate-500">
                    Demo accounts
                  </span>
                  <span className="h-px flex-1 bg-white/[0.07]" />
                </div>

                {DEMO_ACCOUNTS.map((d) => (
                  <button key={d.u} onClick={() => signInWithPassword(d.u, d.p)}
                    className="group mb-2.5 flex w-full items-center justify-between rounded-xl border border-white/[0.07] bg-white/[0.02] px-4 py-3.5 text-left transition hover:border-cyan-400/30 hover:bg-white/[0.05] focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-400">
                    <span className="text-[13.5px] text-white">
                      {d.label}<span className="text-slate-500"> · {d.u}</span>
                    </span>
                    <span className="text-slate-600 transition group-hover:translate-x-0.5 group-hover:text-cyan-300">→</span>
                  </button>
                ))}
              </>
            )}
          </div>

          {error && (
            <p className="mt-4 rounded-xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-[12.5px] text-rose-300">
              {error}
            </p>
          )}
        </div>
      </main>
    );
  }

  const initials = (me.display_name || me.username || "?")
    .split(" ").map((s: string) => s[0]).slice(0, 2).join("").toUpperCase();

  // ================================================================ assistant
  return (
    <main className={"relative flex h-screen overflow-hidden " + font}>
      <Glow />

      <aside className="hidden w-[272px] shrink-0 flex-col border-r border-white/[0.06] bg-black/25 px-4 py-5 md:flex">
        <div className="mb-6 flex items-center gap-2.5 px-1">
          <span className="grid h-8 w-8 place-items-center rounded-lg border border-cyan-400/20 bg-cyan-400/10 text-cyan-300">
            <Shield size={16} />
          </span>
          <span className="text-[14px] font-semibold tracking-[0.34em] text-white">AEGIS</span>
        </div>

        <button onClick={newChat}
          className="flex items-center gap-2 rounded-xl border border-white/[0.09] bg-white/[0.03] px-4 py-3 text-[13.5px] font-medium text-white transition hover:border-cyan-400/30 hover:bg-white/[0.06] focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-400">
          <span className="text-[15px] leading-none text-cyan-300">+</span> New chat
        </button>

        <div className="mb-2 mt-7 px-1 text-[10px] font-medium uppercase tracking-[0.18em] text-slate-500">
          Recent
        </div>
        <div className="-mx-1 flex-1 overflow-y-auto px-1">
          {convos.map((c) => (
            <button key={c.id} onClick={() => openConversation(c.id)}
              className={"mb-0.5 block w-full truncate rounded-lg px-3 py-2 text-left text-[13px] transition " +
                (convoId === c.id
                  ? "bg-white/[0.07] text-white"
                  : "text-slate-400 hover:bg-white/[0.04] hover:text-slate-200")}>
              {c.title}
            </button>
          ))}
          {convos.length === 0 && (
            <p className="px-3 py-2 text-[12.5px] text-slate-600">No conversations yet.</p>
          )}
        </div>

        <div className="mt-4 rounded-xl border border-white/[0.07] bg-white/[0.02] p-3">
          <div className="flex items-center gap-3">
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-cyan-400/15 text-[12px] font-semibold text-cyan-200">
              {initials}
            </span>
            <span className="min-w-0">
              <span className="block truncate text-[13px] font-medium text-white">
                {me.display_name || me.username}
              </span>
              <span className="block truncate text-[11.5px] text-slate-500">
                {me.email || me.username}
              </span>
            </span>
          </div>
          <button
            onClick={async () => {
              try { await api.logout(); } catch {}
              setToken(null); setMe(null); setMsgs([]); setConvos([]);
            }}
            className="mt-3 flex w-full items-center justify-center gap-2 rounded-lg border border-white/[0.08] px-3 py-2 text-[12px] text-slate-400 transition hover:border-white/20 hover:text-slate-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-400">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M15 12H4m0 0l3.5-3.5M4 12l3.5 3.5M11 4h6a2 2 0 012 2v12a2 2 0 01-2 2h-6"
                stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            Log out
          </button>
        </div>
      </aside>

      <section className="flex flex-1 flex-col">
        <div className="flex-1 overflow-y-auto px-5 py-10">
          <div className="mx-auto w-full max-w-[720px]">
            {msgs.length === 0 ? (
              <div className="pt-[8vh] text-center">
                <p className="text-[10.5px] font-medium uppercase tracking-[0.24em] text-cyan-300/70">
                  Your AI workspace
                </p>
                <h1 className="mt-4 text-[40px] font-bold leading-tight tracking-tight text-white">
                  How can I help?
                </h1>
                <p className="mt-3 text-[14px] text-slate-400">
                  Ask, plan, analyze, or get things done with AEGIS.
                </p>
                <div className="mx-auto mt-9 grid gap-3">
                  {SUGGESTIONS.map((s) => (
                    <button key={s} onClick={() => { setInput(s); box.current?.focus(); }}
                      className="rounded-xl border border-white/[0.07] bg-white/[0.02] px-5 py-4 text-left text-[14px] text-slate-300 transition hover:border-cyan-400/25 hover:bg-white/[0.05] hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-400">
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="space-y-5">
                {msgs.map((m) => (
                  <div key={m.id}>
                    {m.role === "user" ? (
                      <div className="flex justify-end">
                        <div className="max-w-[80%] whitespace-pre-wrap rounded-2xl rounded-br-md border border-white/[0.07] bg-white/[0.06] px-4 py-2.5 text-[14px] text-white">
                          {m.content}
                        </div>
                      </div>
                    ) : m.kind === "blocked" ? (
                      <div className="rounded-2xl border border-rose-500/20 bg-rose-500/[0.07] p-4">
                        <div className="mb-1.5 flex items-center gap-2 text-[13px] font-semibold text-rose-300">
                          <Shield size={15} /> Action blocked
                        </div>
                        <p className="text-[14px] leading-relaxed text-slate-300">
                          {m.content.replace(/^Action blocked\.\s*/, "")}
                        </p>
                        <p className="mt-2.5 text-[11.5px] text-slate-500">
                          AEGIS made this decision automatically.
                        </p>
                      </div>
                    ) : m.kind === "confirm" && !m.done ? (
                      <div className="rounded-2xl border border-amber-400/25 bg-amber-400/[0.06] p-4">
                        <div className="mb-1.5 text-[13px] font-semibold text-amber-300">
                          Confirmation required
                        </div>
                        <p className="text-[14px] leading-relaxed text-slate-200">{m.content}</p>
                        {m.proposal && (
                          <p className="mt-2 text-[12px] text-slate-500">
                            {m.proposal.action}
                            {m.proposal.parameters?.name ? " · " + m.proposal.parameters.name : ""}
                          </p>
                        )}
                        <div className="mt-3.5 flex gap-2">
                          <button onClick={() => confirmAction(m)} disabled={busy}
                            className="rounded-lg bg-amber-400/20 px-4 py-2 text-[12.5px] font-semibold text-amber-200 transition hover:bg-amber-400/30 disabled:opacity-40">
                            Confirm
                          </button>
                          <button onClick={() => cancelAction(m)}
                            className="rounded-lg border border-white/[0.09] px-4 py-2 text-[12.5px] text-slate-400 transition hover:text-slate-200">
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : m.kind === "review" ? (
                      <div className="rounded-2xl border border-white/[0.08] bg-white/[0.02] p-4">
                        <div className="mb-3 flex flex-wrap items-center gap-2">
                          <span className="text-[13px] font-semibold text-cyan-300">
                            Code review
                          </span>
                          <span className="text-[11.5px] text-slate-500">
                            {m.review.lines} lines · {m.review.analysed_by}
                          </span>
                          {Object.entries(m.review.counts || {}).map(([sev, n]: any) => (
                            <span key={sev}
                              className={"rounded-full px-2 py-0.5 text-[10px] font-semibold " + SEV[sev]}>
                              {n} {sev}
                            </span>
                          ))}
                        </div>
                        <p className="mb-3 text-[13.5px] leading-relaxed text-slate-300">
                          {m.review.summary}
                        </p>
                        <div className="space-y-2.5">
                          {m.review.findings.map((f: any, i: number) => (
                            <div key={i} className="rounded-xl border border-white/[0.06] bg-black/20 p-3">
                              <div className="mb-1 flex items-center gap-2">
                                <span className={"rounded px-1.5 py-0.5 text-[10px] font-bold " + SEV[f.severity]}>
                                  {f.severity}
                                </span>
                                <span className="text-[13px] font-medium text-white">{f.title}</span>
                                {f.line != null && (
                                  <span className="text-[11px] text-slate-500">line {f.line}</span>
                                )}
                              </div>
                              <p className="text-[12.5px] leading-relaxed text-slate-400">{f.detail}</p>
                              {f.fix && (
                                <p className="mt-1.5 text-[12.5px] leading-relaxed text-cyan-300/80">
                                  Fix: {f.fix}
                                </p>
                              )}
                            </div>
                          ))}
                          {m.review.findings.length === 0 && (
                            <p className="text-[13px] text-emerald-300">No risks found.</p>
                          )}
                        </div>
                      </div>
                    ) : m.kind === "result" ? (
                      <p className="flex items-center gap-2 text-[14px] text-cyan-300/90">
                        <span className="text-[15px] leading-none">✓</span> {m.content}
                      </p>
                    ) : (
                      <p className="whitespace-pre-wrap text-[14.5px] leading-relaxed text-slate-200">
                        {m.content}
                      </p>
                    )}
                  </div>
                ))}
                {busy && (
                  <p className="flex items-center gap-2 text-[13.5px] text-slate-500">
                    <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-cyan-400" />
                    Thinking…
                  </p>
                )}
                {error && <p className="text-[13.5px] text-rose-400">{error}</p>}
                <div ref={bottom} />
              </div>
            )}
          </div>
        </div>

        <div className="px-5 pb-7">
          <div className="mx-auto w-full max-w-[720px]">
            <div className="flex items-end gap-2 rounded-2xl border border-white/[0.08] bg-white/[0.03] py-2.5 pl-5 pr-2.5 transition focus-within:border-cyan-400/30">
              <textarea
                ref={box}
                rows={1}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  // Enter sends. Shift+Enter (or Ctrl/Cmd+Enter) starts a new line.
                  if (e.key === "Enter" && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
                    e.preventDefault();
                    send();
                  }
                }}
                disabled={busy}
                placeholder="Message AEGIS…"
                aria-label="Message AEGIS"
                className="max-h-[200px] flex-1 resize-none bg-transparent py-2 text-[14.5px] leading-relaxed text-white outline-none placeholder:text-slate-500 disabled:opacity-50" />
              <button onClick={send} disabled={busy || !input.trim()}
                className="mb-0.5 flex shrink-0 items-center gap-1.5 rounded-full bg-cyan-400 px-5 py-2.5 text-[13px] font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:opacity-30 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cyan-400">
                Send
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M12 19V5m0 0l-6 6m6-6l6 6" stroke="currentColor"
                    strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
            </div>
            <p className="mt-2 text-center text-[11px] text-slate-600">
              Enter to send · Shift + Enter for a new line
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}
