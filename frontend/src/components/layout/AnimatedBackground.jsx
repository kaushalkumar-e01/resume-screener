export default function AnimatedBackground() {
  return (
    <div
      className="no-print pointer-events-none fixed inset-0 -z-10 bg-[var(--bg-canvas)]"
      aria-hidden="true"
    >
      <div
        className="absolute inset-x-0 top-0 h-80 opacity-60"
        style={{
          background:
            "linear-gradient(180deg, var(--bg-soft) 0%, transparent 100%)",
        }}
      />
    </div>
  );
}
