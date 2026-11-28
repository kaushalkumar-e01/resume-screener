export default function VerdictBadge({ verdict, status }) {
  if (status && status !== "Success") {
    return (
      <span className="inline-flex items-center rounded-full border border-rose-300/60 bg-rose-500/10 px-2.5 py-0.5 text-xs font-medium text-rose-700 dark:text-rose-300">
        Failed
      </span>
    );
  }
  const v = (verdict || "").toLowerCase();
  if (v.includes("strong")) {
    return (
      <span className="inline-flex items-center rounded-full border border-emerald-300/60 bg-emerald-500/10 px-2.5 py-0.5 text-xs font-semibold text-emerald-700 dark:text-emerald-300">
        {verdict}
      </span>
    );
  }
  if (v.includes("consider")) {
    return (
      <span className="inline-flex items-center rounded-full border border-theme bg-[var(--bg-soft)] px-2.5 py-0.5 text-xs font-semibold text-[var(--brand-primary)]">
        {verdict}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center rounded-full border border-amber-300/60 bg-amber-500/10 px-2.5 py-0.5 text-xs font-medium text-amber-800 dark:text-amber-300">
      {verdict || "Unclassified"}
    </span>
  );
}
