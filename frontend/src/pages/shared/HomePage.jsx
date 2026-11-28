import { ArrowRight, BrainCircuit, Database, Lock, ShieldCheck, Sparkles, Upload } from "lucide-react";
import { Link } from "react-router-dom";
import { useDocumentMeta } from "../../hooks/useDocumentMeta";
import {
  prefetchCandidateConfig,
  prefetchRecruiterDashboardIfAuthorized,
} from "../../services/api/prefetch";

export default function HomePage() {
  useDocumentMeta({
    title: "Overview",
    description:
      "Submit verified candidate resumes and run structured Gemini AI resume screening in TalentPulse AI.",
  });

  return (
    <main id="main-content" tabIndex={-1} className="mx-auto max-w-6xl px-4 pb-20 pt-10 sm:px-6 sm:pt-16">
      <section className="mx-auto max-w-4xl text-center">
        <div className="inline-flex items-center gap-2 rounded-full border border-theme surface-soft px-3.5 py-1.5 text-xs font-semibold tracking-wider uppercase">
          <Sparkles className="h-3.5 w-3.5 text-[var(--brand-accent)]" />
          <span>AI-Powered Recruitment Workspace</span>
        </div>

        <h1 className="mt-6 text-3xl font-bold tracking-tight text-heading sm:text-5xl">
          Screen resumes faster.{" "}
          <span className="text-[var(--brand-primary)]">Evaluate talent with precision.</span>
        </h1>

        <p className="mx-auto mt-5 max-w-2xl text-base leading-relaxed text-muted sm:text-lg">
          Collect verified candidate applications and empower recruiters with structured
          Gemini AI resume scoring, skill-gap diagnostics, and persistent candidate ranking.
        </p>

        <div className="mt-7 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <Link
            to="/candidate"
            onMouseEnter={prefetchCandidateConfig}
            onFocus={prefetchCandidateConfig}
            className="inline-flex min-h-[46px] w-full items-center justify-center gap-2 rounded-xl bg-[var(--brand-primary)] px-6 py-3 text-sm font-semibold text-white shadow-xs transition-colors hover:bg-[var(--brand-primary-hover)] sm:w-auto"
          >
            <span>Apply as Candidate</span>
            <ArrowRight className="h-4 w-4" />
          </Link>
          <Link
            to="/recruiter"
            onMouseEnter={prefetchRecruiterDashboardIfAuthorized}
            onFocus={prefetchRecruiterDashboardIfAuthorized}
            className="inline-flex min-h-[46px] w-full items-center justify-center gap-2 rounded-xl border border-theme bg-[var(--bg-surface)] px-6 py-3 text-sm font-semibold text-heading transition-colors hover:bg-[var(--bg-soft)] sm:w-auto"
          >
            <span>Recruiter Sign In</span>
          </Link>
        </div>
      </section>

      <section className="mt-10 grid gap-6 md:grid-cols-2 sm:mt-12">
        <div className="surface-card surface-card-interactive flex flex-col justify-between rounded-2xl p-6 sm:p-8">
          <div>
            <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-theme surface-soft">
              <Upload className="h-6 w-6" />
            </div>
            <h2 className="mt-5 text-xl font-bold text-heading sm:text-2xl">Candidate Portal</h2>
            <p className="mt-2.5 text-sm leading-relaxed text-muted sm:text-base">
              Submit your profile, verify your email via 4-digit OTP, choose your target
              technical role, and upload your PDF resume securely.
            </p>
          </div>

          <Link
            to="/candidate"
            onMouseEnter={prefetchCandidateConfig}
            onFocus={prefetchCandidateConfig}
            className="mt-8 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-[var(--brand-primary)] px-5 py-3 text-sm font-semibold text-white shadow-xs transition-colors hover:bg-[var(--brand-primary-hover)]"
          >
            <span>Continue as Candidate</span>
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>

        <div className="surface-card surface-card-interactive flex flex-col justify-between rounded-2xl p-6 sm:p-8">
          <div>
            <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-theme surface-soft text-[var(--brand-accent)]">
              <ShieldCheck className="h-6 w-6" />
            </div>
            <h2 className="mt-5 text-xl font-bold text-heading sm:text-2xl">
              Recruiter Workspace
            </h2>
            <p className="mt-2.5 text-sm leading-relaxed text-muted sm:text-base">
              Sign in to manage applicants, define job descriptions, run structured Gemini AI
              screening, and inspect ranked match diagnostics.
            </p>
          </div>

          <Link
            to="/recruiter"
            onMouseEnter={prefetchRecruiterDashboardIfAuthorized}
            onFocus={prefetchRecruiterDashboardIfAuthorized}
            className="mt-8 inline-flex w-full items-center justify-center gap-2 rounded-xl border border-[var(--brand-primary)] bg-[var(--bg-surface)] px-5 py-3 text-sm font-semibold text-[var(--brand-primary)] transition-colors hover:bg-[var(--bg-soft)]"
          >
            <span>Enter Recruiter Workspace</span>
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </section>

      <section className="mt-10 flex flex-wrap items-center justify-center gap-3 text-xs font-medium text-body sm:gap-4 sm:text-sm">
        <div className="flex items-center gap-2 rounded-full border border-theme bg-[var(--bg-surface)] px-4 py-2 shadow-2xs">
          <Lock className="h-4 w-4 text-[var(--brand-primary)]" />
          <span>OTP-Verified Submissions</span>
        </div>
        <div className="flex items-center gap-2 rounded-full border border-theme bg-[var(--bg-surface)] px-4 py-2 shadow-2xs">
          <Database className="h-4 w-4 text-[var(--brand-accent)]" />
          <span>Persistent SQLite Storage</span>
        </div>
        <div className="flex items-center gap-2 rounded-full border border-theme bg-[var(--bg-surface)] px-4 py-2 shadow-2xs">
          <BrainCircuit className="h-4 w-4 text-emerald-600" />
          <span>Structured Gemini AI Scoring</span>
        </div>
      </section>
    </main>
  );
}
