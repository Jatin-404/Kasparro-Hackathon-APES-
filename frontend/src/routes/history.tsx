import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ArrowRight, GitCompareArrows, Loader2, RotateCcw, X } from "lucide-react";
import { TopNav } from "@/components/TopNav";
import {
  clearTestAudits,
  compareAudits,
  fetchAuditsByStore,
  fetchRecentAudits,
  type ApiDimension,
  type AuditCompareResult,
  type AuditSummary,
} from "@/lib/audit-api";

export const Route = createFileRoute("/history")({
  validateSearch: (search: Record<string, unknown>) => ({
    store: typeof search.store === "string" ? search.store : undefined,
  }),
  head: () => ({
    meta: [
      { title: "APES - Audit History" },
      { name: "description", content: "Track AI readiness score trends and compare audit runs over time." },
    ],
  }),
  component: HistoryPage,
});

type Filter = "all" | "improved" | "declined" | "critical";
type XAxisMode = "time" | "date" | "auto";

function HistoryPage() {
  const navigate = useNavigate();
  const { store } = Route.useSearch();
  const [audits, setAudits] = useState<AuditSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [clearing, setClearing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<Filter>("all");
  const [xAxisMode, setXAxisMode] = useState<XAxisMode>("auto");
  const [compareBase, setCompareBase] = useState<AuditSummary | null>(null);

  async function loadAudits(showSkeleton = true) {
    if (showSkeleton) setLoading(true);
    setError(null);
    try {
      const data = store ? await fetchAuditsByStore(store) : await fetchRecentAudits(20);
      setAudits(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load audit history");
    } finally {
      if (showSkeleton) setLoading(false);
    }
  }

  useEffect(() => {
    let mounted = true;
    async function load() {
      if (!mounted) return;
      await loadAudits(true);
    }
    load();
    const timer = window.setInterval(() => {
      if (audits.some((audit) => audit.status === "running")) loadAudits(false);
    }, 5000);
    return () => {
      mounted = false;
      window.clearInterval(timer);
    };
  }, [store]);

  const filtered = useMemo(() => audits.filter((audit) => matchesFilter(audit, filter)), [audits, filter]);
  const chartAudits = useMemo(() => [...audits].reverse(), [audits]);
  const chartDates = useMemo(() => chartAudits.map((audit) => audit.created_at).filter(Boolean) as string[], [chartAudits]);
  const chartData = useMemo(
    () =>
      chartAudits.map((audit) => ({
        xLabel: getXAxisLabel(audit.created_at, xAxisMode, chartDates),
        created_at: audit.created_at,
        audit_id: audit.audit_id,
        before_score: audit.before_score ?? 0,
        after_score: audit.after_score ?? 0,
        failed_queries: audit.failed_queries ?? 0,
      })),
    [chartAudits, chartDates, xAxisMode],
  );

  function openAudit(auditId: string) {
    navigate({ to: "/audit/$auditId", params: { auditId } });
  }

  async function clearStoreAudits() {
    if (!store || clearing) return;
    const confirmed = window.confirm("Delete all audits for this store except the most recent one?");
    if (!confirmed) return;
    setClearing(true);
    setError(null);
    try {
      await clearTestAudits(store);
      await loadAudits(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not clear test audits");
    } finally {
      setClearing(false);
    }
  }

  return (
    <div className="min-h-screen">
      <TopNav showActions />
      <main className="mx-auto max-w-7xl space-y-6 px-6 py-8">
        <section className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="font-display text-3xl font-semibold">Audit History</h1>
              {store ? <span className="pill pill-primary">{store}</span> : null}
            </div>
            <p className="mt-2 text-sm text-muted-foreground">Track your AI readiness score over time.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {store ? (
              <button
                type="button"
                onClick={clearStoreAudits}
                disabled={clearing || audits.length <= 1}
                className="btn-ghost inline-flex items-center gap-1.5 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {clearing ? <Loader2 className="h-4 w-4 animate-spin-soft" /> : <RotateCcw className="h-4 w-4" />}
                Clear Test Audits
              </button>
            ) : null}
            <Link to="/" className="btn-primary inline-flex items-center gap-1.5">
              New Audit <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </section>

        <section className="surface-card p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="label-tiny">Score Trend</div>
              <h2 className="mt-1 font-display text-xl font-semibold">AI Readiness Score Over Time</h2>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              {audits.length === 1 ? <span className="pill pill-muted">Run more audits to see trends</span> : null}
              <div className="inline-flex rounded-lg border border-border bg-background p-1 text-sm">
                {(["time", "date", "auto"] as XAxisMode[]).map((mode) => (
                  <button
                    key={mode}
                    type="button"
                    onClick={() => setXAxisMode(mode)}
                    className={`rounded-md px-3 py-1.5 transition-colors ${
                      xAxisMode === mode ? "bg-primary text-primary-foreground shadow" : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {mode[0].toUpperCase() + mode.slice(1)}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="mt-6 h-[360px]">
            {loading ? (
              <SkeletonChart />
            ) : error ? (
              <ErrorBox message={error} />
            ) : audits.length === 0 ? (
              <EmptyState />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={chartData}
                  margin={{ top: 16, right: 24, bottom: 8, left: 0 }}
                  onClick={(event) => {
                    const auditId = event?.activePayload?.[0]?.payload?.audit_id;
                    if (auditId) openAudit(auditId);
                  }}
                >
                  <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
                  <XAxis dataKey="xLabel" stroke="var(--muted-foreground)" />
                  <YAxis domain={[0, 100]} stroke="var(--muted-foreground)" />
                  <ReferenceLine y={70} stroke="var(--success)" strokeDasharray="4 4" />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend />
                  <Line type="monotone" dataKey="before_score" name="Before score" stroke="var(--warning)" strokeWidth={3} dot={{ r: 5 }} activeDot={{ r: 7 }} />
                  <Line type="monotone" dataKey="after_score" name="After score" stroke="var(--success)" strokeWidth={3} strokeDasharray="7 5" dot={{ r: 5 }} activeDot={{ r: 7 }} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </section>

        <section className="surface-card p-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <h2 className="font-display text-xl font-semibold">All Audits</h2>
            <div className="flex flex-wrap gap-2">
              {(["all", "improved", "declined", "critical"] as Filter[]).map((item) => (
                <button
                  key={item}
                  type="button"
                  onClick={() => setFilter(item)}
                  className={`pill ${filter === item ? "pill-primary" : "pill-muted"}`}
                >
                  {item[0].toUpperCase() + item.slice(1)}
                </button>
              ))}
            </div>
          </div>

          <div className="mt-5 overflow-x-auto">
            {loading ? (
              <SkeletonRows />
            ) : filtered.length === 0 ? (
              <EmptyState />
            ) : (
              <table className="w-full min-w-[920px] border-separate border-spacing-y-2 text-left text-sm">
                <thead className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2">Date</th>
                    <th className="px-3 py-2">Store</th>
                    <th className="px-3 py-2">Before Score</th>
                    <th className="px-3 py-2">After Score</th>
                    <th className="px-3 py-2">Delta</th>
                    <th className="px-3 py-2">Failed Queries</th>
                    <th className="px-3 py-2">Status</th>
                    <th className="px-3 py-2">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((audit) => (
                    <tr key={audit.audit_id} className={audit.status === "running" ? "animate-pulse" : ""}>
                      <td className="rounded-l-lg border-y border-l border-border bg-background/70 px-3 py-3">
                        <div>{friendlyDate(audit.created_at)}</div>
                      </td>
                      <td className="border-y border-border bg-background/70 px-3 py-3 font-mono text-xs text-muted-foreground">{audit.shop_url}</td>
                      <td className="border-y border-border bg-background/70 px-3 py-3 font-mono">{audit.before_score ?? "-"}/100</td>
                      <td className="border-y border-border bg-background/70 px-3 py-3 font-mono">{audit.after_score ?? "-"}/100</td>
                      <td className="border-y border-border bg-background/70 px-3 py-3"><DeltaBadge value={audit.score_delta} /></td>
                      <td className="border-y border-border bg-background/70 px-3 py-3">{audit.failed_queries ?? 0}/20 failed</td>
                      <td className="border-y border-border bg-background/70 px-3 py-3"><StatusBadge status={audit.status} /></td>
                      <td className="rounded-r-lg border-y border-r border-border bg-background/70 px-3 py-3">
                        <div className="flex gap-2">
                          <button type="button" onClick={() => openAudit(audit.audit_id)} className="btn-ghost text-xs">Open</button>
                          <button type="button" onClick={() => setCompareBase(audit)} className="btn-ghost inline-flex items-center gap-1 text-xs">
                            <GitCompareArrows className="h-3.5 w-3.5" /> Compare
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </section>
      </main>

      {compareBase ? (
        <CompareModal
          base={compareBase}
          audits={audits}
          onClose={() => setCompareBase(null)}
          onOpen={openAudit}
        />
      ) : null}
    </div>
  );
}

function CustomTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const row = payload[0]?.payload;
  const fullDate = row.created_at
    ? new Date(row.created_at).toLocaleString([], {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "";
  return (
    <div className="rounded-lg border border-border bg-background p-3 text-xs shadow-xl">
      <div className="font-mono text-muted-foreground">{fullDate}</div>
      <div className="mt-2 text-warning">Before: {row.before_score}/100</div>
      <div className="text-success">After: {row.after_score}/100</div>
      <div className="mt-1 text-muted-foreground">Failed: {row.failed_queries}/20</div>
      <div className="mt-2 text-foreground">Click to open audit</div>
    </div>
  );
}

function CompareModal({ base, audits, onClose, onOpen }: { base: AuditSummary; audits: AuditSummary[]; onClose: () => void; onOpen: (auditId: string) => void }) {
  const [targetId, setTargetId] = useState(audits.find((audit) => audit.audit_id !== base.audit_id)?.audit_id || "");
  const [result, setResult] = useState<AuditCompareResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!targetId) return;
    let mounted = true;
    setLoading(true);
    setError(null);
    compareAudits(base.audit_id, targetId)
      .then((data) => mounted && setResult(data))
      .catch((err) => mounted && setError(err instanceof Error ? err.message : "Comparison failed"))
      .finally(() => mounted && setLoading(false));
    return () => {
      mounted = false;
    };
  }, [base.audit_id, targetId]);

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/70 px-4">
      <div className="surface-card max-h-[88vh] w-full max-w-4xl overflow-y-auto p-6">
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="label-tiny">Compare Audits</div>
            <h2 className="mt-1 font-display text-2xl font-semibold">Audit A vs Audit B</h2>
          </div>
          <button type="button" onClick={onClose} className="btn-ghost"><X className="h-4 w-4" /></button>
        </div>

        <label className="mt-5 block text-sm font-medium">
          Compare against
          <select value={targetId} onChange={(event) => setTargetId(event.target.value)} className="mt-2 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none">
            {audits.filter((audit) => audit.audit_id !== base.audit_id).map((audit) => (
              <option key={audit.audit_id} value={audit.audit_id}>
                {friendlyDateTime(audit.created_at)} - {audit.before_score}/100
              </option>
            ))}
          </select>
        </label>

        {loading ? <div className="mt-6 text-sm text-muted-foreground">Loading comparison...</div> : null}
        {error ? <ErrorBox message={error} /> : null}
        {result ? (
          <div className="mt-6 space-y-5">
            <div className="grid gap-4 md:grid-cols-2">
              <CompareSide title="Audit A" side={result.audit_a} />
              <CompareSide title="Audit B" side={result.audit_b} />
            </div>
            <div className="rounded-lg border border-primary/30 bg-primary/10 p-4">
              <div className="font-display text-lg font-semibold">
                Change: <DeltaText value={result.delta.score_change} /> {result.delta.direction.toUpperCase()}
              </div>
              <div className="mt-2 text-sm text-muted-foreground">
                Failed queries changed by {signed(result.delta.failed_queries_change)}. High severity issues changed by {signed(result.delta.high_findings_change)}.
              </div>
            </div>
            <DimensionCompare a={result.audit_a.dimensions} b={result.audit_b.dimensions} />
            <button type="button" onClick={() => onOpen(result.audit_b.audit_id)} className="btn-primary">
              Open Audit B <ArrowRight className="ml-1 inline h-4 w-4" />
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function CompareSide({ title, side }: { title: string; side: AuditCompareResult["audit_a"] }) {
  return (
    <div className="rounded-lg border border-border bg-background/70 p-4">
      <div className="label-tiny">{title}</div>
      <div className="mt-2 font-mono text-xs text-muted-foreground">{friendlyDateTime(side.created_at)}</div>
      <div className="mt-4 space-y-2 text-sm">
        <Row label="Before Score" value={`${side.before_score ?? "-"}/100`} />
        <Row label="After Score" value={`${side.after_score ?? "-"}/100`} />
        <Row label="Failed" value={`${side.failed_queries ?? 0}/20`} />
        <Row label="High Issues" value={side.high_findings} />
      </div>
    </div>
  );
}

function DimensionCompare({ a, b }: { a: ApiDimension[]; b: ApiDimension[] }) {
  return (
    <table className="w-full text-sm">
      <thead className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
        <tr><th className="py-2 text-left">Dimension</th><th>Audit A</th><th>Audit B</th><th>Change</th></tr>
      </thead>
      <tbody>
        {a.map((dim) => {
          const next = b.find((item) => item.dimension === dim.dimension);
          const change = (next?.score ?? dim.score) - dim.score;
          return (
            <tr key={dim.dimension} className="border-t border-border">
              <td className="py-3">{dim.label}</td>
              <td className="text-center font-mono">{dim.score}/100</td>
              <td className="text-center font-mono">{next?.score ?? "-"}/100</td>
              <td className="text-center"><DeltaText value={change} /></td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function Row({ label, value }: { label: string; value: ReactNode }) {
  return <div className="flex justify-between gap-4"><span className="text-muted-foreground">{label}</span><span className="font-mono">{value}</span></div>;
}

function DeltaBadge({ value }: { value: number | null }) {
  const className = value == null || value === 0 ? "pill-muted" : value > 0 ? "pill-success" : "pill-danger";
  const arrow = value == null || value === 0 ? "->" : value > 0 ? "up" : "down";
  return <span className={`pill ${className}`}>{value == null ? "-" : `${value > 0 ? "+" : ""}${value}`} {arrow}</span>;
}

function DeltaText({ value }: { value: number | null }) {
  const className = value == null || value === 0 ? "text-muted-foreground" : value > 0 ? "text-success" : "text-danger";
  return <span className={className}>{value == null ? "-" : `${value > 0 ? "+" : ""}${value}`} pts</span>;
}

function StatusBadge({ status }: { status: string }) {
  if (status === "running") return <span className="pill pill-primary inline-flex items-center gap-1"><Loader2 className="h-3 w-3 animate-spin-soft" /> RUNNING</span>;
  if (status === "failed") return <span className="pill pill-danger">FAILED</span>;
  return <span className="pill pill-success">COMPLETE</span>;
}

function SkeletonChart() {
  return <div className="h-full animate-pulse rounded-lg border border-border bg-background/70" />;
}

function SkeletonRows() {
  return <div className="space-y-2">{Array.from({ length: 5 }).map((_, index) => <div key={index} className="h-14 animate-pulse rounded-lg bg-background/70" />)}</div>;
}

function EmptyState() {
  return (
    <div className="rounded-lg border border-border bg-background/70 p-8 text-center">
      <div className="font-display text-lg font-semibold">No audits yet</div>
      <p className="mt-2 text-sm text-muted-foreground">Run your first audit to start tracking your AI readiness score.</p>
      <Link to="/" className="btn-primary mt-4 inline-flex items-center gap-1.5">Run Audit <ArrowRight className="h-4 w-4" /></Link>
    </div>
  );
}

function ErrorBox({ message }: { message: string }) {
  return <div className="rounded-lg border border-danger/30 bg-danger/10 p-4 text-sm text-danger">{message}</div>;
}

function matchesFilter(audit: AuditSummary, filter: Filter) {
  if (filter === "improved") return (audit.score_delta ?? 0) > 0;
  if (filter === "declined") return (audit.score_delta ?? 0) < 0;
  if (filter === "critical") return (audit.before_score ?? 100) < 40;
  return true;
}

function getXAxisLabel(dateStr: string | null, mode: XAxisMode, allDates: string[]) {
  if (!dateStr) return "-";
  const date = new Date(dateStr);
  if (mode === "time") {
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }
  if (mode === "date") {
    return date.toLocaleDateString([], { month: "short", day: "numeric" });
  }
  const first = new Date(allDates[0] || dateStr);
  const last = new Date(allDates[allDates.length - 1] || dateStr);
  const diffDays = (last.getTime() - first.getTime()) / (1000 * 60 * 60 * 24);
  if (diffDays < 1) {
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }
  return date.toLocaleDateString([], { month: "short", day: "numeric" });
}

function shortDate(value: string | null) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric" }).format(new Date(value));
}

function friendlyDate(value: string | null) {
  if (!value) return "-";
  const date = new Date(value);
  const today = new Date();
  const yesterday = new Date();
  yesterday.setDate(today.getDate() - 1);
  const time = new Intl.DateTimeFormat("en", { hour: "numeric", minute: "2-digit" }).format(date);
  if (date.toDateString() === today.toDateString()) return `Today at ${time}`;
  if (date.toDateString() === yesterday.toDateString()) return `Yesterday at ${time}`;
  return `${shortDate(value)} at ${time}`;
}

function friendlyDateTime(value: string | null) {
  return friendlyDate(value);
}

function signed(value: number | null) {
  if (value == null) return "-";
  return value > 0 ? `+${value}` : String(value);
}
