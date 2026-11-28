import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  ChevronDown,
  Clock,
  FileText,
  HelpCircle,
  Loader2,
  Mail,
  Minus,
  Plus,
  Send,
  ShieldCheck,
  UploadCloud,
} from "lucide-react";
import { memo, useCallback, useEffect, useId, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import RoleCombobox from "../../components/common/RoleCombobox";
import UnifiedPhoneInput from "../../components/common/UnifiedPhoneInput";
import StatusBanner from "../../components/ui/StatusBanner";
import { useDocumentMeta } from "../../hooks/useDocumentMeta";
import { candidateApi } from "../../services/api/candidateApi";
import { getCandidateConfigCached } from "../../services/api/prefetch";
import { captureUtmParams } from "../../utils/utm";

function createSessionId() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `sess_${Date.now()}_${Math.random().toString(36).slice(2, 11)}`;
}

const DEFAULT_ROLES = [
  "AI Engineer",
  "Machine Learning Engineer",
  "Data Scientist",
  "Data Engineer",
  "Data Analyst",
  "Software Engineer",
  "Full-Stack Engineer",
  "Backend Engineer",
  "Frontend Engineer",
  "Mobile App Developer (iOS / Android)",
  "DevOps Engineer",
  "Site Reliability Engineer (SRE)",
  "Cloud Engineer",
  "Platform Engineer",
  "Cybersecurity Engineer",
  "QA / Test Automation Engineer",
  "Database Administrator (DBA)",
  "Solutions Architect",
  "Systems Engineer",
  "Embedded Systems Engineer",
  "Blockchain Developer",
  "Game Developer",
  "UI/UX Designer",
  "Technical Product Manager",
  "Engineering Manager",
];

const FAQ_ITEMS = [
  {
    q: "Why do I need to verify my email with a 4-digit OTP?",
    a: "Email verification prevents automated spam submissions and ensures your application is tied to a valid, reachable email address. Codes expire after 5 minutes.",
  },
  {
    q: "What resume file formats are supported?",
    a: "Only text-selectable PDF files up to 10 MB are accepted. Scanned image-only PDFs may receive a low-text warning during parsing.",
  },
  {
    q: "What happens if I submit again with the same email?",
    a: "Submitting with an email already on file updates your existing candidate record and replaces your previous resume for fresh recruiter review.",
  },
  {
    q: "How is my phone number and personal data handled?",
    a: "Your phone number is validated and stored in international E.164 format. Resumes are saved with opaque server-generated filenames accessible only to authenticated recruiters.",
  },
];

