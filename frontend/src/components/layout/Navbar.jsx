import { Cpu, Home, Menu, Moon, ShieldCheck, Sun, Upload, X } from "lucide-react";
import { memo, useEffect, useState } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import {
  prefetchCandidateConfig,
  prefetchRecruiterDashboardIfAuthorized,
} from "../../services/api/prefetch";

const NAV_ITEMS = [
  { to: "/", label: "Overview", icon: Home, end: true },
  {
    to: "/candidate",
    label: "Candidate Portal",
    icon: Upload,
    end: false,
    onIntent: prefetchCandidateConfig,
  },
  {
    to: "/recruiter",
    label: "Recruiter Workspace",
    icon: ShieldCheck,
    end: false,
    onIntent: prefetchRecruiterDashboardIfAuthorized,
  },
];

function Navbar({ apiOnline, theme, onToggleTheme }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!mobileOpen) return;
    const onKeyDown = (e) => {
      if (e.key === "Escape") setMobileOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [mobileOpen]);

  return (
    <header className="no-print sticky top-0 z-40 border-b border-theme bg-[var(--bg-surface)]/95 shadow-xs">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
        <Link
          to="/"
          className="group flex min-w-0 items-center gap-2.5"
        >
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[var(--brand-primary)] text-white shadow-xs transition-colors group-hover:bg-[var(--brand-primary-hover)]">
            <Cpu className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <div className="truncate text-sm font-bold tracking-tight text-[var(--brand-primary)] sm:text-base">
              TalentPulse <span className="text-[var(--brand-accent)]">AI</span>
            </div>
            <div className="hidden text-xs font-medium text-muted sm:block">
              Resume Screening Intelligence
            </div>
          </div>
        </Link>

        {/* Desktop Nav */}
        <nav
          aria-label="Primary navigation"
          className="hidden items-center gap-1 rounded-xl border border-theme bg-[var(--bg-canvas)] p-1 md:flex"
        >
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                onMouseEnter={item.onIntent}
                onFocus={item.onIntent}
                className={({ isActive }) =>
                  `flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-[var(--brand-primary)] text-white shadow-xs"
                      : "text-body hover:bg-[var(--bg-soft)] hover:text-heading"
                  }`
                }
              >
                <Icon className="h-4 w-4 shrink-0" />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>

        <div className="flex items-center gap-2">
          <div
            className="hidden items-center gap-2 rounded-full border border-theme bg-[var(--bg-canvas)] px-3 py-1 text-xs font-medium lg:flex"
            title={
              apiOnline === true
                ? "FastAPI backend is reachable"
                : apiOnline === false
                  ? "FastAPI backend is unreachable"
                  : "Checking backend connection"
            }
          >
            <span
              className={`h-2 w-2 rounded-full ${
                apiOnline === true
                  ? "bg-emerald-600"
                  : apiOnline === false
                    ? "bg-rose-600"
                    : "bg-amber-500"
              }`}
            />
            <span className="text-body">
              {apiOnline === true
                ? "Engine Online"
                : apiOnline === false
                  ? "API Offline"
                  : "Connecting…"}
            </span>
          </div>

          <button
            type="button"
            onClick={onToggleTheme}
            aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
            title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
            className="flex h-9 w-9 items-center justify-center rounded-xl border border-theme bg-[var(--bg-canvas)] text-body transition-colors hover:bg-[var(--bg-soft)] hover:text-heading"
          >
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>

          <button
            type="button"
            onClick={() => setMobileOpen((o) => !o)}
            aria-expanded={mobileOpen}
            aria-controls="mobile-nav-menu"
            aria-label={mobileOpen ? "Close navigation menu" : "Open navigation menu"}
            className="flex h-9 w-9 items-center justify-center rounded-xl border border-theme bg-[var(--bg-canvas)] text-body transition-colors hover:bg-[var(--bg-soft)] md:hidden"
          >
            {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Nav Drawer */}
      {mobileOpen && (
        <nav
          id="mobile-nav-menu"
          aria-label="Mobile navigation"
          className="border-t border-theme bg-[var(--bg-surface)] px-4 py-3 md:hidden"
        >
          <div className="flex flex-col gap-1.5">
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  onFocus={item.onIntent}
                  className={({ isActive }) =>
                    `flex items-center gap-2.5 rounded-xl px-3.5 py-2.5 text-sm font-medium transition-colors ${
                      isActive
                        ? "bg-[var(--brand-primary)] text-white"
                        : "text-body hover:bg-[var(--bg-soft)]"
                    }`
                  }
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  <span>{item.label}</span>
                </NavLink>
              );
            })}
          </div>
        </nav>
      )}
    </header>
  );
}

export default memo(Navbar);
