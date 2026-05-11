import { createFileRoute, Link } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { TopNav } from "@/components/TopNav";
import { CountUp } from "@/components/CountUp";
import { ACTION_PLAN, SCORE_BEFORE, SCORE_POTENTIAL } from "@/lib/mock-data";
import { Check, ArrowRight } from "lucide-react";

export const Route = createFileRoute("/plan")({
  head: () => ({
    meta: [
      { title: "APES — Ranked Action Plan" },
      { name: "description", content: "The exact sequence of fixes to maximize your AI Readiness Score, with cumulative impact." },
    ],
  }),
  component: Plan,
});

function Plan() {
  const [done, setDone] = useState<Record<number, boolean>>({});
  const totalDelta = ACTION_PLAN.reduce((s, a) => s + a.delta, 0);
  const appliedDelta = useMemo(
    () => ACTION_PLAN.reduce((s, a) => s + (done[a.rank] ? a.delta : 0), 0),
    [done]
  );
  const current = SCORE_BEFORE + appliedDelta;
  const appliedCount = Object.values(done).filter(Boolean).length;

  // Cumulative checkpoints for the progress segments
  const checkpoints = useMemo(() => {
    const arr: number[] = [SCORE_BEFORE];
    let acc = SCORE_BEFORE;
    for (const a of ACTION_PLAN) { acc += a.delta; arr.push(acc); }
    return arr;
  }, []);

  return (
    <div className="min-h-screen">
      <TopNav showActions />
      <main className="mx-auto max-w-5xl px-6 py-8">
        <header className="mb-6">
          <h1 className="font-display text-2xl font-semibold">Your Ranked Action Plan</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Apply these fixes in order for maximum AI representation improvement.
          </p>
        </header>

        {/* Summary */}
        <section className="surface-card p-6">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <div className="label-tiny">Progress</div>
              <div className="mt-1 font-mono text-sm">
                {appliedCount} of {ACTION_PLAN.length} fixes applied · Score:{" "}
                <CountUp to={current} trigger={current} className="text-foreground" />/100 → potential {SCORE_POTENTIAL}/100
              </div>
            </div>
            <div className="text-right">
              <div className="label-tiny">Cumulative Lift</div>
              <div className="mt-1 font-mono text-sm text-success">+{appliedDelta} / +{totalDelta}</div>
            </div>
          </div>

          {/* Segmented progress with checkpoints */}
          <div className="mt-5">
            <div className="flex h-2 overflow-hidden rounded-full bg-secondary">
              {ACTION_PLAN.map((a) => (
                <div
                  key={a.rank}
                  className="h-full border-r border-background last:border-r-0 transition-all duration-700"
                  style={{
                    flex: a.delta,
                    background: done[a.rank] ? "var(--success)" : "transparent",
                  }}
                />
              ))}
            </div>
            <div className="mt-2 grid grid-cols-7 text-center font-mono text-[10px] text-muted-foreground">
              {checkpoints.map((c, i) => (
                <div key={i} className={`${done[ACTION_PLAN[i-1]?.rank] || i === 0 ? "text-foreground" : ""}`}>
                  {c}
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Action items */}
        <section className="mt-6 grid gap-4">
          {ACTION_PLAN.map((a, i) => {
            const isDone = !!done[a.rank];
            return (
              <article
                key={a.rank}
                className="surface-card animate-fade-up p-6"
                style={{ animationDelay: `${i * 50}ms` }}
              >
                <div className="flex items-start gap-5">
                  <button
                    onClick={() => setDone(d => ({ ...d, [a.rank]: !d[a.rank] }))}
                    className={`mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-full border transition-all ${
                      isDone
                        ? "border-success bg-success/15 text-success"
                        : "border-border bg-background hover:border-foreground"
                    }`}
                    aria-label={isDone ? "Mark as not done" : "Mark as done"}
                  >
                    {isDone ? <Check className="h-4 w-4" strokeWidth={3} /> : <span className="font-mono text-sm">#{a.rank}</span>}
                  </button>

                  <div className="flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="pill pill-primary">{a.priority}</span>
                      <span className="pill pill-muted">{a.impact}</span>
                      <span className="pill pill-muted">Effort: {a.effort}</span>
                      <span className="ml-auto font-mono text-xs text-success">+{a.delta} pts</span>
                    </div>

                    <h3 className={`mt-3 font-display text-lg font-semibold ${isDone ? "text-muted-foreground line-through" : ""}`}>
                      {a.title}
                    </h3>
                    <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
                      <span className="text-foreground">Why:</span> {a.why}
                    </p>
                    <div className="mt-2 text-xs text-muted-foreground">Affects: {a.affects}</div>

                    <div className="mt-4">
                      <Link to="/fixes" search={{ id: a.fixIds[0] } as any} className="btn-ghost inline-flex items-center gap-1.5 text-sm">
                        Apply Fix <ArrowRight className="h-4 w-4" />
                      </Link>
                    </div>
                  </div>
                </div>
              </article>
            );
          })}
        </section>
      </main>
    </div>
  );
}
