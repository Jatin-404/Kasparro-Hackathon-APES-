import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { TopNav } from "@/components/TopNav";
import { ArrowRight, Search, Brain, Wrench, TrendingUp, Terminal } from "lucide-react";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "APES — Your store is invisible to AI agents" },
      { name: "description", content: "APES simulates how AI shopping agents perceive your Shopify store — and shows you exactly what to fix." },
      { property: "og:title", content: "APES — Agent Perception Evaluation System" },
      { property: "og:description", content: "Simulate how AI shopping agents see your Shopify store. Find every data gap. Ship the fixes." },
    ],
  }),
  component: Landing,
});

function Landing() {
  const navigate = useNavigate();
  const [url, setUrl] = useState("");

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
            className="mt-6 max-w-4xl font-display text-5xl font-bold leading-[1.05] tracking-tight sm:text-7xl animate-fade-up"
            style={{ animationDelay: "60ms" }}
          >
            Your store is{" "}
            <span className="bg-gradient-to-r from-foreground to-muted-foreground bg-clip-text text-transparent">
              invisible
            </span>{" "}
            to AI agents.
          </h1>

          <p
            className="mt-5 max-w-2xl text-base leading-relaxed text-muted-foreground sm:text-lg animate-fade-up"
            style={{ animationDelay: "120ms" }}
          >
            APES simulates how AI shopping agents perceive your Shopify store —
            and shows you exactly what to fix.
          </p>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              navigate({
                to: "/audit",
                search: { store: url || "hackathon-store-h8ivgk49.myshopify.com", demo: false } as any,
              });
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
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="your-store.myshopify.com"
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
          </form>

          <div
            className="mt-12 font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground animate-fade-up"
            style={{ animationDelay: "260ms" }}
          >
            Used in Kasparro AI Commerce Hackathon 2026
          </div>
        </section>

        <section id="how" className="relative mx-auto max-w-5xl px-6 pb-32">
          <div className="grid gap-4 sm:grid-cols-2">
            {[
              { i: <Search className="h-5 w-5" />,     t: "Agent Simulation",       d: "We simulate 20 real customer queries against your store data." },
              { i: <Brain className="h-5 w-5" />,      t: "Failure Forensics",      d: "Every AI failure traced to an exact data gap." },
              { i: <Wrench className="h-5 w-5" />,     t: "Guided Fix Suggestions", d: "AI drafts safer content and flags missing facts as Merchant Input Needed." },
              { i: <TrendingUp className="h-5 w-5" />, t: "Proof of Improvement",   d: "Re-simulate after fixes. Watch your score change." },
            ].map((f, idx) => (
              <div
                key={f.t}
                className="surface-card animate-fade-up p-6"
                style={{ animationDelay: `${320 + idx * 60}ms` }}
              >
                <div className="grid h-9 w-9 place-items-center rounded-lg bg-primary/15 text-primary ring-1 ring-primary/30">
                  {f.i}
                </div>
                <h3 className="mt-4 font-display text-lg font-semibold">{f.t}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{f.d}</p>
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
