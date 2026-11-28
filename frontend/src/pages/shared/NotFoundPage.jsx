import { ArrowLeft, Compass } from "lucide-react";
import { Link } from "react-router-dom";
import { useDocumentMeta } from "../../hooks/useDocumentMeta";

export default function NotFoundPage() {
  useDocumentMeta({
    title: "Page Not Found (404)",
    description: "The requested page could not be found in TalentPulse AI.",
  });

  return (
    <main id="main-content" tabIndex={-1} className="mx-auto flex max-w-lg flex-col items-center px-4 py-24 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-theme surface-soft">
        <Compass className="h-7 w-7" />
      </div>
      <div className="mt-4 text-xs font-semibold tracking-wider text-[var(--brand-accent)] uppercase">
        Error 404
      </div>
      <h1 className="mt-2 text-3xl font-bold text-heading">Page not found</h1>
      <p className="mt-2 text-sm text-muted">
        The route you requested does not exist. Return to the overview or open a portal.
      </p>
      <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
        <Link
          to="/"
          className="inline-flex items-center gap-2 rounded-xl bg-[var(--brand-primary)] px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[var(--brand-primary-hover)]"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Back to Overview</span>
        </Link>
        <Link
          to="/candidate"
          className="inline-flex items-center rounded-xl border border-theme bg-[var(--bg-surface)] px-5 py-2.5 text-sm font-medium text-body transition-colors hover:bg-[var(--bg-soft)]"
        >
          Candidate Portal
        </Link>
      </div>
    </main>
  );
}
