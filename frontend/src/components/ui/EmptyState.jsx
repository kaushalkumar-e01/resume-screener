export default function EmptyState({ icon: Icon, title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-theme bg-[var(--bg-subtle)] px-6 py-12 text-center">
      {Icon && (
        <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-theme surface-soft">
          <Icon className="h-6 w-6" />
        </div>
      )}
      <h3 className="mt-4 text-base font-semibold text-heading">{title}</h3>
      {description && (
        <p className="mt-1.5 max-w-md text-sm text-muted">{description}</p>
      )}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
