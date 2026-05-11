import { createFileRoute, Link } from "@tanstack/react-router";
import { useState, type FormEvent, type ReactNode } from "react";
import { TopNav } from "@/components/TopNav";
import { ScoreCard } from "@/components/ScoreCard";
import { CountUp } from "@/components/CountUp";
import { analyzeBrandGap, loadAudit, getDimensions, getScores, type BrandGapAnalysis } from "@/lib/audit-api";
import { scoreLabel } from "@/lib/score";
import { ArrowRight, Loader2 } from "lucide-react";

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
  const [brandPositioning, setBrandPositioning] = useState("");
  const [brandAdjectives, setBrandAdjectives] = useState<string[]>([]);
  const [customAdjective, setCustomAdjective] = useState("");
  const [targetCustomer, setTargetCustomer] = useState("");
  const [mustGetRight, setMustGetRight] = useState("");
  const [mustNeverSay, setMustNeverSay] = useState("");
  const [brandGap, setBrandGap] = useState<BrandGapAnalysis | null>(null);
  const [brandGapError, setBrandGapError] = useState<string | null>(null);
  const [brandGapLoading, setBrandGapLoading] = useState(false);
  const scores = getScores(audit);
  const dimensions = getDimensions(audit);
  const score = showAfter ? scores.after : scores.before;
  const failed = showAfter ? scores.failedAfter : scores.failedBefore;
  const status = scoreLabel(score);
  const statusClass = score < 40 ? "pill-danger" : score < 70 ? "pill-warning" : "pill-success";
  const perception = audit?.score.current_perception;
  const canAnalyze = Boolean(audit?.audit_id && brandPositioning.trim() && brandAdjectives.length >= 3 && targetCustomer);

  async function submitBrandGap(event: FormEvent) {
    event.preventDefault();
    if (!audit?.audit_id || !canAnalyze) return;
    setBrandGapLoading(true);
    setBrandGapError(null);
    try {
      const result = await analyzeBrandGap(audit.audit_id, {
        brand_positioning: brandPositioning.trim(),
        brand_adjectives: brandAdjectives,
        target_customer: targetCustomer,
        must_get_right: mustGetRight.trim(),
        must_never_say: mustNeverSay.trim(),
      });
      setBrandGap(result);
    } catch (error) {
      setBrandGapError(error instanceof Error ? error.message : "Brand gap analysis failed");
    } finally {
      setBrandGapLoading(false);
    }
  }

  function toggleAdjective(value: string) {
    setBrandAdjectives((current) =>
      current.includes(value) ? current.filter((item) => item !== value) : [...current, value].slice(0, 8),
    );
  }

  function addCustomAdjective() {
    const value = customAdjective.trim();
    if (!value || brandAdjectives.includes(value)) return;
    setBrandAdjectives((current) => [...current, value].slice(0, 8));
    setCustomAdjective("");
  }

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

        {/* CURRENT PERCEPTION */}
        <section>
          <article
            className="surface-card p-6"
            style={{ background: "var(--gradient-danger)", borderColor: "oklch(0.65 0.24 25 / 0.35)" }}
          >
            <div className="flex flex-wrap items-center justify-between gap-3">
              <span className="label-tiny">How AI agents see your store now</span>
              <span className="pill pill-danger">Before</span>
            </div>
            <blockquote className="mt-5 max-w-4xl text-xl leading-relaxed text-foreground/95">
              "{perception?.perception_summary ||
                "AI agents currently see this as a store with incomplete AI-readable information. Product specs, trust signals, policies, or FAQ coverage may be too thin for confident recommendations."}"
            </blockquote>
            <div className="mt-6 grid gap-3 md:grid-cols-3">
              <PerceptionStat label="Perceived as" value={perception?.perceived_as || "incomplete store profile"} />
              <PerceptionStat label="AI Confidence" value={(perception?.confidence_level || "low").toUpperCase()} tone="danger" />
              <PerceptionStat label="Reason" value={perception?.confidence_reason || "Missing policies, reviews, or detailed product data limit confident answers."} />
            </div>
            {perception?.biggest_perception_problems?.length ? (
              <div className="mt-5 flex flex-wrap gap-2">
                {perception.biggest_perception_problems.slice(0, 3).map((problem) => (
                  <span key={problem} className="pill pill-danger">
                    {problem}
                  </span>
                ))}
              </div>
            ) : null}
          </article>
        </section>

        {/* BRAND GAP INPUT */}
        <section className="surface-card p-6">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <div className="label-tiny">Desired Brand Representation</div>
              <h2 className="mt-1 font-display text-xl font-semibold">
                How do you want AI agents to represent your store?
              </h2>
            </div>
            {brandGap ? <span className="pill pill-primary">Gap Score {brandGap.gap_score}/10</span> : null}
          </div>

          <form onSubmit={submitBrandGap} className="mt-6 grid gap-5 lg:grid-cols-[1fr_420px]">
            <div className="space-y-5">
              <Field label="How would you describe your store in one sentence?" required>
                <textarea
                  value={brandPositioning}
                  onChange={(event) => setBrandPositioning(event.target.value.slice(0, 200))}
                  maxLength={200}
                  rows={3}
                  placeholder="e.g. A premium electronics store known for expert product curation and reliable after-sales support"
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none transition-colors placeholder:text-muted-foreground/60 focus:border-primary"
                />
                <Counter value={brandPositioning.length} max={200} />
              </Field>

              <Field label="Pick 3-5 words that describe your brand" required>
                <div className="flex flex-wrap gap-2">
                  {BRAND_ADJECTIVES.map((item) => {
                    const active = brandAdjectives.includes(item);
                    return (
                      <button
                        key={item}
                        type="button"
                        onClick={() => toggleAdjective(item)}
                        className={`pill transition-colors ${active ? "pill-primary" : "pill-muted hover:border-primary/50 hover:text-foreground"}`}
                      >
                        {item}
                      </button>
                    );
                  })}
                </div>
                <div className="mt-3 flex gap-2">
                  <input
                    value={customAdjective}
                    onChange={(event) => setCustomAdjective(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter") {
                        event.preventDefault();
                        addCustomAdjective();
                      }
                    }}
                    placeholder="Add custom word"
                    className="min-w-0 flex-1 rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none placeholder:text-muted-foreground/60 focus:border-primary"
                  />
                  <button type="button" onClick={addCustomAdjective} className="btn-ghost">
                    Add
                  </button>
                </div>
                <div className="mt-2 text-xs text-muted-foreground">{brandAdjectives.length} selected, minimum 3</div>
              </Field>

              <Field label="Who is your primary customer?" required>
                <select
                  value={targetCustomer}
                  onChange={(event) => setTargetCustomer(event.target.value)}
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-primary"
                >
                  <option value="">Select a customer segment</option>
                  {TARGET_CUSTOMERS.map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                </select>
              </Field>

              <Field label="What's the most important thing an AI agent should know about your store?">
                <textarea
                  value={mustGetRight}
                  onChange={(event) => setMustGetRight(event.target.value.slice(0, 300))}
                  maxLength={300}
                  rows={3}
                  placeholder="e.g. We offer a 30-day no-questions return policy and free shipping on all orders"
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none transition-colors placeholder:text-muted-foreground/60 focus:border-primary"
                />
                <Counter value={mustGetRight.length} max={300} />
              </Field>

              <Field label="What perception would be most damaging?">
                <textarea
                  value={mustNeverSay}
                  onChange={(event) => setMustNeverSay(event.target.value.slice(0, 200))}
                  maxLength={200}
                  rows={3}
                  placeholder="e.g. That we don't have clear return policies or that product quality is uncertain"
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none transition-colors placeholder:text-muted-foreground/60 focus:border-primary"
                />
                <Counter value={mustNeverSay.length} max={200} />
              </Field>

              <button
                type="submit"
                disabled={!canAnalyze || brandGapLoading}
                className="btn-primary inline-flex items-center gap-2 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {brandGapLoading ? <Loader2 className="h-4 w-4 animate-spin-soft" /> : null}
                Analyze Brand Gap -&gt;
              </button>
              {brandGapError ? <div className="text-sm text-danger">{brandGapError}</div> : null}
            </div>

            <BrandGapResult result={brandGap} />
          </form>
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

const BRAND_ADJECTIVES = [
  "Premium",
  "Budget-friendly",
  "Reliable",
  "Fast shipping",
  "Expert",
  "Trustworthy",
  "Eco-friendly",
  "Innovative",
  "Family-friendly",
  "Professional",
  "Enthusiast-grade",
  "Luxury",
  "Value-for-money",
  "Specialist",
  "Community-driven",
];

const TARGET_CUSTOMERS = [
  "Tech enthusiasts",
  "Casual consumers",
  "Gift buyers",
  "Professional users",
  "Budget shoppers",
  "Small businesses",
  "Students",
  "Gamers",
  "Content creators",
  "Home users",
];

function Field({ label, required, children }: { label: string; required?: boolean; children: ReactNode }) {
  return (
    <label className="block">
      <span className="text-sm font-medium text-foreground">
        {label} {required ? <span className="text-danger">*</span> : null}
      </span>
      <div className="mt-2">{children}</div>
    </label>
  );
}

function Counter({ value, max }: { value: number; max: number }) {
  return <div className="mt-1 text-right font-mono text-[11px] text-muted-foreground">{value}/{max}</div>;
}

function PerceptionStat({ label, value, tone }: { label: string; value: string; tone?: "danger" }) {
  return (
    <div className="rounded-lg border border-border bg-background/70 p-4">
      <div className="label-tiny">{label}</div>
      <div className={`mt-2 text-sm font-semibold leading-snug ${tone === "danger" ? "text-danger" : "text-foreground"}`}>
        {value}
      </div>
    </div>
  );
}

function BrandGapResult({ result }: { result: BrandGapAnalysis | null }) {
  if (!result) {
    return (
      <aside className="rounded-lg border border-border bg-background p-5">
        <div className="label-tiny">Gap Analysis</div>
        <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
          Fill in your desired brand representation to compare it against how AI agents currently perceive the store.
        </p>
      </aside>
    );
  }
  const gapWidth = `${Math.min(100, Math.max(0, result.gap_score * 10))}%`;
  const badge = gapBadge(result.gap_score);
  const priorityPoints = { high: 18, medium: 11, low: 6 };

  return (
    <aside className="animate-enter rounded-lg border border-danger/30 bg-danger/10 p-5 shadow-[0_0_36px_oklch(0.63_0.25_25_/_0.14)]">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="label-tiny">Brand Perception Gap</div>
          <div className="mt-1 flex items-baseline gap-3">
            <span className="font-mono text-4xl font-semibold">{result.gap_score}/10</span>
            <span className={`pill ${badge.className}`}>
              {badge.label}
            </span>
          </div>
        </div>
      </div>
      <div className="mt-4 h-2 overflow-hidden rounded-full bg-background">
        <div className="h-full rounded-full transition-all duration-700" style={{ width: gapWidth, background: badge.color }} />
      </div>
      <p className="mt-4 text-sm leading-relaxed text-foreground/90">"{result.gap_summary}"</p>

      <div className="mt-5 space-y-4">
        <MiniSection title="You Want vs. AI Perceives">
          {result.misaligned_areas.slice(0, 3).map((item) => (
            <div key={`${item.desired}-${item.current}`} className="rounded-md border border-border bg-background/75 p-3">
              <div className="grid gap-3 text-sm sm:grid-cols-2">
                <div>
                  <div className="label-tiny">You want</div>
                  <div className="mt-1 font-semibold text-foreground">{item.desired}</div>
                </div>
                <div>
                  <div className="label-tiny">AI perceives</div>
                  <div className="mt-1 font-semibold text-danger">{item.current}</div>
                </div>
              </div>
              <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
                <span>Caused by: {item.caused_by}</span>
                <span className={`pill ${item.fix_priority === "high" ? "pill-danger" : item.fix_priority === "medium" ? "pill-warning" : "pill-muted"}`}>
                  {item.fix_priority} +{priorityPoints[item.fix_priority]} pts
                </span>
              </div>
            </div>
          ))}
        </MiniSection>

        <MiniSection title="Must-Never-Say Risk">
          <div className={`rounded-md border p-3 ${result.must_never_say_risk.at_risk ? "border-danger/40 bg-danger/10" : "border-success/30 bg-success/10"}`}>
            <div className={result.must_never_say_risk.at_risk ? "font-semibold text-danger" : "font-semibold text-success"}>
              {result.must_never_say_risk.at_risk ? "ACTIVE" : "LOWER RISK"}
            </div>
            <p className="mt-2 text-sm text-muted-foreground">{result.must_never_say_risk.reason}</p>
          </div>
        </MiniSection>

        <MiniSection title="Top Blockers">
          {result.perception_blockers.slice(0, 3).map((item) => (
            <div key={item.blocker} className="text-sm text-muted-foreground">
              <div className="text-foreground">{item.blocker}</div>
              <div className="mt-1">Needed: {item.data_needed}</div>
              <div className="mt-1 font-mono text-xs">Potential gap reduction: -{item.estimated_gap_reduction}</div>
            </div>
          ))}
        </MiniSection>

        <MiniSection title="If All Fixed">
          <div className="rounded-md border border-success/30 bg-success/10 p-3">
            <div className="font-mono text-sm text-foreground">
              Gap Score: {result.gap_score}/10 -&gt; {result.if_all_fixed.projected_gap_score}/10
            </div>
            <p className="mt-2 text-sm text-muted-foreground">"{result.if_all_fixed.projected_perception}"</p>
          </div>
        </MiniSection>
      </div>
    </aside>
  );
}

function MiniSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div>
      <div className="label-tiny">{title}</div>
      <div className="mt-2 space-y-2">{children}</div>
    </div>
  );
}

function gapBadge(score: number) {
  if (score <= 3) {
    return { label: "LOW MISMATCH", className: "pill-success", color: "var(--success)" };
  }
  if (score <= 6) {
    return { label: "MODERATE MISMATCH", className: "pill-warning", color: "var(--warning)" };
  }
  if (score <= 8) {
    return { label: "HIGH MISMATCH", className: "pill-high", color: "oklch(0.72 0.2 45)" };
  }
  return { label: "CRITICAL MISMATCH", className: "pill-danger", color: "var(--danger)" };
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
