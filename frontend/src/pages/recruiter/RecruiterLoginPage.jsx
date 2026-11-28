import { ArrowLeft, Eye, EyeOff, Loader2, Lock } from "lucide-react";
import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import StatusBanner from "../../components/ui/StatusBanner";
import { useDocumentMeta } from "../../hooks/useDocumentMeta";
import { recruiterApi } from "../../services/api/recruiterApi";

export default function RecruiterLoginPage({ onAuthenticated }) {
  useDocumentMeta({
    title: "Recruiter Sign In",
    description: "Sign in to access the TalentPulse AI Recruiter Command Center.",
  });
  const passwordInputRef = useRef(null);
  const [userId, setUserId] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loginError, setLoginError] = useState("");
  const [loggingIn, setLoggingIn] = useState(false);

  const togglePasswordVisibility = () => {
    const input = passwordInputRef.current;
    const selStart = input?.selectionStart ?? null;
    const selEnd = input?.selectionEnd ?? null;

    setShowPassword((prev) => !prev);

    requestAnimationFrame(() => {
      if (passwordInputRef.current) {
        passwordInputRef.current.focus({ preventScroll: true });
        if (selStart !== null && selEnd !== null) {
          try {
            passwordInputRef.current.setSelectionRange(selStart, selEnd);
          } catch {
            // Ignore selection errors
          }
        }
      }
    });
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoginError("");
    setLoggingIn(true);
    try {
      const res = await recruiterApi.login(userId, password);
      onAuthenticated(res.token);
      setPassword("");
    } catch (err) {
      setLoginError(err.message);
    } finally {
      setLoggingIn(false);
    }
  };

  return (
    <main id="main-content" tabIndex={-1} className="mx-auto max-w-md px-4 pb-20 pt-12 sm:px-6">
      <div className="surface-card rounded-2xl p-6 sm:p-8">
        <div className="mb-6 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl border border-theme surface-soft">
            <Lock className="h-6 w-6" />
          </div>
          <h1 className="mt-4 text-2xl font-bold text-heading">Recruiter Sign In</h1>
          <p className="mt-1.5 text-xs text-muted">
            Authorized access only. Credentials are validated server-side.
          </p>
        </div>

        <form onSubmit={handleLogin} className="space-y-4">
          <div className="space-y-1.5">
            <label htmlFor="recruiter-user" className="block text-sm font-medium text-body">
              User ID
            </label>
            <input
              id="recruiter-user"
              type="text"
              autoComplete="username"
              required
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              className="surface-input min-h-[44px] w-full rounded-xl px-3.5 py-2 text-sm"
            />
          </div>

          <div className="space-y-1.5">
            <label htmlFor="recruiter-pass" className="block text-sm font-medium text-body">
              Password
            </label>
            <div className="relative">
              <input
                ref={passwordInputRef}
                id="recruiter-pass"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="surface-input min-h-[44px] w-full rounded-xl py-2 pl-3.5 pr-11 text-sm"
              />
              <button
                type="button"
                aria-label={showPassword ? "Hide password" : "Show password"}
                aria-pressed={showPassword}
                onMouseDown={(e) => e.preventDefault()}
                onClick={togglePasswordVisibility}
                className="absolute right-1.5 top-1/2 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-lg text-muted transition-colors hover:bg-[var(--bg-soft)] hover:text-heading"
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          {loginError && <StatusBanner type="error">{loginError}</StatusBanner>}

          <button
            type="submit"
            disabled={loggingIn}
            className="inline-flex min-h-[46px] w-full items-center justify-center gap-2 rounded-xl bg-[var(--brand-primary)] px-5 py-2.5 text-sm font-semibold text-white shadow-xs transition-colors hover:bg-[var(--brand-primary-hover)] disabled:opacity-60"
          >
            {loggingIn && <Loader2 className="h-4 w-4 animate-spin" />}
            <span>Sign In Securely</span>
          </button>
        </form>

        <Link
          to="/"
          className="mt-5 inline-flex w-full items-center justify-center gap-1.5 text-xs font-medium text-muted hover:text-heading"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>Back to Overview</span>
        </Link>
      </div>
    </main>
  );
}
