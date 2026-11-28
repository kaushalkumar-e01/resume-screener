import { useEffect, useState } from "react";
import { Link, Outlet, useLocation } from "react-router-dom";
import { useTheme } from "../../hooks/useTheme";
import { candidateApi } from "../../services/api/candidateApi";
import BackToTopButton from "../ui/BackToTopButton";
import CookieNotice from "../ui/CookieNotice";
import ScrollProgressBar from "../ui/ScrollProgressBar";
import AnimatedBackground from "./AnimatedBackground";
import Navbar from "./Navbar";

export default function AppLayout() {
  const [apiOnline, setApiOnline] = useState(null);
  const { theme, toggleTheme } = useTheme();
  const location = useLocation();
  const showScrollProgress =
    location.pathname.startsWith("/candidate") ||
    location.pathname.startsWith("/recruiter");

  useEffect(() => {
    let active = true;
    const check = () => {
      candidateApi
        .health()
        .then(() => active && setApiOnline(true))
        .catch(() => active && setApiOnline(false));
    };
    check();
    const timer = setInterval(check, 30000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, []);

  return (
    <div className="relative flex min-h-screen flex-col text-body">
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>
      {showScrollProgress && <ScrollProgressBar />}
      <AnimatedBackground />
      <Navbar apiOnline={apiOnline} theme={theme} onToggleTheme={toggleTheme} />
      <div className="flex-1 min-w-0">
        <Outlet />
      </div>
      <footer className="border-t border-theme bg-[var(--bg-surface)]/80 px-4 py-5 text-xs text-muted">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3">
          <span>TalentPulse AI · Structured Gemini Resume Screening</span>
          <div className="flex items-center gap-4">
            <Link to="/privacy" className="hover:text-heading hover:underline">
              Privacy Policy
            </Link>
            <Link to="/terms" className="hover:text-heading hover:underline">
              Terms &amp; Conditions
            </Link>
          </div>
        </div>
      </footer>
      <BackToTopButton />
      <CookieNotice />
    </div>
  );
}
