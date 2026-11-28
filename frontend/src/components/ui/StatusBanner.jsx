import { AlertCircle, AlertTriangle, CheckCircle2, Info } from "lucide-react";

const STYLES = {
  success: {
    box: "border-emerald-300/60 bg-emerald-500/10 text-emerald-800 dark:text-emerald-200",
    icon: CheckCircle2,
    iconColor: "text-emerald-600 dark:text-emerald-400",
  },
  warning: {
    box: "border-amber-300/60 bg-amber-500/10 text-amber-900 dark:text-amber-200",
    icon: AlertTriangle,
    iconColor: "text-amber-600 dark:text-amber-400",
  },
  error: {
    box: "border-rose-300/60 bg-rose-500/10 text-rose-800 dark:text-rose-200",
    icon: AlertCircle,
    iconColor: "text-rose-600 dark:text-rose-400",
  },
  info: {
    box: "border-theme bg-[var(--bg-soft)] text-heading",
    icon: Info,
    iconColor: "text-[var(--brand-accent)]",
  },
};

export default function StatusBanner({ type = "info", children, className = "" }) {
  const cfg = STYLES[type] || STYLES.info;
  const Icon = cfg.icon;

  return (
    <div
      role={type === "error" ? "alert" : "status"}
      aria-live="polite"
      className={`flex items-start gap-2.5 rounded-xl border px-4 py-3 text-xs leading-relaxed sm:text-sm ${cfg.box} ${className}`}
    >
      <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${cfg.iconColor}`} />
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}
