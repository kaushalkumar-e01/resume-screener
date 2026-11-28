import {
  Bot,
  ChevronDown,
  Download,
  FileUp,
  Loader2,
  LogOut,
  Printer,
  Search,
  Sparkles,
  Trash2,
  Users,
} from "lucide-react";
import { memo, useCallback, useEffect, useMemo, useState } from "react";
import ConfirmDialog from "../../components/ui/ConfirmDialog";
import CopyButton from "../../components/ui/CopyButton";
import EmptyState from "../../components/ui/EmptyState";
import { SkeletonCard, SkeletonTable } from "../../components/ui/Skeleton";
import StatusBanner from "../../components/ui/StatusBanner";
import VerdictBadge from "../../components/ui/VerdictBadge";
import { useDocumentMeta } from "../../hooks/useDocumentMeta";
import {
  getRecruiterDashboardCached,
  invalidatePrefetch,
} from "../../services/api/prefetch";
import { recruiterApi } from "../../services/api/recruiterApi";
import RecruiterLoginPage from "./RecruiterLoginPage";

const TOKEN_KEY = "ai_screener_recruiter_token";

const LeaderboardRow = memo(function LeaderboardRow({ item, onSelect }) {
  return (
    <tr
      onClick={() => onSelect(item.id)}
      className="cursor-pointer transition-colors hover:bg-[var(--bg-soft)]/45"
    >
      <td data-label="Candidate" className="px-4 py-3 font-medium text-heading">
        {item.name}
      </td>
      <td data-label="Role" className="px-4 py-3 text-body">
        {item.target_role}
      </td>
      <td data-label="Match Score" className="px-4 py-3">
        <div className="flex items-center gap-2.5">
          <div className="h-2 w-24 overflow-hidden rounded-full bg-[var(--bg-soft)]">
            <div
              className="h-full rounded-full bg-[var(--brand-primary)]"
              style={{ width: `${Math.min(100, Math.max(0, item.match_score))}%` }}
            />
          </div>
          <span className="text-xs font-semibold text-[var(--brand-primary)]">
            {item.match_score}%
          </span>
        </div>
      </td>
      <td data-label="Verdict" className="px-4 py-3">
        <VerdictBadge verdict={item.recommendation} status={item.screening_status} />
      </td>
      <td data-label="Experience" className="px-4 py-3 text-xs text-muted">
        {item.estimated_experience_years != null
          ? `${item.estimated_experience_years} yrs`
          : "—"}
      </td>
      <td data-label="Resume" className="px-4 py-3 text-xs text-muted">
        <span className="block max-w-[180px] truncate">{item.original_filename}</span>
      </td>
    </tr>
  );
});

