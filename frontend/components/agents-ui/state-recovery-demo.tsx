"use client";

/**
 * State Recovery Demo
 *
 * Hackathon judge moment: prove that session state lives in MongoDB,
 * not in React. Click → local state evaporates (page reload) →
 * EventLog re-polls /api/events → state reconstructs from event history
 * via the same logic as derive_state() in mongo_event_repo.py.
 */
export function StateRecoveryDemo() {
  const handleReload = () => {
    if (typeof window === "undefined") return;
    // Local state evaporates here. MongoDB is the source of truth.
    window.location.reload();
  };

  return (
    <div className="flex flex-col gap-2 p-3 bg-black/20 rounded-lg text-xs font-mono">
      <p className="text-white/50 text-[10px] uppercase tracking-wider">
        State Recovery Demo
      </p>
      <button
        type="button"
        onClick={handleReload}
        className="rounded border border-red-500/40 bg-red-500/10 px-3 py-1.5 text-[11px] font-medium text-red-300 transition-colors hover:bg-red-500/20 hover:text-red-200 focus:outline-none focus:ring-1 focus:ring-red-400"
        title="State persists in MongoDB. Reload reconstructs from event history."
      >
        End Session & Reload
      </button>
      <p className="text-white/40 text-[10px] leading-snug">
        State persists in MongoDB. Reload reconstructs from event history.
      </p>
    </div>
  );
}
