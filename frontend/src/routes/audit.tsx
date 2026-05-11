import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { TopNav } from "@/components/TopNav";
import { CountUp } from "@/components/CountUp";
import { Check, Loader2, ArrowRight, RotateCcw, TriangleAlert } from "lucide-react";
import { STORE_URL, SCORE_BEFORE } from "@/lib/mock-data";
import { runAuditStream, saveAudit, type AuditProgressEvent, type AuditResult } from "@/lib/audit-api";

export const Route = createFileRoute("/audit")({
  validateSearch: (search: Record<string, unknown>) => ({
    store: typeof search.store === "string" ? search.store : "hackathon-store-h8ivgk49.myshopify.com",
    demo: search.demo === true || search.demo === "true",
  }),
  head: () => ({
    meta: [
      { title: "APES - Live Audit" },
      { name: "description", content: "Watching APES simulate AI shopping agents against your store in real time." },
    ],
  }),
  component: AuditPage,
});

interface Step {
  key: string;
  marker: string;
  title: string;
  body: (progress: number) => React.ReactNode;
}

const STEPS: Step[] = [
  { key: "crawl", marker: "01", title: "Crawling store data", body: () => "Waiting for backend crawler..." },
  { key: "personas", marker: "02", title: "Generating customer personas", body: () => "Waiting for persona query generation..." },
  { key: "simulations", marker: "03", title: "Running agent simulations", body: (p) => `Simulating query ${Math.max(1, Math.ceil(p * 20))} of 20` },
  { key: "verification", marker: "04", title: "Analyzing failures", body: () => "Waiting for response classification..." },
  { key: "fixes", marker: "05", title: "Generating fixes", body: () => "Waiting for fix generation and re-simulation..." },
  { key: "scoring", marker: "06", title: "Calculating AI Readiness Score", body: () => "Waiting for score calculation..." },
];

const STAGE_INDEX: Record<string, number> = {
  crawl: 0,
  personas: 1,
  simulations: 2,
  verification: 3,
  forensics: 3,
  fixes: 4,
  resimulation: 4,
  scoring: 5,
};