function formatCountdown(seconds) {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

const OtpVerificationSection = memo(function OtpVerificationSection({
  sessionId,
  email,
  emailVerified,
  onVerified,
  onResetVerification,
  onEmailChange,
}) {
  const emailId = useId();
  const otpId = useId();

  const [otpSent, setOtpSent] = useState(false);
  const [otpCode, setOtpCode] = useState("");
  const [otpFeedback, setOtpFeedback] = useState(null);
  const [sendingOtp, setSendingOtp] = useState(false);
  const [verifyingOtp, setVerifyingOtp] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);
  const [expirySeconds, setExpirySeconds] = useState(0);

  useEffect(() => {
    if (!email && !emailVerified && !otpSent) {
      setOtpFeedback(null);
      setOtpCode("");
      setResendCooldown(0);
      setExpirySeconds(0);
    }
  }, [email, emailVerified, otpSent]);

  useEffect(() => {
    if (resendCooldown <= 0 && expirySeconds <= 0) return;
    const timer = setInterval(() => {
      setResendCooldown((prev) => Math.max(0, prev - 1));
      setExpirySeconds((prev) => Math.max(0, prev - 1));
    }, 1000);
    return () => clearInterval(timer);
  }, [resendCooldown, expirySeconds]);

  const handleInputChange = (nextEmail) => {
    onEmailChange(nextEmail);
    if (emailVerified || otpSent) {
      onResetVerification();
      setOtpSent(false);
      setOtpCode("");
      setOtpFeedback(null);
      setResendCooldown(0);
      setExpirySeconds(0);
      candidateApi.syncEmail(sessionId, nextEmail).catch(() => { });
    }
  };

  const handleSendOtp = async () => {
    const trimmed = email.trim().toLowerCase();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmed)) {
      setOtpFeedback({ type: "error", text: "Please enter a valid email address first." });
      return;
    }
    setSendingOtp(true);
    setOtpFeedback(null);
    try {
      const res = await candidateApi.sendOtp(sessionId, trimmed);
      setOtpSent(true);
      onResetVerification();
      setResendCooldown(60);
      setExpirySeconds(300);
      setOtpFeedback({ type: "success", text: res.message });
    } catch (err) {
      setOtpFeedback({ type: "error", text: err.message });
    } finally {
      setSendingOtp(false);
    }
  };

  const handleVerifyOtp = async () => {
    const trimmed = email.trim().toLowerCase();
    if (!/^\d{4}$/.test(otpCode.trim())) {
      setOtpFeedback({ type: "error", text: "Please enter the 4-digit numeric verification code." });
      return;
    }
    setVerifyingOtp(true);
    setOtpFeedback(null);
    try {
      const res = await candidateApi.verifyOtp(sessionId, trimmed, otpCode.trim());
      onVerified();
      setOtpSent(false);
      setResendCooldown(0);
      setExpirySeconds(0);
      setOtpFeedback({ type: "success", text: res.message });
    } catch (err) {
      setOtpFeedback({ type: "error", text: err.message });
    } finally {
      setVerifyingOtp(false);
    }
  };

  return (
    <div className="space-y-3">
      <div className="space-y-1.5">
        <label htmlFor={emailId} className="block text-sm font-medium text-body">
          Email Address <span className="text-[var(--brand-primary)]" aria-hidden="true">*</span>
        </label>
        <input
          id={emailId}
          name="email"
          type="email"
          autoComplete="email"
          autoCapitalize="none"
          spellCheck={false}
          maxLength={254}
          required
          value={email}
          onChange={(e) => handleInputChange(e.target.value)}
          placeholder="e.g., jane.doe@example.com"
          className="surface-input min-h-[46px] w-full rounded-xl px-3.5 py-2.5 text-sm transition-colors"
        />
      </div>

      {emailVerified ? (
        <div
          role="status"
          className="flex items-center gap-2 rounded-xl border border-emerald-300/60 bg-emerald-500/10 px-3.5 py-2.5 text-sm font-medium text-emerald-700 dark:text-emerald-300"
        >
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          <span className="min-w-0 truncate">Email verified: {email.trim().toLowerCase()}</span>
        </div>
      ) : (
        <>
          <button
            type="button"
            onClick={handleSendOtp}
            disabled={sendingOtp || resendCooldown > 0}
            className="inline-flex min-h-[42px] w-full items-center justify-center gap-2 rounded-xl border border-theme surface-soft px-4 py-2 text-sm font-medium transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {sendingOtp ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Mail className="h-4 w-4" />
            )}
            <span>
              {resendCooldown > 0
                ? `Resend OTP in ${resendCooldown}s`
                : otpSent
                  ? "Resend OTP"
                  : "Verify Email"}
            </span>
          </button>

          {otpSent && (
            <div className="space-y-2.5 rounded-xl border border-theme bg-[var(--bg-canvas)] p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <label htmlFor={otpId} className="block text-xs font-medium text-body">
                  Enter 4-Digit Verification Code (OTP)
                </label>
                {expirySeconds > 0 ? (
                  <span className="inline-flex items-center gap-1 text-xs font-medium text-[var(--brand-primary)]">
                    <Clock className="h-3 w-3" />
                    Expires in {formatCountdown(expirySeconds)}
                  </span>
                ) : (
                  <span className="text-xs font-medium text-amber-600">Code expired</span>
                )}
              </div>
              <input
                id={otpId}
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={4}
                value={otpCode}
                onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, "").slice(0, 4))}
                placeholder="1234"
                className="surface-input min-h-[44px] w-full rounded-xl px-3.5 py-2 text-center text-lg font-semibold tracking-[0.45em] placeholder:tracking-normal"
              />
              <button
                type="button"
                onClick={handleVerifyOtp}
                disabled={verifyingOtp || expirySeconds === 0}
                className="inline-flex min-h-[42px] w-full items-center justify-center gap-2 rounded-xl bg-[var(--brand-primary)] px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-[var(--brand-primary-hover)] disabled:opacity-60"
              >
                {verifyingOtp && <Loader2 className="h-4 w-4 animate-spin" />}
                <span>Verify OTP</span>
              </button>
            </div>
          )}
        </>
      )}

      {otpFeedback && <StatusBanner type={otpFeedback.type}>{otpFeedback.text}</StatusBanner>}
    </div>
  );
});

