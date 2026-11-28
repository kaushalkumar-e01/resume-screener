import { Check, ChevronDown, Search } from "lucide-react";
import { memo, useEffect, useId, useMemo, useRef, useState } from "react";

function RoleCombobox({ roles, value, onChange, error }) {
  const inputId = useId();
  const listboxId = useId();
  const containerRef = useRef(null);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState(value || "");
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    setQuery(value || "");
  }, [value]);

  useEffect(() => {
    const handleOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpen(false);
        setQuery(value || "");
      }
    };
    document.addEventListener("mousedown", handleOutside);
    return () => document.removeEventListener("mousedown", handleOutside);
  }, [value]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q || (value && query === value)) return roles;
    return roles.filter((r) => r.toLowerCase().includes(q));
  }, [roles, query, value]);

  const selectRole = (role) => {
    onChange(role);
    setQuery(role);
    setOpen(false);
  };

  const handleKeyDown = (e) => {
    if (!open && (e.key === "ArrowDown" || e.key === "Enter")) {
      setOpen(true);
      return;
    }
    if (!open) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((prev) => Math.min(prev + 1, Math.max(0, filtered.length - 1)));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((prev) => Math.max(prev - 1, 0));
    } else if (e.key === "Enter" && filtered[activeIndex]) {
      e.preventDefault();
      selectRole(filtered[activeIndex]);
    } else if (e.key === "Escape") {
      setOpen(false);
      setQuery(value || "");
    }
  };

  return (
    <div ref={containerRef} className="relative min-w-0 space-y-1.5">
      <label htmlFor={inputId} className="block text-sm font-medium text-body">
        Target Position / Role <span className="text-[var(--brand-primary)]" aria-hidden="true">*</span>
      </label>

      <div className="relative">
        <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
        <input
          id={inputId}
          type="text"
          role="combobox"
          aria-expanded={open}
          aria-controls={listboxId}
          aria-autocomplete="list"
          aria-invalid={Boolean(error)}
          value={query}
          onFocus={() => setOpen(true)}
          onChange={(e) => {
            setQuery(e.target.value);
            setActiveIndex(0);
            setOpen(true);
            if (e.target.value === "") onChange("");
          }}
          onKeyDown={handleKeyDown}
          placeholder="Type to search or select a technical role…"
          className={`surface-input min-h-[46px] w-full rounded-xl py-2.5 pl-10 pr-10 text-sm transition-colors ${
            error ? "border-rose-400 focus:border-rose-500" : ""
          }`}
        />
        <button
          type="button"
          aria-label="Toggle role options"
          onClick={() => setOpen((o) => !o)}
          className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded-lg p-1 text-muted hover:bg-[var(--bg-soft)] hover:text-heading"
        >
          <ChevronDown className={`h-4 w-4 transition-transform ${open ? "rotate-180" : ""}`} />
        </button>
      </div>

      {open && (
        <ul
          id={listboxId}
          role="listbox"
          className="smooth-scroll absolute z-30 mt-1 max-h-64 w-full overflow-y-auto rounded-xl border border-theme bg-[var(--bg-surface)] p-1.5 shadow-xl"
        >
          {filtered.length === 0 ? (
            <li className="px-3 py-2.5 text-sm text-muted">
              No matching technical roles found.
            </li>
          ) : (
            filtered.map((role, idx) => {
              const selected = value === role;
              const highlighted = idx === activeIndex;
              return (
                <li
                  key={role}
                  role="option"
                  aria-selected={selected}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    selectRole(role);
                  }}
                  onMouseEnter={() => setActiveIndex(idx)}
                  className={`flex cursor-pointer items-center justify-between rounded-lg px-3 py-2 text-sm transition-colors ${
                    selected
                      ? "bg-[var(--bg-soft)] font-semibold text-[var(--brand-primary)]"
                      : highlighted
                        ? "bg-[var(--bg-canvas)] text-heading"
                        : "text-body hover:bg-[var(--bg-canvas)]"
                  }`}
                >
                  <span>{role}</span>
                  {selected && <Check className="h-4 w-4 text-emerald-600" />}
                </li>
              );
            })
          )}
        </ul>
      )}

      {error && (
        <p role="alert" className="text-xs font-medium text-rose-600">
          {error}
        </p>
      )}
    </div>
  );
}

export default memo(RoleCombobox);
