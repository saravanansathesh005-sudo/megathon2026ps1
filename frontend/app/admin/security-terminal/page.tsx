"use client";

import { useCallback, useEffect, useState } from "react";

import { api, BAND_STYLE, DECISION_STYLE, loadToken, SEVERITY_STYLE, setToken } from "@/lib/api";

/**
 * AEGIS Admin Security Terminal — READ ONLY.
 *
 * There is deliberately no Approve, Reject, Override, Force Execute, Ignore Policy,
 * Make ALLOW, Disable, Reset or Clear control anywhere in this file. The backend
 * exposes no write endpoint for security decisions either; hiding a button is not
 * a security control, so the gate is server-side (require_observer).
 */

const TABS = ["Overview", "Events", "Users", "Audit"] as const;

function Row({ k, v, accent }: any) {
  return (
    <div className="flex justify-between gap-3 py-0.5">
      <span className="text-slate-500">{k}</span>
      <span className={"text-right " + (accent || "text-slate-200")}>{String(v)}</span>
    </div>
  );
}

function Card({ title, tone, children }: any) {
  return (
    <div className="rounded border border-slate-800 bg-slate-950/60 p-3">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-[10px] uppercase tracking-widest text-slate-500">{title}</h3>
        {tone && <span className={"text-[11px] font-bold " + (SEVERITY_STYLE[tone] || "text-slate-300")}>{tone}</span>}
      </div>
      <div className="space-y-0.5 text-xs text-slate-300">{children}</div>
    </div>
  );
}