const CandidateFaqSection = memo(function CandidateFaqSection() {
  const [openIndex, setOpenIndex] = useState(null);

  return (
    <section aria-labelledby="candidate-faq-heading" className="mt-10 surface-card rounded-2xl p-5 sm:p-7">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2 border-b border-theme pb-3">
        <div className="flex items-center gap-2">
          <HelpCircle className="h-5 w-5 text-[var(--brand-primary)]" />
          <h2 id="candidate-faq-heading" className="text-base font-semibold text-heading">
            Frequently Asked Questions
          </h2>
        </div>
        <span className="text-xs text-muted">Last updated: Nov 28, 2026</span>
      </div>

      <div className="divide-y divide-[var(--border-color)]">
        {FAQ_ITEMS.map((item, idx) => {
          const isOpen = openIndex === idx;
          const panelId = `faq-panel-${idx}`;
          const btnId = `faq-btn-${idx}`;
          return (
            <div key={item.q} className="py-3 first:pt-1 last:pb-1">
              <button
                id={btnId}
                type="button"
                aria-expanded={isOpen}
                aria-controls={panelId}
                onClick={() => setOpenIndex(isOpen ? null : idx)}
                className="flex w-full items-center justify-between gap-3 py-1 text-left text-sm font-medium text-heading transition-colors hover:text-[var(--brand-primary)]"
              >
                <span>{item.q}</span>
                <ChevronDown
                  className={`h-4 w-4 shrink-0 text-muted transition-transform ${isOpen ? "rotate-180" : ""
                    }`}
                />
              </button>
              {isOpen && (
                <div
                  id={panelId}
                  role="region"
                  aria-labelledby={btnId}
                  className="pt-2 text-sm leading-relaxed text-muted"
                >
                  {item.a}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
});

export default function CandidatePortalPage() {
  useDocumentMeta({
    title: "Candidate Portal",
    description:
      "Verify your email with a 4-digit OTP and submit your PDF resume for AI-assisted recruiter review.",
  });

  const nameId = useId();
  const expId = useId();
  const fileId = useId();
  const location = useLocation();
  const navigate = useNavigate();

  const [sessionId] = useState(createSessionId);
  const [roles, setRoles] = useState(DEFAULT_ROLES);
  const [maxUploadMb, setMaxUploadMb] = useState(10);

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phoneState, setPhoneState] = useState({ region: "IN", phone: "" });
  const [targetRole, setTargetRole] = useState("");
  const [yearsExp, setYearsExp] = useState(0);
  const [resumeFile, setResumeFile] = useState(null);
  const [emailVerified, setEmailVerified] = useState(false);
  const [confirmAdult, setConfirmAdult] = useState(false);

  const [submitting, setSubmitting] = useState(false);
  const [fieldErrors, setFieldErrors] = useState({});
  const [submitErrors, setSubmitErrors] = useState([]);

  useEffect(() => {
    captureUtmParams(location.search);
  }, [location.search]);

  useEffect(() => {
    getCandidateConfigCached()
      .then((cfg) => {
        if (Array.isArray(cfg.technical_roles) && cfg.technical_roles.length) {
          setRoles(cfg.technical_roles);
        }
        if (cfg.max_upload_size_mb) {
          setMaxUploadMb(cfg.max_upload_size_mb);
        }
      })
      .catch(() => { });
  }, []);

  const handleVerified = useCallback(() => setEmailVerified(true), []);
  const handleResetVerification = useCallback(() => setEmailVerified(false), []);

  const stepExperience = (delta) => {
    setYearsExp((prev) => {
      const next = Math.round((Number(prev || 0) + delta) * 2) / 2;
      return Math.min(50, Math.max(0, next));
    });
  };

  const handleFileSelect = (file) => {
    if (!file) {
      setResumeFile(null);
      return;
    }
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setSubmitErrors(["Only PDF files are accepted."]);
      setResumeFile(null);
      return;
    }
    if (file.size > maxUploadMb * 1024 * 1024) {
      setSubmitErrors([`The selected PDF exceeds the ${maxUploadMb} MB limit.`]);
      setResumeFile(null);
      return;
    }
    setSubmitErrors([]);
    setResumeFile(file);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitErrors([]);
    setFieldErrors({});

    const errs = [];
    const fErrs = {};
    const trimmedName = fullName.trim().replace(/\s+/g, " ");
    if (!trimmedName || trimmedName.replace(/\s/g, "").length < 2) {
      fErrs.fullName = "Please enter your full name (at least 2 characters).";
      errs.push(fErrs.fullName);
    } else if (!/\p{L}/u.test(trimmedName) || /\d/.test(trimmedName)) {
      fErrs.fullName = "Please enter a valid full name without numbers or symbol-only text.";
      errs.push(fErrs.fullName);
    }

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      errs.push("Please enter a valid email address.");
    } else if (!emailVerified) {
      errs.push("Please verify your email address using the 4-digit OTP before submitting.");
    }

    if (!phoneState.phone.trim()) {
      fErrs.phone = "Phone Number is required.";
      errs.push(fErrs.phone);
    }
    if (!targetRole) {
      fErrs.role = "Please select a target position / role from the list.";
      errs.push(fErrs.role);
    }
    if (yearsExp < 0 || yearsExp > 50 || Math.round(yearsExp * 2) !== yearsExp * 2) {
      errs.push("Professional experience must be between 0 and 50 years in 0.5-year increments.");
    }
    if (!resumeFile) {
      errs.push("Please upload a PDF resume.");
    }
    if (!confirmAdult) {
      fErrs.confirmAdult = "Please confirm that you are 18+ and accept the Privacy Policy and Terms.";
      errs.push(fErrs.confirmAdult);
    }

    if (errs.length > 0) {
      setFieldErrors(fErrs);
      setSubmitErrors(errs);
      return;
    }

    const fd = new FormData();
    fd.append("session_id", sessionId);
    fd.append("name", trimmedName);
    fd.append("email", email.trim().toLowerCase());
    fd.append("region_code", phoneState.region);
    fd.append("phone", phoneState.phone);
    fd.append("target_role", targetRole);
    fd.append("years_exp", String(yearsExp));
    fd.append("confirm_adult", confirmAdult ? "true" : "false");
    fd.append("resume", resumeFile);

    setSubmitting(true);
    try {
      const res = await candidateApi.submitApplication(fd);
      navigate("/candidate/success", { state: { submission: res }, replace: true });
    } catch (err) {
      setSubmitErrors([err.message]);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main id="main-content" tabIndex={-1} className="mx-auto max-w-3xl px-4 pb-20 pt-8 sm:px-6 sm:pt-10">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-heading sm:text-3xl">
            Candidate Application Portal
          </h1>
          <p className="mt-1 text-sm text-muted">
            Verify your email and submit your resume for AI-assisted recruiter review.
          </p>
        </div>
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 rounded-xl border border-theme bg-[var(--bg-surface)] px-3.5 py-2 text-xs font-medium text-body transition-colors hover:border-[var(--brand-accent)] hover:text-heading"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>Overview</span>
        </Link>
      </div>

      <StatusBanner type="info" className="mb-6">
        <span className="flex items-center gap-2">
          <ShieldCheck className="hidden h-4 w-4 shrink-0 text-[var(--brand-accent)] sm:inline" />
          <span>
            Your PDF is stored securely with an opaque server filename. Only authenticated
            recruiters can access application records. Maximum size: <strong>{maxUploadMb} MB</strong>.
          </span>
        </span>
      </StatusBanner>

      <form
        onSubmit={handleSubmit}
        noValidate
        className="surface-card space-y-6 rounded-2xl p-5 sm:p-8"
      >
        <div className="border-b border-theme pb-3">
          <h2 className="text-base font-semibold text-heading">1. Applicant Information</h2>
        </div>

        {/* Full Name */}
        <div className="space-y-1.5">
          <label htmlFor={nameId} className="block text-sm font-medium text-body">
            Full Name <span className="text-[var(--brand-primary)]" aria-hidden="true">*</span>
          </label>
          <input
            id={nameId}
            name="full_name"
            type="text"
            autoComplete="name"
            maxLength={120}
            required
            aria-invalid={Boolean(fieldErrors.fullName)}
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            placeholder="e.g., Jane Doe"
            className={`surface-input min-h-[46px] w-full rounded-xl px-3.5 py-2.5 text-sm transition-colors ${fieldErrors.fullName ? "border-rose-400 focus:border-rose-500" : ""
              }`}
          />
          {fieldErrors.fullName && (
            <p role="alert" className="text-xs font-medium text-rose-600">
              {fieldErrors.fullName}
            </p>
          )}
        </div>

        {/* Email + Isolated OTP Section */}
        <OtpVerificationSection
          sessionId={sessionId}
          email={email}
          emailVerified={emailVerified}
          onVerified={handleVerified}
          onResetVerification={handleResetVerification}
          onEmailChange={setEmail}
        />

        {/* Unified Phone Input */}
        <UnifiedPhoneInput
          region={phoneState.region}
          phone={phoneState.phone}
          onChange={setPhoneState}
          error={fieldErrors.phone}
        />

        {/* Target Role */}
        <RoleCombobox
          roles={roles}
          value={targetRole}
          onChange={setTargetRole}
          error={fieldErrors.role}
        />

        {/* Experience (Years) */}
        <div className="space-y-1.5">
          <label htmlFor={expId} className="block text-sm font-medium text-body">
            Professional Experience (years)
          </label>
          <div className="flex items-center gap-2">
            <button
              type="button"
              aria-label="Decrease experience by 0.5 years"
              onClick={() => stepExperience(-0.5)}
              className="flex h-[46px] w-12 shrink-0 items-center justify-center rounded-xl border border-theme bg-[var(--bg-surface)] text-body transition-colors hover:bg-[var(--bg-soft)]"
            >
              <Minus className="h-4 w-4" />
            </button>
            <input
              id={expId}
              name="years_exp"
              type="number"
              min="0"
              max="50"
              step="0.5"
              value={yearsExp}
              onChange={(e) => setYearsExp(e.target.value === "" ? 0 : Number(e.target.value))}
              className="surface-input min-h-[46px] min-w-0 flex-1 rounded-xl px-3.5 py-2.5 text-center text-sm font-medium transition-colors"
            />
            <button
              type="button"
              aria-label="Increase experience by 0.5 years"
              onClick={() => stepExperience(0.5)}
              className="flex h-[46px] w-12 shrink-0 items-center justify-center rounded-xl border border-theme bg-[var(--bg-surface)] text-body transition-colors hover:bg-[var(--bg-soft)]"
            >
              <Plus className="h-4 w-4" />
            </button>
          </div>
          <p className="text-xs text-muted">Increments of 0.5 years (0 → 0.5 → 1.0 → 1.5…)</p>
        </div>

        {/* Resume Upload */}
        <div className="border-t border-theme pt-5">
          <h2 className="mb-3 text-base font-semibold text-heading">2. Resume Upload</h2>
          <label
            htmlFor={fileId}
            className="flex cursor-pointer flex-col items-center justify-center rounded-2xl border border-dashed border-[var(--border-input)] bg-[var(--bg-canvas)] px-4 py-7 text-center transition-colors hover:border-[var(--brand-primary)] hover:bg-[var(--bg-soft)]/50 sm:px-6"
          >
            <UploadCloud className="h-8 w-8 text-[var(--brand-accent)]" />
            <span className="mt-2.5 max-w-full truncate text-sm font-medium text-heading">
              {resumeFile ? resumeFile.name : "Click to upload your PDF resume"}
            </span>
            <span className="mt-1 text-xs text-muted">
              {resumeFile
                ? `${(resumeFile.size / 1024).toFixed(1)} KB · Ready to submit`
                : `Text-selectable PDF only · Max ${maxUploadMb} MB`}
            </span>
            {resumeFile && (
              <span className="mt-2 inline-flex items-center gap-1 rounded-full border border-emerald-300/60 bg-emerald-500/10 px-2.5 py-0.5 text-xs font-medium text-emerald-700 dark:text-emerald-300">
                <FileText className="h-3 w-3" /> PDF selected
              </span>
            )}
            <input
              id={fileId}
              type="file"
              accept=".pdf,application/pdf"
              className="sr-only"
              onChange={(e) => handleFileSelect(e.target.files?.[0] || null)}
            />
          </label>
        </div>

        {submitErrors.length > 0 && (
          <div
            role="alert"
            aria-live="assertive"
            className="space-y-1.5 rounded-xl border border-rose-300/60 bg-rose-500/10 p-4 text-sm text-rose-800 dark:text-rose-200"
          >
            {submitErrors.map((err, i) => (
              <div key={i} className="flex items-start gap-2">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-600 dark:text-rose-400" />
                <span>{err}</span>
              </div>
            ))}
          </div>
        )}

        <div className="space-y-1.5">
          <label className="flex cursor-pointer items-start gap-2.5 text-xs leading-relaxed text-body sm:text-sm">
            <input
              type="checkbox"
              checked={confirmAdult}
              onChange={(e) => setConfirmAdult(e.target.checked)}
              aria-invalid={Boolean(fieldErrors.confirmAdult)}
              className="mt-1 h-4 w-4 shrink-0 rounded border-[var(--border-input)]"
            />
            <span>
              I confirm that I am at least 18 years old and agree to the{" "}
              <Link to="/privacy" className="text-[var(--brand-primary)] underline">
                Privacy Policy
              </Link>{" "}
              and{" "}
              <Link to="/terms" className="text-[var(--brand-primary)] underline">
                Terms &amp; Conditions
              </Link>
              .
            </span>
          </label>
          {fieldErrors.confirmAdult && (
            <p role="alert" className="text-xs font-medium text-rose-600">
              {fieldErrors.confirmAdult}
            </p>
          )}
        </div>

        <button
          type="submit"
          disabled={submitting}
          className="inline-flex min-h-[48px] w-full items-center justify-center gap-2 rounded-xl bg-[var(--brand-primary)] px-6 py-3 text-sm font-semibold text-white shadow-xs transition-colors hover:bg-[var(--brand-primary-hover)] disabled:opacity-60"
        >
          {submitting ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>Validating &amp; Submitting…</span>
            </>
          ) : (
            <>
              <Send className="h-4 w-4" />
              <span>Submit Application</span>
            </>
          )}
        </button>
      </form>

      <CandidateFaqSection />
    </main>
  );
}
