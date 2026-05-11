import { Link, useLocation } from "@tanstack/react-router";
import { Activity } from "lucide-react";
import { loadAudit } from "@/lib/audit-api";

export function TopNav({ showActions = false }: { showActions?: boolean }) {
  const { pathname } = useLocation();
  const isLanding = pathname === "/";
  const audit = typeof window === "undefined" ? null : loadAudit();
  const storeUrl = audit?.store_context.store_url || "hackathon-store.myshopify.com";
  return (
    <header className="sticky top-0 z-30 border-b border-border bg-background/70 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-6">
        <Link to="/" className="flex items-center gap-2">
          <div className="grid h-7 w-7 place-items-center rounded-md bg-gradient-to-br from-primary to-primary-glow shadow-[0_0_24px_-4px_var(--primary)]">
            <Activity className="h-4 w-4 text-primary-foreground" strokeWidth={2.5} />
          </div>
          <span className="font-display text-lg font-bold tracking-tight">APES</span>
          {!isLanding && (
            <span className="ml-3 hidden font-mono text-xs text-muted-foreground sm:inline">
              hackathon-store.myshopify.com
            </span>
          )}
        </Link>
        {isLanding ? (
          <nav className="flex items-center gap-2 text-sm">
            <a href="#how" className="hidden px-3 py-1.5 text-muted-foreground hover:text-foreground sm:inline">How it works</a>
            <Link to="/dashboard" className="btn-ghost text-sm">View Demo</Link>
          </nav>
        ) : showActions ? (
          <nav className="flex items-center gap-2">
            <NavLink to="/dashboard" label="Overview" />
            <NavLink to="/failures" label="Failures" />
            <NavLink to="/fixes" label="Fixes" />
            <NavLink to="/plan" label="Action Plan" />
            <Link
              to="/history"
              search={{ store: storeUrl } as any}
              className={`rounded-md px-3 py-1.5 text-sm transition-colors ${
                pathname.startsWith("/history") ? "bg-surface text-foreground" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              History
            </Link>
            <Link to="/audit" className="btn-ghost ml-2 text-sm">Re-run Audit</Link>
            <button className="btn-primary">Export Report</button>
          </nav>
        ) : null}
      </div>
    </header>
  );
}

function NavLink({ to, label }: { to: string; label: string }) {
  const { pathname } = useLocation();
  const active = pathname.startsWith(to);
  return (
    <Link
      to={to}
      className={`rounded-md px-3 py-1.5 text-sm transition-colors ${
        active ? "bg-surface text-foreground" : "text-muted-foreground hover:text-foreground"
      }`}
    >
      {label}
    </Link>
  );
}
