import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { TopNav } from "@/components/TopNav";
import { ScoreCard } from "@/components/ScoreCard";
import { CountUp } from "@/components/CountUp";
import { loadAudit, getDimensions, getScores } from "@/lib/audit-api";
import { scoreLabel } from "@/lib/score";
import { ArrowRight } from "lucide-react";

export const Route = createFileRoute("/dashboard")({
  head: () => ({
    meta: [
      { title: "APES — Dashboard" },
      { name: "description", content: "AI Readiness Score, dimension breakdown, and agent perception summary for your store." },
    ],
  }),
  component: Dashboard,
});

function Dashboard() {
  const [showAfter, setShowAfter] = useState(false);
  const [audit] = useState(() => loadAudit());
  const scores = getScores(audit);
  const dimensions = getDimensions(audit);
  const score = showAfter ? scores.after : scores.before;
  const failed = showAfter ? scores.failedAfter : scores.failedBefore;
  const status = scoreLabel(score);
  const statusClass = score < 40 ? "pill-danger" : score < 70 ? "pill-warning" : "pill-success";

  return (
    <div className="min-h-screen">
      <TopNav showActions />

      <main className="mx-auto max-w-7xl space-y-6 px-6 py-8">
        {/* HERO SCORE */}
        <section
          className="surface-card relative overflow-hidden p-8 sm:p-10"
          style={{ background: "linear-gradient(135deg, var(--surface), oklch(0.18 0.04 280))" }}
        >
          <div className="pointer-events-none absolute inset-0 opacity-50 grid-bg" aria-hidden />

          <div className="relative grid gap-10 md:grid-cols-2 md:items-center">
            <div>
              <div className="label-tiny">AI Readiness Score</div>
              <div className="mt-3 flex items-baseline gap-3">
                <CountUp
                  to={score}
                  trigger={showAfter ? "after" : "before"}
                  className="font-mono text-7xl font-semibold leading-none tracking-tight sm:text-8xl"
                />
                <span className="font-mono text-2xl text-muted-foreground">/100</span>
              </div>
              <div className="mt-4 flex items-center gap-3">
                <span className={`pill ${statusClass} ${score < 40 ? "animate-pulse-danger" : ""}`}>{status}</span>
                <span className="text-sm text-muted-foreground">{failed} of {scores.total} agent queries failed</span>
              </div>
            </div>

            <div className="flex flex-col items-start gap-6 md:items-end">
              <div className="inline-flex rounded-lg border border-border bg-background p-1 text-sm">
                <button
                  onClick={() => setShowAfter(false)}
                  className={`rounded-md px-3 py-1.5 transition-colors ${!showAfter ? "bg-surface text-foreground shadow" : "text-muted-foreground"}`}
                >
                  Before Fixes
                </button>
                <button
                  onClick={() => setShowAfter(true)}
                  className={`rounded-md px-3 py-1.5 transition-colors ${showAfter ? "bg-surface text-foreground shadow" : "text-muted-foreground"}`}
                >
                  After Fixes
                </button>
              </div>

              <ScoreRing score={score} />
            </div>
          </div>
        </section>

        {/* DIMENSIONS */}
        <section>
          <div className="mb-3 flex items-end justify-between">
            <h2 className="font-display text-xl font-semibold">Dimension Scores</h2>
            <span className="label-tiny">Showing: {showAfter ? "After Fixes" : "Before Fixes"}</span>
          </div>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {dimensions.map((d, i) => (
              <ScoreCard
                key={d.key}
                title={d.name}
                score={showAfter ? d.after : d.before}
                delta={d.delta}
                explanation={d.explanation}
                trigger={showAfter ? "a" : "b"}
                delay={i * 60}
              />
            ))}
          </div>
        </section>

        {/* PERCEPTION */}
        <section className="grid gap-4 md:grid-cols-2">
          <article
            className="surface-card p-6"
            style={{ background: "var(--gradient-danger)", borderColor: "oklch(0.65 0.24 25 / 0.3)" }}
          >
            <div className="flex items-center justify-between">
              <span className="label-tiny">How AI agents see your store NOW</span>
              <span className="pill pill-danger">Before</span>
            </div>
            <p className="mt-4 leading-relaxed text-foreground/90">
              A budget electronics store with limited information. Product specs are vague.
              No return or shipping policies exist. No customer reviews. AI agents cannot
              answer basic shopper questions with confidence and will likely skip
              recommending this store.
            </p>
          </article>

          <article
            className="surface-card p-6"
            style={{ background: "var(--gradient-success)", borderColor: "oklch(0.72 0.17 162 / 0.3)" }}
          >
            <div className="flex items-center justify-between">
              <span className="label-tiny">How AI agents SHOULD represent you</span>
              <span className="pill pill-success">After</span>
            </div>
            <p className="mt-4 leading-relaxed text-foreground/90">
              A reliable electronics retailer with clear product specifications, transparent
              shipping and return policies, verified customer reviews, and comprehensive FAQ
              coverage — allowing AI agents to recommend products confidently.
            </p>
          </article>
        </section>

        {/* QUICK NAV */}
        <section className="grid gap-4 md:grid-cols-3">
          <QuickNav to="/failures" title="Agent Failure Replay" desc="See exactly where 13 conversations broke." />
          <QuickNav to="/fixes"    title="Before / After Fixes"  desc="Review every Claude-drafted improvement." />
          <QuickNav to="/plan"     title="Ranked Action Plan"    desc="Apply fixes in order. Track score lift." />
        </section>
      </main>
    </div>
  );
}

function QuickNav({ to, title, desc }: { to: string; title: string; desc: string }) {
  return (
    <Link to={to} className="surface-card group flex items-center justify-between p-5">
      <div>
        <div className="font-display font-semibold">{title}</div>
        <div className="mt-1 text-sm text-muted-foreground">{desc}</div>
      </div>
      <ArrowRight className="h-5 w-5 text-muted-foreground transition-transform group-hover:translate-x-1 group-hover:text-foreground" />
    </Link>
  );
}

function ScoreRing({ score }: { score: number }) {
  const r = 70;
  const c = 2 * Math.PI * r;
  const offset = c - (score / 100) * c;
  const stroke = score < 40 ? "var(--danger)" : score < 70 ? "var(--warning)" : "var(--success)";
  return (
    <svg width="180" height="180" viewBox="0 0 180 180" className="drop-shadow-[0_0_24px_var(--primary)]">
      <circle cx="90" cy="90" r={r} stroke="var(--border)" strokeWidth="10" fill="none" />
      <circle
        cx="90" cy="90" r={r} fill="none" stroke={stroke} strokeWidth="10"
        strokeLinecap="round" strokeDasharray={c} strokeDashoffset={offset}
        transform="rotate(-90 90 90)"
        style={{ transition: "stroke-dashoffset 1.2s cubic-bezier(.2,.7,.2,1), stroke .4s" }}
      />
      <text x="90" y="95" textAnchor="middle" className="fill-foreground font-mono" fontSize="34" fontWeight="600">
        {score}
      </text>
      <text x="90" y="118" textAnchor="middle" className="fill-muted-foreground font-mono" fontSize="11">/ 100</text>
    </svg>
  );
}