const AssessmentCard = memo(function AssessmentCard({ item, rank, isOpen, onToggle }) {
  const reportText = [
    `Candidate: ${item.name}`,
    `Role: ${item.target_role}`,
    `Match Score: ${item.match_score}% (${item.recommendation})`,
    `Matching Skills: ${(item.matching_skills || []).join(", ") || "None"}`,
    `Missing Skills: ${(item.missing_skills || []).join(", ") || "None"}`,
    `Assessment: ${item.justification}`,
  ].join("\n");

  return (
    <div className="overflow-hidden rounded-xl border border-theme bg-[var(--bg-surface)]">
      <button
        type="button"
        aria-expanded={isOpen}
        onClick={() => onToggle(item.id)}
        className="flex w-full items-center justify-between gap-3 px-4 py-3.5 text-left transition-colors hover:bg-[var(--bg-soft)]/40"
      >
        <div className="flex min-w-0 flex-wrap items-center gap-2.5">
          <span className="text-xs font-semibold text-[var(--brand-accent)]">#{rank}</span>
          <span className="font-semibold text-heading">{item.name}</span>
          <span className="text-xs font-semibold text-[var(--brand-primary)]">
            {item.match_score}%
          </span>
          <VerdictBadge verdict={item.recommendation} status={item.screening_status} />
        </div>
        <ChevronDown
          className={`h-4 w-4 shrink-0 text-muted transition-transform ${
            isOpen ? "rotate-180" : ""
          }`}
        />
      </button>

      {isOpen && (
        <div className="space-y-4 border-t border-theme bg-[var(--bg-subtle)] px-4 py-4 text-sm">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="print-confidential flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted">
              <span className="inline-flex items-center gap-1.5">
                <strong className="text-heading">Email:</strong> {item.email}
                <CopyButton text={item.email} label="Copy" />
              </span>
              {item.phone && (
                <span className="inline-flex items-center gap-1.5">
                  <strong className="text-heading">Phone:</strong> {item.phone}
                  <CopyButton text={item.phone} label="Copy" />
                </span>
              )}
            </div>
            <div className="flex items-center gap-3 text-xs text-muted">
              {item.screened_at && <span>Screened: {item.screened_at}</span>}
              <CopyButton text={reportText} label="Copy Summary" />
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <div className="mb-1.5 text-xs font-semibold text-emerald-700 dark:text-emerald-400 uppercase">
                Matching Skills
              </div>
              <div className="flex flex-wrap gap-1.5">
                {item.matching_skills?.length ? (
                  item.matching_skills.map((s) => (
                    <span
                      key={s}
                      className="rounded-lg border border-emerald-300/60 bg-emerald-500/10 px-2.5 py-1 text-xs text-emerald-800 dark:text-emerald-200"
                    >
                      {s}
                    </span>
                  ))
                ) : (
                  <span className="text-xs text-muted">None identified</span>
                )}
              </div>
            </div>

            <div>
              <div className="mb-1.5 text-xs font-semibold text-amber-700 dark:text-amber-400 uppercase">
                Missing Skills / Gaps
              </div>
              <div className="flex flex-wrap gap-1.5">
                {item.missing_skills?.length ? (
                  item.missing_skills.map((s) => (
                    <span
                      key={s}
                      className="rounded-lg border border-amber-300/60 bg-amber-500/10 px-2.5 py-1 text-xs text-amber-800 dark:text-amber-200"
                    >
                      {s}
                    </span>
                  ))
                ) : (
                  <span className="text-xs text-muted">None identified</span>
                )}
              </div>
            </div>
          </div>

          <div>
            <div className="mb-1 text-xs font-semibold text-muted uppercase">
              AI Assessment
            </div>
            <p className="leading-relaxed text-body">{item.justification}</p>
          </div>
        </div>
      )}
    </div>
  );
});

