import { Shield, X } from "lucide-react";
import { useState } from "react";

const DISMISS_KEY = "talentpulse_privacy_notice_dismissed";

export default function CookieNotice() {
  const [dismissed, setDismissed] = useState(() => {
    try {
      return localStorage.getItem(DISMISS_KEY) === "1";
    } catch {
      return false;
    }
  });

  if (dismissed) return null;

  const handleDismiss = () => {
    try {
      localStorage.setItem(DISMISS_KEY, "1");
    } catch {
      // Ignore storage errors
    }
    setDismissed(true);
  };

  return (
    <aside
      aria-label="Privacy and storage notice"
      className="no-print fixed bottom-4 left-4 right-4 z-30 mx-auto max-w-xl rounded-2xl border border-theme bg-[var(--bg-surface)] p-4 shadow-xl sm:left-6 sm:right-auto"
    >
      <div className="flex items-start gap-3">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg surface-soft">
          <Shield className="h-4 w-4" />
        </div>
        <div className="min-w-0 flex-1 text-xs leading-relaxed text-body">
          <strong className="font-semibold text-heading">Essential Storage Only:</strong>{" "}
          This portal uses browser storage strictly for your theme preference, OTP
          verification session, and recruiter authentication—no advertising or third-party
          tracking cookies.
        </div>
        <button
          type="button"
          onClick={handleDismiss}
          aria-label="Dismiss privacy notice"
          className="shrink-0 rounded-lg p-1.5 text-muted transition-colors hover:bg-[var(--bg-soft)] hover:text-heading"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </aside>
  );
}

