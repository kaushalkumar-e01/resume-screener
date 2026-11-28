import { memo, useId, useRef } from "react";

const COUNTRY_RULES = [
  { region: "IN", flag: "🇮🇳", dial: "+91", name: "India", max: 10, placeholder: "98765 43210", groups: [5, 5] },
  { region: "US", flag: "🇺🇸", dial: "+1", name: "United States", max: 10, placeholder: "(415) 555-0123", usStyle: true },
  { region: "GB", flag: "🇬🇧", dial: "+44", name: "United Kingdom", max: 10, placeholder: "7911 123456", groups: [4, 6] },
  { region: "AU", flag: "🇦🇺", dial: "+61", name: "Australia", max: 9, placeholder: "412 345 678", groups: [3, 3, 3] },
  { region: "SG", flag: "🇸🇬", dial: "+65", name: "Singapore", max: 8, placeholder: "9123 4567", groups: [4, 4] },
  { region: "AE", flag: "🇦🇪", dial: "+971", name: "UAE", max: 9, placeholder: "50 123 4567", groups: [2, 3, 4] },
  { region: "DE", flag: "🇩🇪", dial: "+49", name: "Germany", max: 11, placeholder: "151 2345 6789", groups: [3, 4, 4] },
  { region: "FR", flag: "🇫🇷", dial: "+33", name: "France", max: 9, placeholder: "6 12 34 56 78", groups: [1, 2, 2, 2, 2] },
  { region: "JP", flag: "🇯🇵", dial: "+81", name: "Japan", max: 10, placeholder: "90 1234 5678", groups: [2, 4, 4] },
  { region: "CA", flag: "🇨🇦", dial: "+1", name: "Canada", max: 10, placeholder: "(416) 555-0199", usStyle: true },
];

function formatDigits(digits, region) {
  const rule = COUNTRY_RULES.find((r) => r.region === region) || COUNTRY_RULES[0];
  const d = digits.slice(0, rule.max);
  if (!d) return "";
  if (rule.usStyle) {
    if (d.length <= 3) return `(${d}`;
    if (d.length <= 6) return `(${d.slice(0, 3)}) ${d.slice(3)}`;
    return `(${d.slice(0, 3)}) ${d.slice(3, 6)}-${d.slice(6)}`;
  }
  const parts = [];
  let idx = 0;
  for (const g of rule.groups) {
    if (idx >= d.length) break;
    parts.push(d.slice(idx, idx + g));
    idx += g;
  }
  if (idx < d.length) parts.push(d.slice(idx));
  return parts.join(" ");
}

function countDigitsBefore(str, pos) {
  let c = 0;
  for (let i = 0; i < Math.min(pos, str.length); i++) {
    if (/\d/.test(str[i])) c++;
  }
  return c;
}

function cursorPosForDigitCount(formatted, targetDigits) {
  if (targetDigits <= 0) return 0;
  let seen = 0;
  for (let i = 0; i < formatted.length; i++) {
    if (/\d/.test(formatted[i])) {
      seen++;
      if (seen === targetDigits) return i + 1;
    }
  }
  return formatted.length;
}

function UnifiedPhoneInput({ region, phone, onChange, error, onBlur }) {
  const inputId = useId();
  const hintId = useId();
  const inputRef = useRef(null);
  const currentRule = COUNTRY_RULES.find((r) => r.region === region) || COUNTRY_RULES[0];

  const handlePhoneInput = (e) => {
    const raw = e.target.value;
    const selStart = e.target.selectionStart ?? raw.length;
    const digitsBefore = countDigitsBefore(raw, selStart);
    const digits = raw.replace(/\D/g, "");
    const formatted = formatDigits(digits, region);

    onChange({ region, phone: formatted });

    requestAnimationFrame(() => {
      if (inputRef.current) {
        const nextPos = cursorPosForDigitCount(formatted, digitsBefore);
        try {
          inputRef.current.setSelectionRange(nextPos, nextPos);
        } catch {
          // Ignore unsupported selection operations
        }
      }
    });
  };

  const handleCountryChange = (e) => {
    const nextRegion = e.target.value;
    const digits = (phone || "").replace(/\D/g, "");
    const reformatted = formatDigits(digits, nextRegion);
    onChange({ region: nextRegion, phone: reformatted });
  };

  return (
    <div className="min-w-0 space-y-1.5">
      <label htmlFor={inputId} className="block text-sm font-medium text-body">
        Phone Number <span className="text-[var(--brand-primary)]" aria-hidden="true">*</span>
      </label>

      <div
        className={`flex min-h-[46px] w-full min-w-0 items-center rounded-xl border bg-[var(--bg-surface)] transition-colors focus-within:ring-2 ${
          error
            ? "border-rose-400 focus-within:border-rose-500 focus-within:ring-rose-200"
            : "border-[var(--border-input)] focus-within:border-[var(--brand-primary)] focus-within:ring-[var(--bg-soft)]"
        }`}
      >
        <select
          aria-label="Country dialing code"
          value={region}
          onChange={handleCountryChange}
          className="h-full max-w-[112px] shrink-0 cursor-pointer rounded-l-xl bg-transparent py-2.5 pl-2.5 pr-1.5 text-sm font-medium text-body outline-none sm:pl-3 sm:pr-2"
        >
          {COUNTRY_RULES.map((c) => (
            <option key={c.region} value={c.region} className="bg-[var(--bg-surface)] text-body">
              {c.flag} {c.dial}
            </option>
          ))}
        </select>

        <span className="mx-1 h-6 w-px shrink-0 bg-[var(--border-color)] sm:mx-1.5" aria-hidden="true" />

        <input
          ref={inputRef}
          id={inputId}
          name="phone"
          type="tel"
          inputMode="numeric"
          autoComplete="tel-national"
          required
          aria-invalid={Boolean(error)}
          aria-describedby={hintId}
          value={phone}
          onChange={handlePhoneInput}
          onBlur={onBlur}
          placeholder={currentRule.placeholder}
          className="min-w-0 flex-1 rounded-r-xl bg-transparent py-2.5 pl-2 pr-3 text-sm text-body placeholder:text-muted outline-none"
        />
      </div>

      <p id={hintId} className="text-xs text-muted">
        {currentRule.name} ({currentRule.dial}) · Automatically formatted &amp; validated in E.164
      </p>
      {error && (
        <p role="alert" className="text-xs font-medium text-rose-600">
          {error}
        </p>
      )}
    </div>
  );
}

export default memo(UnifiedPhoneInput);