export default function SecurityTerminal() {
  const [state, setState] = useState<"loading" | "denied" | "anon" | "ok">("loading");
  const [me, setMe] = useState<any>(null);
  const [tab, setTab] = useState<(typeof TABS)[number]>("Overview");
  const [overview, setOverview] = useState<any>(null);
  const [events, setEvents] = useState<any[]>([]);
  const [users, setUsers] = useState<any[]>([]);
  const [audit, setAudit] = useState<any>(null);
  const [detail, setDetail] = useState<any>(null);
  const [history, setHistory] = useState<any>(null);
  const [filter, setFilter] = useState("");
  const [signingIn, setSigningIn] = useState(false);
  const [signInError, setSignInError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const [o, e, u, a] = await Promise.all([
      api.secOverview(), api.secEvents(), api.secUsers(), api.secAudit(),
    ]);
    setOverview(o); setEvents(e.events); setUsers(u.users); setAudit(a);
  }, []);

  useEffect(() => {
    const t = loadToken();
    if (!t) { setState("anon"); return; }
    api.me()
      .then(async (u) => {
        setMe(u);
        if (!u.is_observer) { setState("denied"); return; }
        await load();
        setState("ok");
      })
      .catch((err) => setState(err?.status === 403 ? "denied" : "anon"));
  }, [load]);

  if (state === "loading") {
    return <main className="grid min-h-screen place-items-center text-sm text-slate-500">
      Verifying credentials…</main>;
  }

  if (state === "anon" || state === "denied") {
    return (
      <main className="grid min-h-screen place-items-center px-4 font-mono">
        <div className="w-full max-w-md rounded border border-rose-900/60 bg-rose-500/5 p-6">
          <div className="text-center">
            <div className="text-xs uppercase tracking-widest text-rose-400">
              403 · access denied
            </div>
            <h1 className="mt-2 text-xl font-semibold text-slate-100">
              Admin Security Terminal
            </h1>
            <p className="mt-3 text-sm text-slate-400">
              {state === "anon"
                ? "This area requires an authenticated observer account."
                : "Signed in as " + (me?.username ?? "this account") +
                  " (role " + (me?.role ?? "?") + "). That role has no security " +
                  "observability access."}
            </p>
            <p className="mt-4 text-[11px] text-slate-600">
              The backend enforces this. Role is resolved server-side; a role supplied
              by the client is ignored.
            </p>
          </div>

          <form onSubmit={signIn}
            className="mt-6 border-t border-slate-800 pt-5">
            <p className="mb-3 text-center text-[10px] uppercase tracking-widest text-slate-500">
              Observer sign-in
            </p>
            <input name="username" defaultValue="admin" autoComplete="username"
              aria-label="Observer username"
              className="mb-2 w-full rounded border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-200 outline-none focus:border-cyan-700" />
            <input name="password" type="password" defaultValue="" autoComplete="current-password"
              placeholder="password" aria-label="Observer password"
              className="mb-3 w-full rounded border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-200 outline-none focus:border-cyan-700" />
            <button type="submit" disabled={signingIn}
              className="w-full rounded border border-cyan-700 bg-cyan-500/10 px-3 py-2 text-xs font-bold text-cyan-300 disabled:opacity-40">
              {signingIn ? "verifying…" : "sign in"}
            </button>
            {signInError && (
              <p className="mt-2 text-center text-[11px] text-rose-300">{signInError}</p>
            )}
            <p className="mt-3 text-center text-[10px] text-slate-600">
              demo observers: admin / admin123 · secadmin / secadmin123
            </p>
          </form>

          <a href="/" className="mt-5 block text-center text-xs text-slate-500 underline">
            Return to the assistant
          </a>
        </div>
      </main>
    );
  }

  const shown = events.filter((e) =>
    !filter || (e.user + e.action + e.resource + e.decision).toLowerCase().includes(filter.toLowerCase()));

  return (
    <main className="flex min-h-screen font-mono">
      <aside className="w-52 shrink-0 border-r border-slate-800 bg-slate-950 p-4">
        <div className="text-sm font-bold tracking-tight text-cyan-300">AEGIS</div>
        <div className="mb-1 text-[10px] uppercase tracking-widest text-slate-600">
          Security Terminal
        </div>
        <div className="mb-5 rounded bg-slate-900 px-2 py-1 text-[9px] uppercase tracking-widest text-amber-400">
          read-only
        </div>
        {TABS.map((t) => (
          <button key={t} onClick={() => { setTab(t); setDetail(null); setHistory(null); }}
            className={"mb-1 block w-full rounded px-2 py-1.5 text-left text-xs " +
              (tab === t ? "bg-cyan-500/10 text-cyan-300" : "text-slate-400 hover:text-slate-200")}>
            {t}
          </button>
        ))}
        <div className="mt-6 border-t border-slate-800 pt-3 text-[11px]">
          <Row k="observer" v={me.username} />
          <Row k="role" v={me.role} accent="text-cyan-300" />
        </div>
        <button onClick={() => { setToken(null); location.href = "/"; }}
          className="mt-3 w-full rounded border border-slate-800 px-2 py-1 text-[10px] text-slate-500 hover:text-slate-300">
          sign out
        </button>
      </aside>

      <section className="flex-1 overflow-auto p-5">
        <div className="mb-4 flex items-center justify-between">
          <h1 className="text-sm font-bold tracking-widest text-slate-200">
            AEGIS ADMIN SECURITY TERMINAL
          </h1>
          <span className="rounded border border-slate-700 px-2 py-1 text-[10px] text-slate-500">
            decision authority: AEGIS · observers cannot change outcomes
          </span>
        </div>

        {tab === "Overview" && overview && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-7">
              {Object.entries(overview.totals).map(([k, v]: any) => (
                <div key={k} className="rounded border border-slate-800 bg-slate-950/60 p-3">
                  <div className="text-xl font-black text-slate-100">{v}</div>
                  <div className="text-[9px] uppercase tracking-wider text-slate-500">
                    {k.replace(/_/g, " ")}
                  </div>
                </div>
              ))}
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <Card title="Terms & Conditions bands">
                {Object.entries(overview.terms_bands).map(([k, v]: any) => (
                  <div key={k} className="flex justify-between py-0.5">
                    <span className={"rounded px-1.5 text-[10px] " + (BAND_STYLE[k] || "")}>{k}</span>
                    <span className="text-slate-200">{v}</span>
                  </div>
                ))}
              </Card>
              <Card title="Audit chain">
                <Row k="status" v={overview.audit.valid ? "INTACT" : "TAMPERED"}
                  accent={overview.audit.valid ? "text-emerald-300" : "text-rose-300"} />
                <Row k="events" v={overview.audit.length} />
                {overview.audit.broken_at && <Row k="broken at" v={"#" + overview.audit.broken_at} accent="text-rose-300" />}
              </Card>
            </div>
            <div className="rounded border border-slate-800">
              <EventTable rows={overview.recent} onPick={pick} />
            </div>
          </div>
        )}

        {tab === "Events" && (
          <div className="space-y-3">
            <input value={filter} onChange={(e) => setFilter(e.target.value)}
              placeholder="filter by user, action, resource or decision…"
              className="w-full rounded border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-200 outline-none focus:border-cyan-700" />
            <div className="rounded border border-slate-800">
              <EventTable rows={shown} onPick={pick} />
            </div>
            {detail && <EventDetail detail={detail} />}
          </div>
        )}

        {tab === "Users" && (
          <div className="space-y-3">
            <div className="rounded border border-slate-800">
              <table className="w-full text-xs">
                <thead className="bg-slate-900/60 text-[9px] uppercase tracking-wider text-slate-500">
                  <tr>{["user", "role", "events", "denied", "high impact", "trajectory", "status"].map((h) =>
                    <th key={h} className="px-2 py-2 text-left">{h}</th>)}</tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.user_id} onClick={() => showTrajectory(u.user_id)}
                      className="cursor-pointer border-t border-slate-900 hover:bg-slate-900/40">
                      <td className="px-2 py-1.5">{u.email || u.username}</td>
                      <td className="px-2 py-1.5 text-slate-400">{u.role}</td>
                      <td className="px-2 py-1.5">{u.events}</td>
                      <td className="px-2 py-1.5">{u.denied}</td>
                      <td className="px-2 py-1.5">{u.high_impact}</td>
                      <td className={"px-2 py-1.5 " + (SEVERITY_STYLE[u.trajectory_level] || "")}>
                        {u.trajectory}/20 {u.trajectory_level}
                      </td>
                      <td className={"px-2 py-1.5 " + (u.status === "RESTRICTED" ? "text-rose-300" : "text-slate-500")}>
                        {u.status}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {users.filter((u) => u.status === "RESTRICTED").map((u) => (
              <Card key={u.user_id} title={"Automatic restriction · " + (u.email || u.username)} tone="EXTREME">
                <Row k="reason" v={u.restriction_reason} />
                <Row k="expires" v={u.restriction_expires} />
                <p className="pt-1 text-[10px] text-slate-600">
                  Applied by AEGIS. It expires on its own; there is no manual unblock.
                </p>
              </Card>
            ))}
            {history && (
              <Card title="Trajectory history">
                {history.history.map((h: any, i: number) => (
                  <div key={i} className="flex items-center gap-2 py-0.5">
                    <span className="w-10 text-slate-600">#{h.action_id}</span>
                    <span className="w-36 text-slate-400">{h.action}</span>
                    <span className={"w-24 " + (SEVERITY_STYLE[h.level] || "")}>{h.score}/20 {h.level}</span>
                    <span className={"rounded border px-1.5 text-[10px] " + (DECISION_STYLE[h.decision] || "")}>
                      {h.decision}
                    </span>
                  </div>
                ))}
              </Card>
            )}
          </div>
        )}

        {tab === "Audit" && audit && (
          <div className="space-y-3">
            <div className={"rounded border p-3 text-xs " + (audit.chain.valid
              ? "border-emerald-700 bg-emerald-500/10 text-emerald-300"
              : "border-rose-700 bg-rose-500/10 text-rose-300")}>
              chain {audit.chain.valid ? "INTACT" : "TAMPERED"} · {audit.chain.length} events
              {audit.chain.broken_at ? " · broken at #" + audit.chain.broken_at : ""}
            </div>
            <div className="rounded border border-slate-800">
              <table className="w-full text-[11px]">
                <thead className="bg-slate-900/60 text-[9px] uppercase tracking-wider text-slate-500">
                  <tr>{["id", "event", "user", "action", "decision", "prev", "hash"].map((h) =>
                    <th key={h} className="px-2 py-2 text-left">{h}</th>)}</tr>
                </thead>
                <tbody>
                  {audit.events.map((e: any) => (
                    <tr key={e.id} className="border-t border-slate-900">
                      <td className="px-2 py-1 text-slate-600">{e.id}</td>
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

  async function pick(id: number) { setDetail(await api.secEvent(id)); setTab("Events"); }
  async function showTrajectory(userId: number) { setHistory(await api.secTrajectory(userId)); }

  /** Observer sign-in. The backend still decides whether this account may observe. */
  async function signIn(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    setSigningIn(true); setSignInError(null);
    try {
      const { token } = await api.login(
        String(form.get("username") || ""), String(form.get("password") || ""));
      setToken(token);
      const who = await api.me();
      setMe(who);
      if (!who.is_observer) {
        setState("denied");
        setSignInError("That account is not an observer.");
      } else {
        await load();
        setState("ok");
      }
    } catch (err: any) {
      setSignInError(err?.status === 401
        ? "Incorrect username or password."
        : "Sign-in unavailable. Is the backend running on :8000?");
    }
    setSigningIn(false);
  }
}

function EventTable({ rows, onPick }: any) {
  return (
    <table className="w-full text-xs">
      <thead className="bg-slate-900/60 text-[9px] uppercase tracking-wider text-slate-500">
        <tr>{["time", "user", "action", "band", "trajectory", "blast", "decision", "status"].map((h) =>
          <th key={h} className="px-2 py-2 text-left">{h}</th>)}</tr>
      </thead>
      <tbody>
        {rows.map((e: any) => (
          <tr key={e.id} onClick={() => onPick(e.id)}
            className="cursor-pointer border-t border-slate-900 hover:bg-slate-900/40">
            <td className="px-2 py-1.5 text-slate-600">{(e.created_at || "").slice(11, 19)}</td>
            <td className="px-2 py-1.5">{e.user}</td>
            <td className="px-2 py-1.5 text-cyan-300">{e.action} <span className="text-slate-600">{e.resource}</span></td>
            <td className="px-2 py-1.5">
              <span className={"rounded px-1.5 text-[10px] " + (BAND_STYLE[e.terms_category] || "")}>
                {e.terms_category}
              </span>
            </td>
            <td className="px-2 py-1.5">{e.trajectory}/20</td>
            <td className="px-2 py-1.5">{e.blast_radius}</td>
            <td className="px-2 py-1.5">
              <span className={"rounded border px-1.5 py-0.5 " + (DECISION_STYLE[e.decision] || "")}>
                {e.decision}
              </span>
            </td>
            <td className="px-2 py-1.5 text-slate-600">{e.execution_status}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function EventDetail({ detail }: any) {
  const a = detail.analysis || {};
  const inv = a.safety_invariants || { violations: [], checked: [] };
  return (
    <div className="rounded border border-slate-800 bg-slate-950/60 p-4">
      <div className="mb-3 flex items-baseline justify-between">
        <h2 className="text-sm font-bold tracking-wide text-slate-100">
          Security Event #{detail.id}
        </h2>
        <span className={"rounded border px-2 py-1 text-xs font-black " + (DECISION_STYLE[detail.decision] || "")}>
          {detail.decision}
        </span>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <Card title="User">
          <Row k="email" v={detail.email || "—"} />
          <Row k="username" v={detail.user} />
          <Row k="role" v={detail.role} />
          <Row k="session" v={(detail.session || "").slice(0, 12)} />
          <Row k="time" v={detail.created_at} />
        </Card>
        <Card title="Request">
          <div className="text-slate-300">“{detail.user_request}”</div>
        </Card>
        <Card title="Planner proposal">
          <Row k="action" v={detail.action} accent="text-cyan-300" />
          <Row k="resource" v={detail.resource || "—"} />
          <Row k="source" v={detail.proposal_source} />
          <Row k="validated" v={a.action?.known ? "yes" : "no"} />
        </Card>

        <Card title="Authorization" tone={a.authorization?.authorized ? "LOW" : "CRITICAL"}>
          <Row k="result" v={a.authorization?.authorized ? "AUTHORIZED" : "DENIED"} />
          <div className="text-slate-400">{a.authorization?.reason}</div>
        </Card>
        <Card title="Intent / scope"
          tone={a.intent?.status === "WITHIN_SCOPE" ? "LOW" : a.intent?.status === "SCOPE_EXPANSION" ? "MODERATE" : "CRITICAL"}>
          <Row k="status" v={a.intent?.status} />
          <div className="text-slate-400">{a.intent?.reason}</div>
        </Card>
        <Card title="Terms & Conditions">
          <span className={"rounded px-1.5 text-[10px] " + (BAND_STYLE[a.terms?.category] || "")}>
            {a.terms?.category}
          </span>
          <div className="pt-1 text-slate-400">{a.terms?.meaning}</div>
          {(a.terms?.reasons || []).map((r: string, i: number) => (
            <div key={i} className="text-slate-500">• {r}</div>
          ))}
        </Card>

        <Card title="Blast radius" tone={a.blast_radius?.severity}>
          <Row k="score" v={(a.blast_radius?.score ?? "—") + " / 10"} />
          <Row k="affected resources" v={a.consequences?.affected_resource_count} />
          <Row k="records" v={a.consequences?.affected_records + " / " + a.consequences?.total_records} />
          {(a.blast_radius?.reasons || []).map((r: string, i: number) => (
            <div key={i} className="text-slate-500">• {r}</div>
          ))}
        </Card>
        <Card title="Reversibility" tone={a.reversibility?.level === "R3" ? "CRITICAL" : a.reversibility?.level === "R2" ? "HIGH" : "LOW"}>
          <Row k="level" v={a.reversibility?.level} />
          <div className="text-slate-400">{a.reversibility?.explanation}</div>
          <Row k="rollback" v={a.reversibility?.rollback_supported ? "supported" : "unavailable"} />
        </Card>
        <Card title="Trajectory" tone={a.trajectory?.level}>
          <Row k="score" v={a.trajectory?.score + " / 20"} />
          <Row k="level" v={a.trajectory?.level} />
          {(a.trajectory?.signals || []).map((s: string, i: number) => (
            <div key={i} className="text-slate-500">• {s}</div>
          ))}
        </Card>

        <Card title="Safety invariants" tone={inv.passed ? "LOW" : "CRITICAL"}>
          <Row k="checked" v={(inv.checked || []).join(", ")} />
          {inv.violations?.length === 0
            ? <div className="text-emerald-300">all PASS</div>
            : inv.violations.map((v: any, i: number) => (
              <div key={i} className="text-rose-300">✗ {v.code} FAIL — {v.detail}</div>
            ))}
        </Card>
        <Card title="Execution">
          <Row k="status" v={detail.execution_status} />
          <Row k="verification" v={detail.verification_status} />
          <Row k="commit" v={detail.commit_status} />
        </Card>
        <div className={"rounded border p-3 " + (DECISION_STYLE[detail.decision] || "border-slate-700")}>
          <div className="text-[10px] uppercase tracking-widest opacity-70">Final decision</div>
          <div className="my-1 text-xl font-black">{detail.decision}</div>
          <ul className="space-y-0.5 text-[11px] opacity-90">
            {(a.policy_decision?.reasons || []).map((r: string, i: number) => <li key={i}>— {r}</li>)}
          </ul>
          <p className="mt-3 border-t border-current/20 pt-2 text-[10px] opacity-70">
            AEGIS automatically made this decision. It cannot be changed here.
          </p>
        </div>
      </div>
    </div>
  );
}
