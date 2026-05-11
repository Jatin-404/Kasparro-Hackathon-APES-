import { createFileRoute, Link } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { TopNav } from "@/components/TopNav";
import { type Classification, type Persona } from "@/lib/mock-data";
import { getFailures, loadAudit } from "@/lib/audit-api";
import { ChevronDown, ChevronUp, ArrowRight } from "lucide-react";

export const Route = createFileRoute("/failures")({
  head: () => ({
    meta: [
      { title: "APES — Agent Failure Replay" },
      { name: "description", content: "Replay every AI agent conversation that failed against your store. Trace each failure to its root cause." },
    ],
  }),
  component: Failures,
});

const CLASS_LABEL: Record<Classification, { label: string; pill: string; emoji: string }> = {
  REFUSED:      { label: "REFUSED",      pill: "pill-danger",  emoji: "🔴" },
  VAGUE:        { label: "VAGUE",        pill: "pill-warning", emoji: "🟡" },
  HALLUCINATED: { label: "HALLUCINATED", pill: "pill-warning", emoji: "⚠️" },
  CONFIDENT:    { label: "CONFIDENT",    pill: "pill-success", emoji: "✅" },
};

const PERSONAS: Persona[] = ["Budget Buyer","Gift Buyer","Researcher","Impulse Buyer","Skeptic"];

function Failures() {
  const [classFilter, setClassFilter] = useState<"ALL" | Classification>("ALL");
  const [personaFilter, setPersonaFilter] = useState<"ALL" | Persona>("ALL");
  const [audit] = useState(() => loadAudit());
  const failures = getFailures(audit);

  const counts = useMemo(() => ({
    REFUSED: failures.filter(f => f.classification === "REFUSED").length,
    VAGUE: failures.filter(f => f.classification === "VAGUE").length,
    HALLUCINATED: failures.filter(f => f.classification === "HALLUCINATED").length,
  }), [failures]);

  const list = failures
    .filter(f => classFilter === "ALL" || f.classification === classFilter)
    .filter(f => personaFilter === "ALL" || f.persona === personaFilter)
    .sort((a, b) => sevWeight(b.severity) - sevWeight(a.severity) || a.persona.localeCompare(b.persona));

  return (
    <div className="min-h-screen">
      <TopNav showActions />
      <main className="mx-auto max-w-6xl px-6 py-8">
        <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="font-display text-2xl font-semibold">Agent Failure Replay</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Every conversation an AI agent had with your store data — and where it broke.
            </p>
          </div>
        </header>

        <div className="surface-card mb-6 flex flex-wrap items-center gap-2 p-3">
          <span className="label-tiny mr-1 ml-2">Filter</span>
          <FilterPill active={classFilter==="ALL"}        onClick={() => setClassFilter("ALL")}>All {failures.length}</FilterPill>
          <FilterPill active={classFilter==="REFUSED"}     onClick={() => setClassFilter("REFUSED")}>🔴 REFUSED {counts.REFUSED}</FilterPill>
          <FilterPill active={classFilter==="VAGUE"}       onClick={() => setClassFilter("VAGUE")}>🟡 VAGUE {counts.VAGUE}</FilterPill>
          <FilterPill active={classFilter==="HALLUCINATED"}onClick={() => setClassFilter("HALLUCINATED")}>⚠️ HALLUCINATED {counts.HALLUCINATED}</FilterPill>
          <span className="mx-2 h-5 w-px bg-border" />
          <FilterPill active={personaFilter==="ALL"} onClick={() => setPersonaFilter("ALL")}>All personas</FilterPill>
          {PERSONAS.map(p => (
            <FilterPill key={p} active={personaFilter===p} onClick={() => setPersonaFilter(p)}>{p}</FilterPill>
          ))}
        </div>

        {list.length === 0 ? (
          <div className="surface-card p-12 text-center text-muted-foreground">
            No failures match these filters.
          </div>
        ) : (
          <div className="grid gap-3">
            {list.map((f, i) => (
              <FailureCard key={f.id} f={f} delay={i * 40} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

function sevWeight(s: string) { return s === "HIGH" ? 3 : s === "MEDIUM" ? 2 : 1; }

function FilterPill({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={`pill transition-colors ${active ? "pill-primary" : "pill-muted hover:bg-surface-elevated"}`}
    >
      {children}
    </button>
  );
}

function FailureCard({ f, delay }: { f: ReturnType<typeof getFailures>[number]; delay: number }) {
  const [open, setOpen] = useState(false);
  const c = CLASS_LABEL[f.classification];
  return (
    <article className="surface-card animate-fade-up p-5" style={{ animationDelay: `${delay}ms` }}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-2 text-sm">
          <span className="grid h-7 w-7 place-items-center rounded-full bg-secondary font-mono text-xs">👤</span>
          <span className="font-medium">{f.persona}</span>
          <span className="pill pill-muted ml-1">{f.severity} impact</span>
        </div>
        <span className={`pill ${c.pill}`}>{c.emoji} {c.label}</span>
      </div>

      <p className="mt-4 text-lg leading-snug text-foreground">"{f.query}"</p>

      <div className="mt-4 rounded-lg border border-border bg-background/40 p-4">
        <div className="label-tiny mb-1.5">🤖 AI Agent responded</div>
        <p className="text-sm leading-relaxed text-muted-foreground">"{open ? f.response : truncate(f.response, 140)}"</p>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-[1fr_auto] sm:items-center">
        <div>
          <div className="label-tiny mb-1">📌 Root cause</div>
          <p className="text-sm text-foreground/90">{f.rootCause}</p>
          <div className="mt-2 text-xs text-muted-foreground">
            Affects: <span className="text-foreground">{f.affects}</span>
          </div>
        </div>
        <div className="flex gap-2">
          <Link to="/fixes" search={{ id: f.id } as any} className="btn-ghost inline-flex items-center gap-1.5 text-sm">
            See Fix <ArrowRight className="h-4 w-4" />
          </Link>
          <button onClick={() => setOpen(o => !o)} className="btn-ghost inline-flex items-center gap-1 text-sm">
            {open ? <>Collapse <ChevronUp className="h-4 w-4" /></> : <>Expand <ChevronDown className="h-4 w-4" /></>}
          </button>
        </div>
      </div>

      {open && (
        <div className="mt-4 rounded-lg border border-dashed border-border p-4 text-sm">
          <div className="label-tiny mb-2">Forensics</div>
          <ul className="space-y-1.5 text-muted-foreground">
            <li><span className="text-foreground">Classification</span> · {c.label} ({f.classification === "HALLUCINATED" ? "fabricated unverifiable claim" : f.classification === "REFUSED" ? "agent declined to answer" : "answer lacked the specific facts the shopper needed"})</li>
            <li><span className="text-foreground">Source gap</span> · {f.rootCause}</li>
            <li><span className="text-foreground">Score impact</span> · +{f.scoreDelta} pts when fixed</li>
            <li><span className="text-foreground">Effort</span> · {f.effort}</li>
          </ul>
        </div>
      )}
    </article>
  );
}

function truncate(s: string, n: number) {
  return s.length > n ? s.slice(0, n) + "…" : s;
}