export default function RecruiterDashboardPage() {
  useDocumentMeta({
    title: "Recruiter Workspace",
    description:
      "Manage candidate applications, run Gemini AI resume screening, and inspect ranked match results.",
  });

  const [token, setToken] = useState(() => sessionStorage.getItem(TOKEN_KEY) || "");
  const [checkingSession, setCheckingSession] = useState(Boolean(token));

  const [data, setData] = useState(null);
  const [loadingDash, setLoadingDash] = useState(false);
  const [jobDescription, setJobDescription] = useState("");
  const [selectedCandidateId, setSelectedCandidateId] = useState("");
  const [expandedId, setExpandedId] = useState(null);
  const [confirmClearAll, setConfirmClearAll] = useState(false);
  const [confirmDeleteOne, setConfirmDeleteOne] = useState(false);

  const [searchQuery, setSearchQuery] = useState("");
  const [verdictFilter, setVerdictFilter] = useState("all");
  const [sortBy, setSortBy] = useState("score_desc");

  const [uploading, setUploading] = useState(false);
  const [screening, setScreening] = useState(false);
  const [banner, setBanner] = useState(null);

  const loadDashboard = useCallback(async (authToken, forceFresh = false) => {
    setLoadingDash(true);
    try {
      if (forceFresh) {
        invalidatePrefetch();
      }
      const res = await getRecruiterDashboardCached(authToken);
      setData(res);
      if (res?.results?.length) {
        setExpandedId((prev) => prev || res.results[0].id);
      }
    } catch (err) {
      if (err.status === 401) {
        sessionStorage.removeItem(TOKEN_KEY);
        setToken("");
      } else {
        setBanner({ type: "error", text: err.message });
      }
    } finally {
      setLoadingDash(false);
    }
  }, []);

  useEffect(() => {
    if (!token) {
      setCheckingSession(false);
      return;
    }
    recruiterApi
      .checkSession(token)
      .then(() => loadDashboard(token))
      .catch(() => {
        sessionStorage.removeItem(TOKEN_KEY);
        setToken("");
      })
      .finally(() => setCheckingSession(false));
  }, [token, loadDashboard]);

  const handleAuthenticated = useCallback((newToken) => {
    sessionStorage.setItem(TOKEN_KEY, newToken);
    setToken(newToken);
  }, []);

  const handleLogout = async () => {
    try {
      await recruiterApi.logout(token);
    } catch {
      // Ignore logout failure
    }
    invalidatePrefetch();
    sessionStorage.removeItem(TOKEN_KEY);
    setToken("");
    setData(null);
  };

  const handleBatchUpload = async (filesList) => {
    const files = Array.from(filesList || []);
    if (!files.length) return;
    setUploading(true);
    setBanner(null);
    try {
      const res = await recruiterApi.uploadResumes(token, files);
      const notes = [];
      if (res.added) notes.push(`Stored ${res.added} new resume(s).`);
      if (res.skipped?.length) notes.push(`Skipped ${res.skipped.length} duplicate(s).`);
      if (res.errors?.length) notes.push(res.errors.join(" "));
      setBanner({
        type: res.errors?.length && !res.added ? "error" : "success",
        text: notes.join(" ") || "Upload complete.",
      });
      await loadDashboard(token, true);
    } catch (err) {
      setBanner({ type: "error", text: err.message });
    } finally {
      setUploading(false);
    }
  };

  const handleDeleteSelected = async () => {
    setConfirmDeleteOne(false);
    if (!selectedCandidateId) return;
    setBanner(null);
    try {
      await recruiterApi.deleteCandidate(token, selectedCandidateId);
      setSelectedCandidateId("");
      setBanner({ type: "success", text: "Candidate record and resume deleted." });
      await loadDashboard(token, true);
    } catch (err) {
      setBanner({ type: "error", text: err.message });
    }
  };

  const handleDeleteAll = async () => {
    setConfirmClearAll(false);
    setBanner(null);
    try {
      await recruiterApi.deleteAllCandidates(token);
      setSelectedCandidateId("");
      setBanner({ type: "success", text: "All candidate records and resumes removed." });
      await loadDashboard(token, true);
    } catch (err) {
      setBanner({ type: "error", text: err.message });
    }
  };

  const handleRunScreening = async () => {
    if (jobDescription.trim().length < 30) {
      setBanner({ type: "error", text: "Job Description must contain at least 30 characters." });
      return;
    }
    setScreening(true);
    setBanner(null);
    try {
      const res = await recruiterApi.runScreening(token, jobDescription);
      setBanner({
        type: res.failed > 0 && res.successful === 0 ? "error" : "success",
        text: `Screening complete: ${res.successful} succeeded, ${res.failed} failed out of ${res.total}.`,
      });
      await loadDashboard(token, true);
    } catch (err) {
      setBanner({ type: "error", text: err.message });
    } finally {
      setScreening(false);
    }
  };

  const handleToggleRow = useCallback((id) => {
    setExpandedId((prev) => (prev === id ? null : id));
  }, []);

  const results = useMemo(() => data?.results || [], [data]);
  const candidates = useMemo(() => data?.candidates || [], [data]);

  const verdictCounts = useMemo(() => {
    const counts = { strong: 0, consider: 0, reject: 0 };
    results.forEach((r) => {
      const v = (r.recommendation || "").toLowerCase();
      if (v.includes("strong")) counts.strong += 1;
      else if (v.includes("consider")) counts.consider += 1;
      else counts.reject += 1;
    });
    return counts;
  }, [results]);

  const filteredResults = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    const list = results.filter((r) => {
      const matchesQuery =
        !q ||
        r.name?.toLowerCase().includes(q) ||
        r.target_role?.toLowerCase().includes(q) ||
        r.email?.toLowerCase().includes(q) ||
        r.original_filename?.toLowerCase().includes(q);
      const v = (r.recommendation || "").toLowerCase();
      const matchesVerdict =
        verdictFilter === "all" ||
        (verdictFilter === "strong" && v.includes("strong")) ||
        (verdictFilter === "consider" && v.includes("consider")) ||
        (verdictFilter === "reject" && !v.includes("strong") && !v.includes("consider"));
      return matchesQuery && matchesVerdict;
    });

    return [...list].sort((a, b) => {
      if (sortBy === "score_asc") return a.match_score - b.match_score;
      if (sortBy === "name_asc") return (a.name || "").localeCompare(b.name || "");
      if (sortBy === "exp_desc") {
        return (b.estimated_experience_years ?? -1) - (a.estimated_experience_years ?? -1);
      }
      return b.match_score - a.match_score;
    });
  }, [results, searchQuery, verdictFilter, sortBy]);

  const exportCsv = () => {
    if (!filteredResults.length) return;
    const headers = ["Candidate", "Role", "Score", "Verdict", "Experience", "Resume", "Screened At"];
    const rows = filteredResults.map((r) => [
      r.name,
      r.target_role,
      `${r.match_score}%`,
      r.recommendation,
      r.estimated_experience_years != null ? `${r.estimated_experience_years} yrs` : "—",
      r.original_filename,
      r.screened_at,
    ]);
    const csv = [headers, ...rows]
      .map((row) => row.map((cell) => `"${String(cell ?? "").replace(/"/g, '""')}"`).join(","))
      .join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "candidate_leaderboard.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  if (checkingSession) {
    return (
      <main id="main-content" tabIndex={-1} className="mx-auto flex max-w-md items-center justify-center px-4 py-24">
        <div className="flex items-center gap-3 text-body">
          <Loader2 className="h-5 w-5 animate-spin text-[var(--brand-primary)]" />
          <span>Verifying recruiter session…</span>
        </div>
      </main>
    );
  }

  if (!token) {
    return <RecruiterLoginPage onAuthenticated={handleAuthenticated} />;
  }

  const stats = data?.stats || { total: 0, screened: 0, top_score: null, average_score: null };
  const wordCount = jobDescription.trim() ? jobDescription.trim().split(/\s+/).length : 0;
  const selectedCandidate = candidates.find((c) => c.id === selectedCandidateId);

  return (
    <main id="main-content" tabIndex={-1} className="mx-auto max-w-7xl space-y-6 px-4 pb-20 pt-8 sm:space-y-8 sm:px-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-2xl font-bold tracking-tight text-heading sm:text-3xl">
            Recruiter Command Center
          </h1>
          <p className="mt-1 text-sm text-muted">
            Persistent applicant management and Gemini structured resume intelligence.
          </p>
        </div>
        <div className="no-print flex flex-wrap items-center gap-3">
          <span className="inline-flex items-center gap-2 rounded-full border border-emerald-300/60 bg-emerald-500/10 px-3 py-1.5 text-xs font-medium text-emerald-700 dark:text-emerald-300">
            <span className="h-2 w-2 rounded-full bg-emerald-600" />
            Secure Session
          </span>
          <button
            type="button"
            onClick={handleLogout}
            className="inline-flex items-center gap-1.5 rounded-xl border border-theme bg-[var(--bg-surface)] px-3.5 py-2 text-xs font-medium text-body transition-colors hover:border-rose-300 hover:text-rose-600"
          >
            <LogOut className="h-3.5 w-3.5" />
            <span>Logout</span>
          </button>
        </div>
      </div>

      {banner && <StatusBanner type={banner.type} className="no-print">{banner.text}</StatusBanner>}

      {/* KPI Cards */}
      <section className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {loadingDash && !data ? (
          [0, 1, 2, 3].map((i) => <SkeletonCard key={i} />)
        ) : (
          [
            { label: "Total Applicants", value: stats.total, accent: "text-heading" },
            { label: "Screened", value: stats.screened, accent: "text-[var(--brand-primary)]" },
            {
              label: "Top Match",
              value: stats.top_score != null ? `${stats.top_score}%` : "—",
              accent: "text-emerald-600 dark:text-emerald-400",
            },
            {
              label: "Average Score",
              value: stats.average_score != null ? `${stats.average_score}%` : "—",
              accent: "text-[var(--brand-accent)]",
            },
          ].map((kpi) => (
            <div key={kpi.label} className="surface-card rounded-2xl p-4 sm:p-5">
              <div className="text-xs font-medium tracking-wide text-muted uppercase">
                {kpi.label}
              </div>
              <div className={`mt-2 text-2xl font-bold sm:text-3xl ${kpi.accent}`}>
                {kpi.value}
              </div>
            </div>
          ))
        )}
      </section>

      {/* Verdict Distribution Bar */}
      {results.length > 0 && (
        <section className="surface-card rounded-2xl p-5">
          <div className="mb-2.5 flex flex-wrap items-center justify-between gap-2 text-xs font-medium">
            <span className="text-muted uppercase tracking-wider">Verdict Distribution</span>
            <div className="flex flex-wrap items-center gap-4">
              <span className="text-emerald-700 dark:text-emerald-400">Strong Hire: {verdictCounts.strong}</span>
              <span className="text-[var(--brand-primary)]">Consider: {verdictCounts.consider}</span>
              <span className="text-amber-700 dark:text-amber-400">Reject / Other: {verdictCounts.reject}</span>
            </div>
          </div>
          <div className="flex h-2.5 w-full overflow-hidden rounded-full bg-[var(--bg-soft)]">
            <div
              className="bg-emerald-600 transition-all duration-300"
              style={{ width: `${(verdictCounts.strong / results.length) * 100}%` }}
            />
            <div
              className="bg-[var(--brand-primary)] transition-all duration-300"
              style={{ width: `${(verdictCounts.consider / results.length) * 100}%` }}
            />
            <div
              className="bg-amber-500 transition-all duration-300"
              style={{ width: `${(verdictCounts.reject / results.length) * 100}%` }}
            />
          </div>
        </section>
      )}

      {/* JD + Upload */}
      <section className="no-print grid gap-6 lg:grid-cols-2">
        <div className="surface-card flex min-w-0 flex-col rounded-2xl p-5 sm:p-6">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-base font-semibold text-heading">1. Job Description</h2>
            <button
              type="button"
              onClick={() => data?.sample_jd && setJobDescription(data.sample_jd)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-theme surface-soft px-3 py-1.5 text-xs font-medium transition-opacity hover:opacity-90"
            >
              <Sparkles className="h-3.5 w-3.5 text-[var(--brand-accent)]" />
              <span>Load Sample JD</span>
            </button>
          </div>
          <textarea
            rows={10}
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
            placeholder="Paste the target role requirements and responsibilities…"
            className="surface-input w-full flex-1 rounded-xl p-3.5 text-sm leading-relaxed"
          />
          <div className="mt-2 text-xs text-muted">
            {wordCount} words · {jobDescription.length} characters
          </div>
        </div>

        <div className="surface-card flex min-w-0 flex-col justify-between rounded-2xl p-5 sm:p-6">
          <div>
            <h2 className="text-base font-semibold text-heading">2. Manual Resume Upload</h2>
            <p className="mt-1 text-xs leading-relaxed text-muted">
              Portal applications appear automatically. Upload external PDFs in batch here.
            </p>
            <label className="mt-4 flex cursor-pointer flex-col items-center justify-center rounded-2xl border border-dashed border-[var(--border-input)] bg-[var(--bg-canvas)] px-4 py-12 text-center transition-colors hover:border-[var(--brand-primary)] hover:bg-[var(--bg-soft)]/50 sm:px-6">
              {uploading ? (
                <Loader2 className="h-8 w-8 animate-spin text-[var(--brand-primary)]" />
              ) : (
                <FileUp className="h-8 w-8 text-[var(--brand-accent)]" />
              )}
              <span className="mt-3 text-sm font-medium text-heading">
                {uploading ? "Uploading PDFs…" : "Select one or more PDF resumes"}
              </span>
              <span className="mt-1 text-xs text-muted">Duplicates are skipped automatically</span>
              <input
                type="file"
                accept=".pdf,application/pdf"
                multiple
                className="sr-only"
                onChange={(e) => handleBatchUpload(e.target.files)}
              />
            </label>
          </div>

          <button
            type="button"
            onClick={handleRunScreening}
            disabled={screening || candidates.length === 0}
            className="mt-6 inline-flex min-h-[48px] w-full items-center justify-center gap-2 rounded-xl bg-[var(--brand-primary)] px-5 py-3 text-sm font-semibold text-white shadow-xs transition-colors hover:bg-[var(--brand-primary-hover)] disabled:opacity-50"
          >
            {screening ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Running Gemini AI Screening…</span>
              </>
            ) : (
              <>
                <Bot className="h-4 w-4" />
                <span>Run AI Screening ({candidates.length} stored)</span>
              </>
            )}
          </button>
        </div>
      </section>

      {/* Candidate Management */}
      {candidates.length > 0 && (
        <section className="no-print surface-card rounded-2xl p-5 sm:p-6">
          <div className="mb-4 flex items-center gap-2 text-base font-semibold text-heading">
            <Users className="h-4 w-4 text-[var(--brand-primary)]" />
            <h2>Candidate Management ({candidates.length})</h2>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <select
              aria-label="Select candidate to delete"
              value={selectedCandidateId}
              onChange={(e) => setSelectedCandidateId(e.target.value)}
              className="surface-input min-h-[44px] min-w-0 flex-1 rounded-xl px-3.5 py-2 text-sm"
            >
              <option value="">Choose a candidate to remove…</option>
              {candidates.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} · {c.target_role} ({c.original_filename})
                </option>
              ))}
            </select>

            <button
              type="button"
              disabled={!selectedCandidateId}
              onClick={() => setConfirmDeleteOne(true)}
              className="inline-flex min-h-[44px] shrink-0 items-center justify-center gap-1.5 rounded-xl border border-theme bg-[var(--bg-surface)] px-4 py-2 text-xs font-medium text-body transition-colors hover:border-rose-400 hover:text-rose-600 disabled:opacity-40"
            >
              <Trash2 className="h-4 w-4" />
              <span>Delete Selected</span>
            </button>

            <button
              type="button"
              onClick={() => setConfirmClearAll(true)}
              className="inline-flex min-h-[44px] shrink-0 items-center justify-center gap-1.5 rounded-xl border border-rose-300/60 bg-rose-500/10 px-4 py-2 text-xs font-semibold text-rose-700 dark:text-rose-300 transition-colors hover:bg-rose-500/20"
            >
              <Trash2 className="h-4 w-4" />
              <span>Delete All</span>
            </button>
          </div>
        </section>
      )}

      {/* Leaderboard */}
      <section className="surface-card min-w-0 rounded-2xl p-5 sm:p-6">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-semibold text-heading">Candidate Leaderboard</h2>
          {filteredResults.length > 0 && (
            <div className="no-print flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => window.print()}
                className="inline-flex items-center gap-1.5 rounded-xl border border-theme bg-[var(--bg-surface)] px-3.5 py-2 text-xs font-medium text-body transition-colors hover:bg-[var(--bg-soft)]"
              >
                <Printer className="h-3.5 w-3.5" />
                <span>Print Report</span>
              </button>
              <button
                type="button"
                onClick={exportCsv}
                className="inline-flex items-center gap-1.5 rounded-xl border border-theme bg-[var(--bg-surface)] px-3.5 py-2 text-xs font-medium text-[var(--brand-primary)] transition-colors hover:bg-[var(--bg-soft)]"
              >
                <Download className="h-3.5 w-3.5" />
                <span>Export CSV</span>
              </button>
            </div>
          )}
        </div>

        {results.length > 0 && (
          <div className="no-print mb-4 grid gap-3 sm:grid-cols-3">
            <div className="relative min-w-0">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
              <input
                type="search"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search name, role, email…"
                aria-label="Search candidates"
                className="surface-input min-h-[42px] w-full rounded-xl pl-9 pr-3 text-sm"
              />
            </div>

            <select
              aria-label="Filter by verdict"
              value={verdictFilter}
              onChange={(e) => setVerdictFilter(e.target.value)}
              className="surface-input min-h-[42px] w-full rounded-xl px-3 text-sm"
            >
              <option value="all">All Verdicts</option>
              <option value="strong">Strong Hire</option>
              <option value="consider">Consider</option>
              <option value="reject">Reject / Other</option>
            </select>

            <select
              aria-label="Sort results"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="surface-input min-h-[42px] w-full rounded-xl px-3 text-sm"
            >
              <option value="score_desc">Sort: Highest Match Score</option>
              <option value="score_asc">Sort: Lowest Match Score</option>
              <option value="exp_desc">Sort: Most Experience</option>
              <option value="name_asc">Sort: Candidate Name (A–Z)</option>
            </select>
          </div>
        )}

        {loadingDash && !data ? (
          <SkeletonTable />
        ) : results.length === 0 ? (
          <EmptyState
            icon={Bot}
            title="No AI Screening Results Yet"
            description="Add a Job Description above and click Run AI Screening to evaluate stored candidates."
          />
        ) : filteredResults.length === 0 ? (
          <EmptyState
            icon={Search}
            title="No Matching Candidates"
            description="Try adjusting your search query or verdict filter."
          />
        ) : (
          <>
            <div
              tabIndex={0}
              role="region"
              aria-label="Candidate leaderboard"
              className="table-wrapper rounded-xl border border-theme"
            >
              <table className="leaderboard-table text-left text-sm">
                <thead>
                  <tr className="border-b border-theme text-xs font-semibold tracking-wider text-muted uppercase">
                    <th className="px-4 py-3">Candidate</th>
                    <th className="px-4 py-3">Role</th>
                    <th className="px-4 py-3">Match Score</th>
                    <th className="px-4 py-3">Verdict</th>
                    <th className="px-4 py-3">Experience</th>
                    <th className="px-4 py-3">Resume</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border-color)]">
                  {filteredResults.map((r) => (
                    <LeaderboardRow key={r.id} item={r} onSelect={handleToggleRow} />
                  ))}
                </tbody>
              </table>
            </div>

            <div className="mt-6 space-y-3">
              <h3 className="text-sm font-semibold tracking-wide text-muted uppercase">
                Detailed AI Assessments
              </h3>
              {filteredResults.map((r, idx) => (
                <AssessmentCard
                  key={r.id}
                  item={r}
                  rank={idx + 1}
                  isOpen={expandedId === r.id}
                  onToggle={handleToggleRow}
                />
              ))}
            </div>
          </>
        )}
      </section>

      <ConfirmDialog
        open={confirmDeleteOne}
        title="Delete Candidate?"
        message={`This will permanently delete ${selectedCandidate?.name || "this candidate"}'s record, uploaded PDF resume, and AI evaluation.`}
        confirmLabel="Delete Candidate"
        onConfirm={handleDeleteSelected}
        onCancel={() => setConfirmDeleteOne(false)}
      />

      <ConfirmDialog
        open={confirmClearAll}
        title="Delete All Candidates?"
        message="This will permanently delete all candidate records, uploaded PDF resumes, and AI screening evaluations from the database."
        confirmLabel="Delete All Records"
        onConfirm={handleDeleteAll}
        onCancel={() => setConfirmClearAll(false)}
      />
    </main>
  );
}