function AuditPage() {
  const search = Route.useSearch();
  const [active, setActive] = useState(0);
  const [progress, setProgress] = useState(0.05);
  const [done, setDone] = useState(false);
  const [auditDone, setAuditDone] = useState(false);
  const [auditError, setAuditError] = useState<string | null>(null);
  const [auditResult, setAuditResult] = useState<AuditResult | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [stepMessages, setStepMessages] = useState<Record<string, string>>({});
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let mounted = true;
    setActive(0);
    setProgress(0.05);
    setDone(false);
    setAuditDone(false);
    setAuditError(null);
    setAuditResult(null);
    setLogs([]);
    setStepMessages({});

    const handleEvent = (event: AuditProgressEvent) => {
      if (!mounted || event.type !== "progress" || !event.stage) return;
      const index = STAGE_INDEX[event.stage] ?? 0;
      const progressValue = event.total ? (event.current ?? 0) / event.total : event.status === "complete" ? 1 : 0.35;
      setActive(event.status === "complete" ? Math.min(index + 1, STEPS.length) : index);
      setProgress(Math.max(0.05, Math.min(1, progressValue)));
      if (event.message) {
        setStepMessages((prev) => ({ ...prev, [STEPS[index].key]: event.message ?? "" }));
        setLogs((prev) => [...prev, event.message ?? ""]);
      }
    };

    runAuditStream(search.store, search.demo, handleEvent)
      .then((result) => {
        if (!mounted) return;
        saveAudit(result);
        setAuditResult(result);
        setActive(STEPS.length);
        setProgress(1);
        setAuditDone(true);
      })
      .catch((error) => {
        if (!mounted) return;
        setActive(STEPS.length);
        setAuditError(error instanceof Error ? error.message : "Audit failed");
      });

    return () => {
      mounted = false;
    };
  }, [search.store, search.demo]);

  useEffect(() => {
    if (active >= STEPS.length && (auditDone || auditError)) setDone(true);
  }, [active, auditDone, auditError]);

  useEffect(() => {
    requestAnimationFrame(() => {
      if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
    });
  }, [logs]);

  return (
    <div className="min-h-screen">
      <TopNav />
      <main className="mx-auto max-w-6xl px-6 py-10">
        <div className="flex items-center justify-between">
          <div>
            <div className="label-tiny">Auditing</div>
            <div className="mt-1 font-mono text-sm text-foreground">{search.demo ? STORE_URL : search.store}</div>
          </div>
          <div className="flex items-center gap-3">
            <span className={`pill ${search.demo ? "pill-warning" : "pill-primary"}`}>
              {search.demo ? "DEMO ENDPOINT" : "LIVE BACKEND"}
            </span>
            <div className="hidden font-mono text-xs text-muted-foreground sm:block">
              {done ? (auditError ? "failed" : "complete") : `step ${Math.min(active + 1, STEPS.length)} / ${STEPS.length}`}
            </div>
          </div>
        </div>

        <div className="mt-10 grid gap-6 lg:grid-cols-[1fr_360px]">
          <ol className="surface-card relative p-8">
            <div className="absolute left-[2.1rem] top-10 bottom-10 w-px bg-border" aria-hidden />
            {STEPS.map((step, index) => {
              const state = index < active ? "done" : index === active ? "active" : "pending";
              return (
                <li key={step.title} className="relative flex gap-4 py-4">
                  <div className="relative z-10">
                    {state === "done" && (
                      <div className="grid h-7 w-7 place-items-center rounded-full bg-primary text-primary-foreground">
                        <Check className="h-4 w-4" strokeWidth={3} />
                      </div>
                    )}
                    {state === "active" && (
                      <div className="grid h-7 w-7 place-items-center rounded-full border border-foreground bg-background">
                        <Loader2 className="h-3.5 w-3.5 animate-spin-soft text-foreground" />
                      </div>
                    )}
                    {state === "pending" && (
                      <div className="grid h-7 w-7 place-items-center rounded-full border border-border bg-background font-mono text-[10px] text-muted-foreground">
                        {step.marker}
                      </div>
                    )}
                  </div>
                  <div className="flex-1 pt-0.5">
                    <div className={`flex items-center gap-2 font-display font-semibold ${state === "active" ? "text-foreground" : state === "done" ? "text-primary" : "text-muted-foreground"}`}>
                      <span>{step.title}</span>
                    </div>
                    <div className="mt-1 font-mono text-xs leading-relaxed text-muted-foreground">
                      {state === "pending" ? "-" : stepMessages[step.key] || step.body(state === "active" ? progress : 1)}
                    </div>
                    {state === "active" && (
                      <div className="mt-2 h-1 w-full overflow-hidden rounded-full bg-secondary">
                        <div className="h-full bg-primary transition-[width] duration-100" style={{ width: `${progress * 100}%` }} />
                      </div>
                    )}
                  </div>
                </li>
              );
            })}

            {active >= STEPS.length && !auditDone && !auditError && (
              <div className="mt-8 rounded-xl border border-primary/30 bg-primary/10 p-6">
                <div className="flex items-center gap-2 font-display font-semibold">
                  <Loader2 className="h-4 w-4 animate-spin-soft" />
                  Waiting for backend audit
                </div>
                <div className="mt-2 text-sm text-muted-foreground">
                  The final report is still being assembled by the backend. This screen will not switch to a report until the real response arrives.
                </div>
              </div>
            )}

            {done && auditError && (
              <div className="mt-8 rounded-xl border border-danger/40 bg-danger/10 p-6">
                <div className="flex items-center gap-2 font-display text-lg font-semibold text-danger">
                  <TriangleAlert className="h-5 w-5" />
                  Live audit did not complete
                </div>
                <div className="mt-2 text-sm text-muted-foreground">
                  Backend audit issue: {auditError}. No fallback report was saved, so you will not accidentally inspect demo data.
                </div>
                <div className="mt-5 flex flex-wrap gap-3">
                  <button type="button" onClick={() => window.location.reload()} className="btn-primary inline-flex items-center gap-1.5">
                    Retry Audit <RotateCcw className="h-4 w-4" />
                  </button>
                  <Link to="/" className="btn-ghost inline-flex items-center gap-1.5">
                    Back to Start
                  </Link>
                </div>
              </div>
            )}

            {done && !auditError && (
              <div className="animate-slam mt-8 rounded-xl border border-danger/30 bg-[var(--gradient-danger)] p-6">
                <div className="label-tiny">AI Readiness Score</div>
                <div className="mt-1 flex items-baseline gap-3">
                  <CountUp to={auditResult?.score.before_score ?? SCORE_BEFORE} duration={1800} className="font-mono text-6xl font-semibold tracking-tight" />
                  <span className="font-mono text-lg text-muted-foreground">/100</span>
                  <span className="pill pill-danger">CRITICAL</span>
                </div>
                <div className="mt-2 text-sm text-muted-foreground">
                  Audit complete from the {search.demo ? "demo" : "live"} backend. Open the report to inspect {auditResult?.failed_queries ?? "the"} failures and fixes.
                </div>
                <Link to="/dashboard" className="btn-primary mt-5 inline-flex items-center gap-1.5">
                  View Full Report <ArrowRight className="h-4 w-4" />
                </Link>
              </div>
            )}
          </ol>

          <aside className="surface-card flex h-[520px] flex-col overflow-hidden p-0">
            <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
              <span className="label-tiny">Live Backend Log</span>
              <span className="flex gap-1">
                <i className="h-2 w-2 rounded-full bg-danger/60" />
                <i className="h-2 w-2 rounded-full bg-warning/60" />
                <i className="h-2 w-2 rounded-full bg-success/60" />
              </span>
            </div>
            <div ref={logRef} className="flex-1 overflow-y-auto px-4 py-3">
              {logs.map((line, index) => (
                <div key={`${line}-${index}`} className="terminal-line whitespace-nowrap">
                  <span className="ts">{ts(index)} </span>
                  <span className="ok">&gt;</span> {line}
                </div>
              ))}
              {!done && <div className="terminal-line"><span className="animate-pulse">|</span></div>}
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}

function ts(index: number) {
  const sec = String(index).padStart(2, "0");
  return `[00:${sec}]`;
}
