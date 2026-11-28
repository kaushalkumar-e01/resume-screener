import { ArrowLeft, CheckCircle2, FileCheck2, ShieldCheck } from "lucide-react";
import { Link, Navigate, useLocation } from "react-router-dom";
import StatusBanner from "../../components/ui/StatusBanner";
import { useDocumentMeta } from "../../hooks/useDocumentMeta";

export default function SubmissionSuccessPage() {
  useDocumentMeta({
    title: "Application Submitted",
    description: "Your resume application has been verified and stored for recruiter review.",
  });

  const location = useLocation();
  const submission = location.state?.submission;

  if (!submission?.ok) {
    return <Navigate to="/candidate" replace />;
  }

  return (
    <main id="main-content" tabIndex={-1} className="mx-auto max-w-2xl px-4 pb-20 pt-12 sm:px-6">
      <div className="surface-card rounded-2xl p-6 text-center sm:p-10">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl border border-emerald-300/60 bg-emerald-500/10 text-emerald-600">
          <CheckCircle2 className="h-8 w-8" />
        </div>

        <h1 className="mt-5 text-2xl font-bold text-heading sm:text-3xl">
          Application Submitted Successfully
        </h1>

        <p className="mt-3 text-sm leading-relaxed text-body sm:text-base">
          Thank you, <strong>{submission.candidate_name}</strong>. Your{" "}
          <strong>{submission.page_count}-page</strong> PDF resume has been verified and
          securely stored for recruiter review.
        </p>

        {submission.warning && (
          <StatusBanner type="warning" className="mt-5 text-left">
            {submission.warning}
          </StatusBanner>
        )}

        <div className="mt-7 space-y-3 rounded-xl border border-theme bg-[var(--bg-canvas)] p-5 text-left text-sm text-body">
          <div className="font-semibold text-heading">What happens next</div>
          <ul className="space-y-2 text-xs leading-relaxed text-muted sm:text-sm">
            <li className="flex items-start gap-2">
              <FileCheck2 className="mt-0.5 h-4 w-4 shrink-0 text-[var(--brand-primary)]" />
              <span>Your application is queued in the recruiter workspace for structured review.</span>
            </li>
            <li className="flex items-start gap-2">
              <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-[var(--brand-accent)]" />
              <span>Your PDF is stored with an opaque server filename accessible only to authorized recruiters.</span>
            </li>
          </ul>
        </div>

        <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:justify-center">
          <Link
            to="/"
            className="inline-flex min-h-[44px] items-center justify-center gap-2 rounded-xl bg-[var(--brand-primary)] px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[var(--brand-primary-hover)]"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Return to Overview</span>
          </Link>
          <Link
            to="/candidate"
            className="inline-flex min-h-[44px] items-center justify-center rounded-xl border border-theme bg-[var(--bg-surface)] px-5 py-2.5 text-sm font-medium text-body transition-colors hover:bg-[var(--bg-soft)]"
          >
            Submit Another Application
          </Link>
        </div>
      </div>
    </main>
  );
}

