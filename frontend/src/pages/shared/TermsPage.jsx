import { ArrowLeft, FileText } from "lucide-react";
import { Link } from "react-router-dom";
import { useDocumentMeta } from "../../hooks/useDocumentMeta";

export default function TermsPage() {
  useDocumentMeta({
    title: "Terms & Conditions",
    description:
      "Terms of use for candidates and recruiters using the TalentPulse AI Resume Screening System.",
  });

  return (
    <main id="main-content" tabIndex={-1} className="mx-auto max-w-3xl px-4 pb-20 pt-10 sm:px-6">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-theme surface-soft">
            <FileText className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-heading sm:text-3xl">Terms &amp; Conditions</h1>
            <p className="text-xs text-muted">Last updated: [Insert Date]</p>
          </div>
        </div>
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 rounded-xl border border-theme bg-[var(--bg-surface)] px-3.5 py-2 text-xs font-medium text-body transition-colors hover:bg-[var(--bg-soft)]"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>Overview</span>
        </Link>
      </div>

      <article className="surface-card space-y-6 rounded-2xl p-6 text-sm leading-relaxed text-body sm:p-8">
        <section className="space-y-2">
          <h2 className="text-base font-semibold text-heading">1. Platform Purpose</h2>
          <p>
            This platform is provided by <strong>[Organization Name]</strong> to collect
            candidate job applications and assist authorized recruiters with resume review.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-base font-semibold text-heading">2. Candidate Submissions</h2>
          <p>
            Candidates agree to provide accurate contact information and submit only their own
            legitimate resume documents in PDF format. Automated abuse, deceptive content, or
            unauthorized access attempts are prohibited.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-base font-semibold text-heading">3. AI-Assisted Evaluation</h2>
          <p>
            AI-generated match scores, skill breakdowns, and assessments are decision-support
            outputs intended to assist human recruiters. They do not constitute automated final
            hiring decisions or guarantees of employment.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-base font-semibold text-heading">4. Availability &amp; Limitations</h2>
          <p>
            The service is provided on an &quot;as-is&quot; basis. <strong>[Organization Name]</strong>{" "}
            does not warrant uninterrupted availability of external email (SMTP) or AI API
            services.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-base font-semibold text-heading">5. Contact</h2>
          <p>
            Questions regarding these terms may be directed to{" "}
            <strong>[contact@example.com]</strong>.
          </p>
        </section>
      </article>
    </main>
  );
}

