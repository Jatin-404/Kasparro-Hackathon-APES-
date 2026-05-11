import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { ArrowRight, Loader2, TriangleAlert } from "lucide-react";
import { TopNav } from "@/components/TopNav";
import { fetchSavedAudit, saveAudit } from "@/lib/audit-api";

export const Route = createFileRoute("/audit/$auditId")({
  head: () => ({
    meta: [
      { title: "APES - Loading Saved Audit" },
      { name: "description", content: "Reloading a persisted APES audit report." },
    ],
  }),
  component: SavedAuditPage,
});

function SavedAuditPage() {
  const { auditId } = Route.useParams();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    fetchSavedAudit(auditId)
      .then((result) => {
        if (!mounted) return;
        saveAudit(result);
        navigate({ to: "/dashboard" });
      })
      .catch((err) => {
        if (!mounted) return;
        setError(err instanceof Error ? err.message : "Could not load saved audit");
      });
    return () => {
      mounted = false;
    };
  }, [auditId, navigate]);

  return (
    <div className="min-h-screen">
      <TopNav />
      <main className="mx-auto grid min-h-[70vh] max-w-2xl place-items-center px-6 py-10">
        <section className="surface-card w-full p-8 text-center">
          {error ? (
            <>
              <TriangleAlert className="mx-auto h-8 w-8 text-danger" />
              <h1 className="mt-4 font-display text-2xl font-semibold">Saved audit could not load</h1>
              <p className="mt-2 text-sm text-muted-foreground">{error}</p>
              <Link to="/history" className="btn-primary mt-6 inline-flex items-center gap-1.5">
                Back to History <ArrowRight className="h-4 w-4" />
              </Link>
            </>
          ) : (
            <>
              <Loader2 className="mx-auto h-8 w-8 animate-spin-soft text-primary" />
              <h1 className="mt-4 font-display text-2xl font-semibold">Loading saved audit</h1>
              <p className="mt-2 font-mono text-sm text-muted-foreground">{auditId}</p>
            </>
          )}
        </section>
      </main>
    </div>
  );
}
