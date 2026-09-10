"use client";

import { useCallback, useEffect, useState } from "react";

import { Analysis, Card, Row } from "@/components/Panels";
import { api, DECISION_STYLE, loadToken, setToken } from "@/lib/api";

const NAV = ["Overview", "Live Actions", "Trajectory", "Approvals", "Audit"];

const DEMO_USERS = [
  { u: "viewer", p: "viewer123" },
  { u: "editor", p: "editor123" },
  { u: "admin", p: "admin123" },
  { u: "secadmin", p: "secadmin123" },
];

export default function Console() {
  const [me, setMe] = useState<any>(null);
  const [view, setView] = useState("Overview");
  const [message, setMessage] = useState("Delete all users");
  const [current, setCurrent] = useState<any>(null);
  const [actionId, setActionId] = useState<number | null>(null);
  const [exec, setExec] = useState<any>(null);
  const [board, setBoard] = useState<any>(null);
  const [actions, setActions] = useState<any[]>([]);
  const [approvals, setApprovals] = useState<any[]>([]);
  const [audit, setAudit] = useState<any[]>([]);
  const [chain, setChain] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [d, a, ap, au, cv] = await Promise.all([
        api.dashboard(), api.actions(), api.approvals(), api.audit(), api.verifyAudit(),
      ]);
      setBoard(d); setActions(a.actions); setApprovals(ap.approvals);
      setAudit(au.events); setChain(cv);
    } catch { /* not logged in */ }
  }, []);

  useEffect(() => {
    const t = loadToken();
    if (t) api.me().then((u) => { setMe(u); refresh(); }).catch(() => setToken(null));
  }, [refresh]);

  async function login(u: string, p: string) {
    setError(null);
    try {
      const r = await api.login(u, p);
      setToken(r.token);
      setMe(await api.me());
      setCurrent(null); setExec(null); setActionId(null);
      await refresh();
    } catch { setError("login failed"); }
  }

  async function send() {
    setBusy(true); setError(null); setExec(null);
    try {
      const r = await api.chat(message);
      setCurrent(r.analysis); setActionId(r.action_id);
      await refresh();
    } catch (e: any) { setError(e?.body?.detail || "request failed"); }
    setBusy(false);
  }

  async function run() {
    if (!actionId) return;
    setBusy(true); setError(null);
    try {
      const r = await api.execute(actionId);
      setExec(r); setCurrent(r.analysis || current);
    } catch (e: any) {
      const d = e?.body?.detail;
      setError(typeof d === "string" ? d : d?.error ? d.error + (d.invariant ? " (" + d.invariant + ")" : "") : "execution refused");
    }
    await refresh(); setBusy(false);
  }

  async function decide(id: number, ok: boolean) {
    setBusy(true);
    try { ok ? await api.approve(id) : await api.reject(id); }
    catch (e: any) { setError(e?.body?.detail?.error || "not permitted"); }
    await refresh(); setBusy(false);
  }

  if (!me) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <div className="w-96 rounded border border-slate-800 bg-slate-950 p-6">
          <h1 className="text-lg font-black tracking-tight text-cyan-300">AEGIS</h1>
          <p className="mb-4 text-[11px] uppercase tracking-widest text-slate-500">
            Security Control Center
          </p>
          {DEMO_USERS.map((d) => (
            <button key={d.u} onClick={() => login(d.u, d.p)}
              className="mb-2 w-full rounded border border-slate-700 px-3 py-2 text-left text-xs hover:border-cyan-500 hover:text-cyan-300">
              sign in as <span className="font-bold">{d.u}</span>
            </button>
          ))}
          {error && <div className="mt-2 text-xs text-rose-400">{error}</div>}
        </div>
      </main>
    );
  }

  const pending = approvals.filter((a) => a.status === "pending");

  return (
    <main className="flex min-h-screen">
      <aside className="w-52 shrink-0 border-r border-slate-800 bg-slate-950 p-4">
        <div className="text-lg font-black tracking-tight text-cyan-300">AEGIS</div>
        <div className="mb-6 text-[10px] uppercase tracking-widest text-slate-600">
          Control Center
        </div>
        {NAV.map((n) => (
          <button key={n} onClick={() => setView(n)}
            className={"mb-1 block w-full rounded px-2 py-1.5 text-left text-xs " +
              (view === n ? "bg-cyan-500/10 text-cyan-300" : "text-slate-400 hover:text-slate-200")}>
            {n}{n === "Approvals" && pending.length > 0 ? " (" + pending.length + ")" : ""}
          </button>
        ))}
        <div className="mt-6 border-t border-slate-800 pt-3 text-xs">
          <Row k="user" v={me.username} />
          <Row k="role" v={me.role} accent="text-cyan-300" />
          <Row k="session" v={me.session_id.slice(0, 8)} />
        </div>
        <button onClick={() => { setToken(null); setMe(null); }}
          className="mt-3 w-full rounded border border-slate-800 px-2 py-1 text-[11px] text-slate-500 hover:text-slate-300">
          sign out
        </button>
        <button onClick={async () => { await api.reset(); setCurrent(null); setExec(null); await refresh(); }}
          className="mt-1 w-full rounded border border-slate-800 px-2 py-1 text-[11px] text-slate-500 hover:text-amber-300">
          reset demo
        </button>
      </aside>

      <section className="flex-1 overflow-auto p-5">
        <div className="mb-4 flex gap-2">
          <input value={message} onChange={(e) => setMessage(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
            className="flex-1 rounded border border-slate-800 bg-slate-950 px-3 py-2 text-sm outline-none focus:border-cyan-600"
            placeholder="Ask the agent to do something..." />
          <button onClick={send} disabled={busy}
            className="rounded border border-cyan-700 bg-cyan-500/10 px-4 text-xs font-bold text-cyan-300 disabled:opacity-40">
            PROPOSE
          </button>
          <button onClick={run} disabled={busy || !actionId}
            className="rounded border border-slate-700 px-4 text-xs font-bold text-slate-300 disabled:opacity-30">
            EXECUTE
          </button>
        </div>

        {error && <div className="mb-3 rounded border border-rose-800 bg-rose-500/10 p-2 text-xs text-rose-300">{error}</div>}

        {view === "Overview" && (
          <div className="space-y-4">
            {board && (
              <div className="grid grid-cols-3 gap-3 md:grid-cols-6">
                {Object.entries(board.totals).map(([k, v]: any) => (
                  <div key={k} className="rounded border border-slate-800 bg-slate-950/60 p-3">
                    <div className="text-2xl font-black text-slate-100">{v}</div>
                    <div className="text-[10px] uppercase tracking-wider text-slate-500">{k.replace(/_/g, " ")}</div>
                  </div>
                ))}
              </div>
            )}
            <Analysis a={current} />
            {exec && (
              <div className="grid gap-3 md:grid-cols-4">
                <Card title="Execution" tone={exec.execution_status === "executed" ? "LOW" : "CRITICAL"}>
                  <Row k="status" v={exec.execution_status} />
                  <Row k="snapshot" v={exec.snapshot_id ?? "none"} />
                </Card>
                <Card title="Verification" tone={exec.verification?.status === "VERIFIED" ? "LOW" : "CRITICAL"}>
                  <Row k="status" v={exec.verification?.status} />
                  {exec.verification?.problems?.map((p: string, i: number) => (
                    <div key={i} className="text-rose-300">• {p}</div>
                  ))}
                </Card>
                <Card title="Commit / Rollback" tone={exec.commit_status === "committed" ? "LOW" : "HIGH"}>
                  <Row k="commit" v={exec.commit_status} />
                  <Row k="rollback" v={exec.rollback_status} />
                </Card>
                <Card title="Tool Result">
                  <pre className="overflow-auto text-[10px] text-slate-400">
                    {JSON.stringify(exec.tool_result, null, 1)}
                  </pre>
                </Card>
              </div>
            )}
          </div>
        )}

        {view === "Live Actions" && (
          <div className="rounded border border-slate-800">
            <table className="w-full text-xs">
              <thead className="bg-slate-900/60 text-[10px] uppercase tracking-wider text-slate-500">
                <tr>{["id", "user", "action", "resource", "intent", "blast", "rev", "traj", "decision", "exec"].map((h) => (
                  <th key={h} className="px-2 py-2 text-left">{h}</th>))}</tr>
              </thead>
              <tbody>
                {actions.map((a) => (
                  <tr key={a.id} className="border-t border-slate-900 hover:bg-slate-900/40">
                    <td className="px-2 py-1.5 text-slate-500">{a.id}</td>
                    <td className="px-2 py-1.5">{a.user}</td>
                    <td className="px-2 py-1.5 text-cyan-300">{a.action}</td>
                    <td className="px-2 py-1.5">{a.resource}</td>
                    <td className="px-2 py-1.5 text-slate-400">{a.intent}</td>
                    <td className="px-2 py-1.5">{a.blast_radius}</td>
                    <td className="px-2 py-1.5">{a.reversibility}</td>
                    <td className="px-2 py-1.5">{a.trajectory}</td>
                    <td className="px-2 py-1.5">
                      <span className={"rounded border px-1.5 py-0.5 " + (DECISION_STYLE[a.decision] || "")}>{a.decision}</span>
                    </td>
                    <td className="px-2 py-1.5 text-slate-500">{a.execution_status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {view === "Trajectory" && board && (
          <div className="grid gap-3 md:grid-cols-2">
            <Card title="Your behaviour score" tone={current?.trajectory?.level}>
              <Row k="user" v={board.trajectory.user} />
              <Row k="score" v={board.trajectory.score + " / 20"} />
              {current?.trajectory?.signals?.map((s: string, i: number) => (
                <div key={i} className="text-slate-400">• {s}</div>
              ))}
            </Card>
            <Card title="Resources">
              {board.resources.map((r: any) => (
                <Row key={r.name} k={r.name}
                  v={[r.production ? "production" : "", r.sensitive ? "sensitive" : "",
                      r.disposable ? "disposable" : "", r.criticality].filter(Boolean).join(" · ")}
                  accent={r.production ? "text-rose-300" : ""} />
              ))}
            </Card>
          </div>
        )}

        {view === "Approvals" && (
          <div className="space-y-2">
            {approvals.length === 0 && <div className="text-xs text-slate-600">No approval requests.</div>}
            {approvals.map((a) => (
              <div key={a.id} className="flex items-center justify-between rounded border border-slate-800 bg-slate-950/60 p-3 text-xs">
                <div>
                  <div className="font-bold text-slate-200">#{a.id} · {a.action_name} → {a.resource}</div>
                  <div className="text-slate-500">
                    by {a.requested_by} · {a.required_level} · blast {a.blast_radius} · {a.reversibility}
                    {a.consumed ? " · consumed" : ""}
                  </div>
                  {!a.you_may_decide && <div className="text-amber-400">{a.decide_note}</div>}
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-slate-400">{a.status}</span>
                  {a.status === "pending" && a.you_may_decide && (
                    <>
                      <button onClick={() => decide(a.id, true)}
                        className="rounded border border-emerald-700 px-2 py-1 text-emerald-300">approve</button>
                      <button onClick={() => decide(a.id, false)}
                        className="rounded border border-rose-800 px-2 py-1 text-rose-300">reject</button>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {view === "Audit" && (
          <div className="space-y-3">
            {chain && (
              <div className={"rounded border p-3 text-xs " + (chain.valid
                ? "border-emerald-700 bg-emerald-500/10 text-emerald-300"
                : "border-rose-700 bg-rose-500/10 text-rose-300")}>
                chain {chain.valid ? "INTACT" : "TAMPERED"} · {chain.length} events
                {chain.broken_at ? " · broken at #" + chain.broken_at + " (" + chain.reason + ")" : ""}
              </div>
            )}
            <div className="rounded border border-slate-800">
              <table className="w-full text-[11px]">
                <thead className="bg-slate-900/60 text-[10px] uppercase tracking-wider text-slate-500">
                  <tr>{["id", "event", "user", "action", "decision", "prev", "hash"].map((h) => (
                    <th key={h} className="px-2 py-2 text-left">{h}</th>))}</tr>
                </thead>
                <tbody>
                  {audit.map((e) => (
                    <tr key={e.id} className="border-t border-slate-900">
                      <td className="px-2 py-1 text-slate-500">{e.id}</td>
                      <td className="px-2 py-1 text-cyan-300">{e.event_type}</td>
                      <td className="px-2 py-1">{e.user}</td>
                      <td className="px-2 py-1 text-slate-400">{e.action} {e.resource}</td>
                      <td className="px-2 py-1">{e.decision}</td>
                      <td className="px-2 py-1 text-slate-600">{e.previous_hash?.slice(0, 10)}</td>
                      <td className="px-2 py-1 text-slate-400">{e.current_hash?.slice(0, 10)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>
    </main>
  );
}
