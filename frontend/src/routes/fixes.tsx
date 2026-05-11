import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { TopNav } from "@/components/TopNav";
import { getFailures, loadAudit } from "@/lib/audit-api";
import { ArrowLeft, ArrowRight, Check, X } from "lucide-react";

export const Route = createFileRoute("/fixes")({
  validateSearch: (s: Record<string, unknown>) => ({ id: typeof s.id === "string" ? s.id : undefined }),
  head: () => ({
    meta: [
      { title: "APES — Before / After Fixes" },
      { name: "description", content: "Compare original store content with Claude's suggested fix, side by side." },
    ],
  }),
  component: Fixes,
});

function Fixes() {
  const { id } = Route.useSearch();
  const [audit] = useState(() => loadAudit());
  const failures = getFailures(audit);
  const startIdx = Math.max(0, failures.findIndex(f => f.id === id));
  const [idx, setIdx] = useState(startIdx === -1 ? 0 : startIdx);
  const [showModal, setShowModal] = useState(false);
  const [applied, setApplied] = useState<Record<string, boolean>>({});

  const f = failures[idx];
  const total = failures.length;
  const isApplied = !!applied[f.id];

  return (
    <div className="min-h-screen">
      <TopNav showActions />
      <main className="mx-auto max-w-6xl px-6 py-8">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <div className="label-tiny">Fix {idx + 1} of {total}</div>
            <h1 className="mt-1 font-display text-2xl font-semibold">{f.fixTitle}</h1>
          </div>
          <div className="flex gap-2">
            <button onClick={() => setIdx(i => (i - 1 + total) % total)} className="btn-ghost inline-flex items-center gap-1.5">
              <ArrowLeft className="h-4 w-4" /> Previous
            </button>
            <button onClick={() => setIdx(i => (i + 1) % total)} className="btn-ghost inline-flex items-center gap-1.5">
              Next <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <Panel
            tone="danger"
            heading="BEFORE"
            subheading="Original Content"
            content={f.before}
            agentLabel="AI said"
            agentText={f.response}
            classification={f.classification}
          />
          <Panel
            tone="success"
            heading="AFTER"
            subheading="Claude's Suggested Fix"
            content={f.after}
            agentLabel="AI said"
            agentText={f.fixedResponse}
            classification="CONFIDENT"
          />
        </div>

        {/* Bottom bar */}
        <div className="surface-card mt-6 flex flex-wrap items-center justify-between gap-4 p-5">
          <div className="flex flex-wrap items-center gap-6 text-sm">
            <div>
              <div className="label-tiny">Impact</div>
              <div className="mt-0.5 text-success">+{f.scoreDelta} points to AI Readiness Score</div>
            </div>
            <div>
              <div className="label-tiny">Effort</div>
              <div className="mt-0.5">{f.effort} — Add to Shopify Policies page</div>
            </div>
            <div>
              <div className="label-tiny">Affects</div>
              <div className="mt-0.5">{f.affects}</div>
            </div>
          </div>
          <div className="flex gap-2">
            <Link to="/failures" className="btn-ghost text-sm">Back to failures</Link>
            {isApplied ? (
              <span className="pill pill-success"><Check className="h-3 w-3" /> Applied</span>
            ) : (
              <button onClick={() => setShowModal(true)} className="btn-primary inline-flex items-center gap-1.5">
                <Check className="h-4 w-4" /> Apply This Fix
              </button>
            )}
          </div>
        </div>
      </main>

      {showModal && (
        <Modal onClose={() => setShowModal(false)}>
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="font-display text-xl font-semibold">Publish to Shopify</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                This will update your Shopify store. Review the suggested content before publishing.
              </p>
            </div>
            <button onClick={() => setShowModal(false)} className="rounded-md p-1 text-muted-foreground hover:bg-surface hover:text-foreground">
              <X className="h-5 w-5" />
            </button>
          </div>

          <div className="mt-5 grid gap-3 md:grid-cols-2">
            <div className="rounded-lg border border-danger/30 bg-danger/5 p-4">
              <div className="label-tiny text-danger">— Removed</div>
              <p className="mt-2 whitespace-pre-wrap font-mono text-xs leading-relaxed text-foreground/80 line-through decoration-danger/40">
                {f.before}
              </p>
            </div>
            <div className="rounded-lg border border-success/30 bg-success/5 p-4">
              <div className="label-tiny text-success">+ Added</div>
              <p className="mt-2 whitespace-pre-wrap font-mono text-xs leading-relaxed text-foreground">{f.after}</p>
            </div>
          </div>

          <div className="mt-5 flex justify-end gap-2">
            <button onClick={() => setShowModal(false)} className="btn-ghost text-sm">Cancel</button>
            <button
              onClick={() => { setApplied(a => ({ ...a, [f.id]: true })); setShowModal(false); }}
              className="btn-primary inline-flex items-center gap-1.5"
            >
              <Check className="h-4 w-4" /> Publish to Shopify
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}

function Panel({
  tone, heading, subheading, content, agentLabel, agentText, classification,
}: {
  tone: "danger" | "success";
  heading: string; subheading: string; content: string;
  agentLabel: string; agentText: string; classification: string;
}) {
  const isBad = tone === "danger";
  const headerClass = isBad
    ? "border-danger/30 text-danger bg-danger/5"
    : "border-success/30 text-success bg-success/5";
  const pill = isBad ? "pill-warning" : "pill-success";
  return (
    <article className="surface-card overflow-hidden p-0">
      <header className={`flex items-center justify-between border-b px-5 py-3 ${headerClass}`}>
        <div className="font-display text-sm font-bold tracking-wider">{heading}</div>
        <div className="font-mono text-xs opacity-80">{subheading}</div>
      </header>
      <div className="space-y-4 p-5">
        <div className="rounded-lg border border-border bg-background/50 p-4">
          <div className="label-tiny mb-2">Store Content</div>
          <p className={`whitespace-pre-wrap text-sm leading-relaxed ${isBad ? "text-foreground/80" : "text-foreground"}`}>
            {isBad ? <span className="underline decoration-danger/60 decoration-wavy underline-offset-4">{content}</span>
                   : <mark className="bg-success/15 text-success-foreground rounded px-1 py-0.5 text-foreground">{content}</mark>}
          </p>
        </div>

        <div className="rounded-lg border border-border bg-background/30 p-4">
          <div className="flex items-center justify-between">
            <div className="label-tiny">🤖 {agentLabel}</div>
            <span className={`pill ${pill}`}>{classification}</span>
          </div>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">"{agentText}"</p>
        </div>
      </div>
    </article>
  );
}

function Modal({ children, onClose }: { children: React.ReactNode; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-background/80 px-4 backdrop-blur-sm" onClick={onClose}>
      <div
        className="surface-card w-full max-w-2xl animate-slam p-6"
        onClick={(e) => e.stopPropagation()}
      >
        {children}
      </div>
    </div>
  );
}
