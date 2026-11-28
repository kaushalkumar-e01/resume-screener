export function SkeletonCard() {
  return (
    <div className="surface-card rounded-2xl p-5">
      <div className="h-3 w-24 rounded bg-[var(--bg-soft)]" />
      <div className="mt-3 h-8 w-16 rounded bg-[var(--bg-soft)] opacity-70" />
    </div>
  );
}

export function SkeletonTable() {
  return (
    <div className="space-y-3 rounded-xl border border-theme bg-[var(--bg-subtle)] p-4">
      {[0, 1, 2, 3].map((row) => (
        <div key={row} className="flex items-center justify-between gap-4">
          <div className="h-4 w-1/4 rounded bg-[var(--bg-soft)]" />
          <div className="h-4 w-1/5 rounded bg-[var(--bg-soft)] opacity-80" />
          <div className="h-3 w-28 rounded-full bg-[var(--bg-soft)]" />
          <div className="h-5 w-20 rounded-full bg-[var(--bg-soft)] opacity-80" />
        </div>
      ))}
    </div>
  );
}
