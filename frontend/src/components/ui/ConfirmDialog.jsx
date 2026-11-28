import { AlertTriangle, X } from "lucide-react";
import { useEffect, useRef } from "react";

export default function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = "Confirm",
  onConfirm,
  onCancel,
}) {
  const dialogRef = useRef(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) {
      dialog.showModal();
    } else if (!open && dialog.open) {
      dialog.close();
    }
  }, [open]);

  if (!open) return null;

  return (
    <dialog
      ref={dialogRef}
      onCancel={(e) => {
        e.preventDefault();
        onCancel();
      }}
      className="m-auto w-[calc(100%-2rem)] max-w-md rounded-2xl border border-theme bg-[var(--bg-surface)] p-6 text-body shadow-2xl backdrop:bg-slate-900/55"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-rose-300/60 bg-rose-500/10 text-rose-600">
            <AlertTriangle className="h-5 w-5" />
          </div>
          <h2 className="text-lg font-semibold text-heading">{title}</h2>
        </div>
        <button
          type="button"
          onClick={onCancel}
          aria-label="Close dialog"
          className="rounded-lg p-1 text-muted hover:bg-[var(--bg-soft)] hover:text-heading"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <p className="mt-4 text-sm leading-relaxed text-body">{message}</p>

      <div className="mt-6 flex justify-end gap-3">
        <button
          type="button"
          onClick={onCancel}
          className="rounded-xl border border-theme bg-[var(--bg-surface)] px-4 py-2 text-sm font-medium text-body transition-colors hover:bg-[var(--bg-soft)]"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={onConfirm}
          className="rounded-xl bg-rose-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-rose-700"
        >
          {confirmLabel}
        </button>
      </div>
    </dialog>
  );
}
