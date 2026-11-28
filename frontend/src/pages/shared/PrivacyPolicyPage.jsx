import { ArrowLeft, Shield } from "lucide-react";
import { Link } from "react-router-dom";
import { useDocumentMeta } from "../../hooks/useDocumentMeta";

export default function PrivacyPolicyPage() {
  useDocumentMeta({
    title: "Privacy Policy",
    description:
      "How candidate information, resumes, and AI-assisted screening data are handled in TalentPulse AI.",
  });

  return (
    <main id="main-content" tabIndex={-1} className="mx-auto max-w-3xl px-4 pb-20 pt-10 sm:px-6">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-theme surface-soft">
            <Shield className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-heading sm:text-3xl">Privacy Policy</h1>
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
          <h2 className="text-base font-semibold text-heading">1. Information We Collect</h2>
          <p>
            When you submit an application through the Candidate Portal, this application collects
            your full name, email address, phone number (formatted in international E.164 format),
            target technical role, years of professional experience, and the uploaded PDF resume.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-base font-semibold text-heading">2. Email Verification</h2>
          <p>
            Before accepting a resume submission, the portal sends a temporary 4-digit one-time
            passcode (OTP) to your email address via configured SMTP. The OTP is stored in
            memory as a salted cryptographic hash and expires after 5 minutes.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-base font-semibold text-heading">3. AI-Assisted Resume Evaluation</h2>
          <p>
            Authorized recruiters may run AI-assisted screening on stored resumes against a
            job description using Google Gemini models. Extracted resume text is sent to the
            configured Gemini API solely to generate structured match scores, skill-gap
            summaries, and recruiter justifications.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-base font-semibold text-heading">4. Storage, Access, and Retention</h2>
          <p>
            Candidate metadata and screening results are stored in the application&apos;s local
            SQLite database, and PDF files are stored on the server using opaque generated
            filenames. Access to recruiter views requires recruiter authentication. Data retention
            periods and deletion schedules are managed by <strong>[Organization / Controller Name]</strong>.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-base font-semibold text-heading">5. Browser Storage</h2>
          <p>
            This site uses essential browser storage (<code>localStorage</code> and{" "}
            <code>sessionStorage</code>) for your light/dark theme preference, privacy notice
            dismissal, OTP session binding, and recruiter session tokens. No third-party
            advertising or analytics tracking cookies are used.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-base font-semibold text-heading">6. Privacy Requests &amp; Contact</h2>
          <p>
            To request access, correction, or deletion of your submitted candidate record,
            please contact <strong>[Organization / Controller Name]</strong> at{" "}
            <strong>[privacy@example.com]</strong>.
          </p>
        </section>
      </article>
    </main>
  );
}

