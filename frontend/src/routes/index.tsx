import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { TopNav } from "@/components/TopNav";
import { ArrowRight, Terminal } from "lucide-react";
import { fetchAuditsByStore, type AuditSummary } from "@/lib/audit-api";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "APES - Your store is invisible to AI agents" },
      { name: "description", content: "APES simulates how AI shopping agents perceive your Shopify store - and shows you exactly what to fix." },
      { property: "og:title", content: "APES - Agent Perception Evaluation System" },
      { property: "og:description", content: "Simulate how AI shopping agents see your Shopify store. Find every data gap. Ship the fixes." },
    ],
  }),
  component: Landing,
});

const PLACEHOLDERS = [
  "your-store.myshopify.com",
  "hackathon-store.myshopify.com",
  "electronics-shop.myshopify.com",
  "gadget-world.myshopify.com",
];

function Landing() {
  const navigate = useNavigate();
  const [url, setUrl] = useState("");
  const [bannerData, setBannerData] = useState<AuditSummary | null>(null);
  const [placeholderIndex, setPlaceholderIndex] = useState(0);
  const [placeholderPaused, setPlaceholderPaused] = useState(false);
  const storeUrl = url.trim();

  useEffect(() => {
    if (placeholderPaused) return;
    const timer = window.setInterval(() => {
      setPlaceholderIndex((current) => (current + 1) % PLACEHOLDERS.length);
    }, 3000);
    return () => window.clearInterval(timer);
  }, [placeholderPaused]);

  useEffect(() => {
    if (!storeUrl || storeUrl.length < 5) {
      setBannerData(null);
      return;
    }
    let mounted = true;
    const timer = window.setTimeout(async () => {
      try {
        const audits = await fetchAuditsByStore(storeUrl);
        if (mounted) setBannerData(audits[0] ?? null);
      } catch {
        if (mounted) setBannerData(null);
      }
    }, 800);
    return () => {
      mounted = false;
      window.clearTimeout(timer);
    };
  }, [storeUrl]);

  function submitAudit() {
    navigate({
      to: "/audit",
      search: { store: url || "hackathon-store-h8ivgk49.myshopify.com", demo: false } as any,
    });
  }

  return (
    <div className="min-h-screen">
      <TopNav />

      <main className="relative">
        <div className="absolute inset-0 grid-bg opacity-60" aria-hidden />
        <div
          className="pointer-events-none absolute inset-x-0 top-0 -z-0 h-[700px]"
          style={{ background: "var(--gradient-hero)" }}
          aria-hidden
        />

        <section className="relative mx-auto flex min-h-[88vh] max-w-5xl flex-col items-center justify-center px-6 pb-20 pt-24 text-center">
          <span className="pill pill-primary animate-fade-up">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-primary" /> Agent Perception Evaluation System
          </span>

          <h1
            className="mt-6 max-w-4xl animate-fade-up font-display text-5xl font-bold leading-[1.05] tracking-tight sm:text-7xl"
            style={{ animationDelay: "60ms" }}
          >
            Your store is{" "}
            <span className="bg-gradient-to-r from-foreground to-muted-foreground bg-clip-text text-transparent">
              invisible
            </span>{" "}
            to AI agents.
          </h1>

          <p
            className="mt-5 max-w-2xl animate-fade-up text-base leading-relaxed text-muted-foreground sm:text-lg"
            style={{ animationDelay: "120ms" }}
          >
            APES simulates how AI shopping agents perceive your Shopify store -
            and shows you exactly what to fix.
          </p>

          <form
            onSubmit={(event) => {
              event.preventDefault();
              submitAudit();
            }}
            className="mt-10 w-full max-w-2xl animate-fade-up"
            style={{ animationDelay: "200ms" }}
          >
            <div className="glow-input flex items-center gap-2 rounded-xl border border-border bg-surface p-2">
              <div className="flex items-center gap-2 pl-3 text-muted-foreground">
                <Terminal className="h-4 w-4" />
                <span className="font-mono text-xs">~/audit ▸</span>
              </div>
              <input
                id="audit-input"
                value={url}
                onFocus={() => setPlaceholderPaused(true)}
                onClick={() => setPlaceholderPaused(true)}
                onChange={(event) => setUrl(event.target.value)}
                placeholder={PLACEHOLDERS[placeholderIndex]}
                className="flex-1 bg-transparent px-2 py-2 font-mono text-sm text-foreground outline-none placeholder:text-muted-foreground/60"
              />
              <button type="submit" className="btn-primary inline-flex items-center gap-1.5">
                Run AI Audit <ArrowRight className="h-4 w-4" />
              </button>
            </div>
            <div className="mt-3 text-sm text-muted-foreground">
              or{" "}
              <Link
                to="/audit"
                search={{ store: "hackathon-store.myshopify.com", demo: true } as any}
                className="text-foreground underline-offset-4 hover:underline"
              >
                View Demo Audit →
              </Link>
            </div>

            {bannerData ? <PreviousAuditBanner audit={bannerData} /> : null}
          </form>

          <div
            className="mt-12 animate-fade-up font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground"
            style={{ animationDelay: "260ms" }}
          >
            USED IN KASPARRO AI COMMERCE HACKATHON 2026
          </div>
        </section>

        <section id="how" className="relative mx-auto max-w-5xl px-6 pb-16">
          <div className="grid gap-4 sm:grid-cols-2">
            {FEATURES.map((feature, index) => (
              <article
                key={feature.title}
                className="animate-fade-up rounded-lg border border-border bg-[#111118] p-6 transition-all duration-200 hover:-translate-y-1 hover:border-primary/50"
                style={{ animationDelay: `${320 + index * 60}ms` }}
              >
                <div className="text-3xl" aria-hidden>{feature.icon}</div>
                <span className="pill pill-primary mt-4 inline-flex">{feature.stat}</span>
                <h3 className="mt-3 font-display text-lg font-semibold">{feature.title}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{feature.description}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="relative mx-auto max-w-5xl px-6 pb-24">
          <div className="text-center">
            <h2 className="font-display text-3xl font-semibold">How APES Works</h2>
            <p className="mt-2 text-sm text-muted-foreground">From store URL to action plan in under 60 seconds</p>
          </div>
          <div className="mt-8 grid gap-4 md:grid-cols-[1fr_auto_1fr_auto_1fr] md:items-stretch">
            <FlowStep icon="🔍" title="Crawl" body="We pull all your store data via Shopify API." />
            <FlowArrow />
            <FlowStep icon="🤖" title="Simulate" body="20 AI agent queries run against your store data." />
            <FlowArrow />
            <FlowStep icon="📊" title="Fix" body="Every failure gets a fix. Score improves. Proof shown." />
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}

function PreviousAuditBanner({ audit }: { audit: AuditSummary }) {
  return (
    <div className="mt-5 animate-fade-up rounded-xl border border-border border-l-4 border-l-primary bg-[#111118] p-5 text-left shadow-[0_16px_48px_oklch(0_0_0_/_0.25)]">
      <div className="flex items-start gap-3">
        <div className="text-2xl" aria-hidden>📊</div>
        <div className="flex-1">
          <div className="font-display font-semibold">Previous audit found for this store</div>
          <div className="mt-4 grid gap-1 text-sm text-muted-foreground sm:grid-cols-2">
            <div>
              Last score: <span className="font-mono text-foreground">{audit.before_score ?? "-"}/100</span> · {scoreLabel(audit.before_score)}
            </div>
            <div>Audited: {formatAuditDateTime(audit.created_at)}</div>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Link to="/audit/$auditId" params={{ auditId: audit.audit_id }} className="btn-ghost inline-flex items-center gap-1.5 text-sm">
              View Last Audit <ArrowRight className="h-4 w-4" />
            </Link>
            <button type="submit" className="btn-primary inline-flex items-center gap-1.5 text-sm">
              Run New Audit <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

const FEATURES = [
  {
    icon: "🤖",
    title: "Agent Simulation",
    stat: "20 queries",
    description: "5 customer personas ask real buying questions against your store data",
  },
  {
    icon: "🔬",
    title: "Failure Forensics",
    stat: "4 failure types",
    description: "HALLUCINATED · VAGUE · REFUSED · CONFIDENT - every failure traced to an exact data gap",
  },
  {
    icon: "🛠",
    title: "Fix Generator",
    stat: "AI-drafted",
    description: "Claude rewrites broken content. Missing facts flagged as Merchant Input Needed.",
  },
  {
    icon: "📈",
    title: "Before vs After",
    stat: "Re-simulated",
    description: "Apply fixes, re-run the same queries, watch your score change live",
  },
];

function FlowStep({ icon, title, body }: { icon: string; title: string; body: string }) {
  return (
    <article className="rounded-lg border border-border bg-[#111118] p-6 text-center">
      <div className="text-3xl" aria-hidden>{icon}</div>
      <div className="mt-3 border-y border-border py-3 font-display text-xl font-semibold">{title}</div>
      <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{body}</p>
    </article>
  );
}

function FlowArrow() {
  return (
    <div className="grid place-items-center text-primary">
      <span className="hidden text-2xl md:inline">→</span>
      <span className="text-2xl md:hidden">↓</span>
    </div>
  );
}

function Footer() {
  return (
    <footer className="border-t border-border bg-background/80 px-6 py-8">
      <div className="mx-auto flex max-w-5xl flex-col gap-4 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="font-display font-semibold text-foreground">APES - Agent Perception Evaluation System</div>
          <div className="mt-1">Built for Kasparro AI Commerce Hackathon 2026</div>
          <div className="mt-2">© 2026 APES</div>
        </div>
        <div className="flex gap-4">
          <a href="#" className="hover:text-foreground">GitHub</a>
          <Link to="/audit" search={{ store: "hackathon-store.myshopify.com", demo: true } as any} className="hover:text-foreground">
            View Demo
          </Link>
        </div>
      </div>
    </footer>
  );
}

function scoreLabel(score: number | null) {
  if (score == null) return "Unknown";
  if (score < 40) return "Critical";
  if (score < 70) return "Needs work";
  return "Ready";
}

function formatAuditDateTime(value: string | null) {
  if (!value) return "recently";
  const date = new Date(value);
  const today = new Date();
  const yesterday = new Date();
  const time = date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  if (date.toDateString() === today.toDateString()) return `Today at ${time}`;
  if (date.toDateString() === yesterday.toDateString()) return `Yesterday at ${time}`;
  return date.toLocaleString([], { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}
