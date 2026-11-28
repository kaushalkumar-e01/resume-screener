import { Check, Copy, AlertCircle } from "lucide-react";
import { useEffect, useRef, useState } from "react";

export default function CopyButton({ text, label = "Copy", className = "" }) {
  const [status, setStatus] = useState("idle"); // idle | copied | error
  const timerRef = useRef(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  const handleCopy = async () => {
    if (!text) return;
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
      } else {
        const el = document.createElement("textarea");
        el.value = text;
        el.setAttribute("readonly", "");
        el.style.position = "fixed";
        el.style.opacity = "0";
        document.body.appendChild(el);
        el.select();
        const ok = document.execCommand("copy");
        document.body.removeChild(el);
        if (!ok) throw new Error("Copy failed");
      }
      setStatus("copied");
    } catch {
      setStatus("error");
    }
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => setStatus("idle"), 1800);
  };

  return (
    <button
      type="button"
      onClick={handleCopy}
      aria-label={label}
      title={label}
      className={`no-print inline-flex items-center gap-1 rounded-lg border border-theme bg-[var(--bg-surface)] px-2 py-1 text-xs font-medium text-muted transition-colors hover:border-[var(--brand-accent)] hover:text-[var(--brand-primary)] ${className}`}
    >
      {status === "copied" ? (
        <>
          <Check className="h-3 w-3 text-emerald-600" />
          <span className="text-emerald-600">Copied</span>
        </>
      ) : status === "error" ? (
        <>
          <AlertCircle className="h-3 w-3 text-rose-600" />
          <span className="text-rose-600">Failed</span>
        </>
      ) : (
        <>
          <Copy className="h-3 w-3" />
          <span>{label}</span>
        </>
      )}
    </button>
  );
}

