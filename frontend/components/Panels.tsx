"use client";

import { DECISION_STYLE, SEVERITY_STYLE } from "@/lib/api";

export function Card({ title, tone, children }: any) {
  return (
    <div className="rounded border border-slate-800 bg-slate-950/60 p-3">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-[11px] uppercase tracking-widest text-slate-500">{title}</h3>
        {tone && <span className={"text-xs font-bold " + (SEVERITY_STYLE[tone] || "text-slate-300")}>{tone}</span>}
      </div>
      <div className="space-y-1 text-xs text-slate-300">{children}</div>
    </div>
  );
}

export function Row({ k, v, accent }: any) {
  return (
    <div className="flex justify-between gap-3">
      <span className="text-slate-500">{k}</span>
      <span className={"text-right " + (accent || "text-slate-200")}>{String(v)}</span>
    </div>
  );
}

export function Decision({ decision, reasons }: { decision: string; reasons: string[] }) {
  return (
    <div className={"rounded border p-4 " + (DECISION_STYLE[decision] || "border-slate-700")}>
      <div className="text-[11px] uppercase tracking-widest opacity-70">Policy Decision</div>
      <div className="my-1 text-2xl font-black tracking-tight">{decision}</div>
      <ul className="mt-2 space-y-1 text-xs opacity-90">
        {reasons?.map((r, i) => <li key={i}>— {r}</li>)}
      </ul>
    </div>
  );
}

export function Meter({ value, max, label }: { value: number; max: number; label: string }) {
  const pct = Math.min(100, (value / max) * 100);
  const color = pct >= 75 ? "bg-rose-500" : pct >= 50 ? "bg-orange-500" : pct >= 25 ? "bg-amber-500" : "bg-emerald-500";
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs">
        <span className="text-slate-500">{label}</span>
        <span className="font-bold text-slate-200">{value}/{max}</span>
      </div>
      <div className="h-2 w-full rounded bg-slate-800">
        <div className={"h-2 rounded " + color} style={{ width: pct + "%" }} />
      </div>
    </div>
  );
}

export function Analysis({ a }: { a: any }) {
  if (!a) return <div className="text-xs text-slate-600">No action analysed yet.</div>;
  const inv = a.safety_invariants;
  return (
    <div className="grid gap-3 lg:grid-cols-3">
      <div className="space-y-3 lg:col-span-2">
        <div className="rounded border border-slate-800 bg-slate-950/60 p-3">
          <Row k="action" v={a.action.name} accent="text-cyan-300" />
          <Row k="resource" v={a.action.resource} />
          <Row k="user / role" v={a.identity.user + " / " + a.identity.role} />
          <Row k="agent" v={a.identity.agent} />
          <Row k="session" v={a.identity.session.slice(0, 12)} />
          <Row k="request" v={a.user_request} />
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          <Card title="Intent Boundary" tone={a.intent.status === "WITHIN_SCOPE" ? "LOW" : a.intent.status === "SCOPE_EXPANSION" ? "MODERATE" : "CRITICAL"}>
            <Row k="status" v={a.intent.status} />
            <div className="text-slate-400">{a.intent.reason}</div>
          </Card>

          <Card title="Authorization" tone={a.authorization.authorized ? "LOW" : "CRITICAL"}>
            <Row k="authorized" v={a.authorization.authorized ? "YES" : "DENIED"} />
            <div className="text-slate-400">{a.authorization.reason}</div>
          </Card>

          <Card title="Dependency Graph">
            <Row k="dependents" v={a.dependencies.count} />
            <Row k="direct" v={a.dependencies.direct.join(", ") || "none"} />
            <Row k="transitive" v={a.dependencies.transitive.join(", ") || "none"} />
          </Card>

          <Card title="Consequences">
            {a.consequences.direct?.map((d: string, i: number) => (
              <div key={i} className="text-slate-300">• {d}</div>
            ))}
            {a.consequences.indirect?.map((d: string, i: number) => (
              <div key={i} className="text-slate-500">↳ {d}</div>
            ))}
          </Card>

          <Card title="Blast Radius" tone={a.blast_radius.severity}>
            <Meter value={a.blast_radius.score} max={10} label="score" />
            <div className="mt-2 space-y-0.5">
              {a.blast_radius.reasons.map((r: string, i: number) => (
                <div key={i} className="text-slate-400">• {r}</div>
              ))}
            </div>
          </Card>

          <Card title="Reversibility" tone={a.reversibility.level === "R3" ? "CRITICAL" : a.reversibility.level === "R2" ? "HIGH" : "LOW"}>
            <Row k="level" v={a.reversibility.level} />
            <div className="text-slate-400">{a.reversibility.explanation}</div>
            <Row k="rollback" v={a.reversibility.rollback_supported ? "supported" : "unavailable"} />
          </Card>

          <Card title="Trajectory" tone={a.trajectory.level}>
            <Meter value={a.trajectory.score} max={20} label="behaviour score" />
            <div className="mt-2 space-y-0.5">
              {a.trajectory.signals.map((s: string, i: number) => (
                <div key={i} className="text-slate-400">• {s}</div>
              ))}
            </div>
            <Row k="history" v={a.trajectory.history_size + " actions / " + a.trajectory.sessions_seen + " sessions"} />
          </Card>

          <Card title="Safety Invariants" tone={inv.passed ? "LOW" : "CRITICAL"}>
            <Row k="checked" v={inv.checked.join(", ")} />
            {inv.violations.length === 0 ? (
              <div className="text-emerald-300">all invariants hold</div>
            ) : (
              inv.violations.map((v: any, i: number) => (
                <div key={i} className="text-rose-300">✗ {v.code}: {v.detail}</div>
              ))
            )}
          </Card>
        </div>
      </div>

      <div className="space-y-3">
        <Decision decision={a.policy_decision.decision} reasons={a.policy_decision.reasons} />
        <Card title="Impact Preview">
          <Row k="records affected" v={a.consequences.affected_records + " / " + a.consequences.total_records} />
          <Row k="resources affected" v={a.consequences.affected_resource_count} />
          <Row k="sensitivity" v={a.consequences.data_sensitivity} />
          <Row k="criticality" v={a.consequences.resource_criticality} />
          <Row k="production" v={a.resource.is_production ? "YES" : "no"} accent={a.resource.is_production ? "text-rose-300" : ""} />
          <Row k="disposable" v={a.resource.is_disposable ? "yes" : "no"} />
        </Card>
        {a.approval && (
          <Card title="Approval">
            <Row k="id" v={a.approval.id} />
            <Row k="level" v={a.approval.required_level} />
            <Row k="status" v={a.approval.status} />
          </Card>
        )}
      </div>
    </div>
  );
}
