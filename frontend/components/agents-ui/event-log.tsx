"use client";
import { useEffect, useMemo, useState } from "react";

type EventEntry = {
  event_type: string;
  timestamp: string;
  red_flag_status: boolean;
  escalation_status: boolean;
};

type DerivedState = "waiting_post_screening" | "post_screening" | "escalated";

const EVENT_LABELS: Record<string, string> = {
  screening_completed: "✅ Screening completed",
  greeting: "👋 Greeting sent",
  question: "💬 Question answered",
  task_pending: "📋 Task pending",
  red_flag: "🚨 Red flag detected",
  escalation: "🔴 Escalation triggered",
};

const STATE_STYLES: Record<DerivedState, string> = {
  waiting_post_screening: "bg-white/10 text-white/70 border-white/20",
  post_screening: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  escalated: "bg-red-500/15 text-red-300 border-red-500/30",
};

const STATE_LABELS: Record<DerivedState, string> = {
  waiting_post_screening: "waiting_post_screening",
  post_screening: "post_screening",
  escalated: "escalated",
};

/**
 * Mirrors `derive_state()` in data_domain/mongo_event_repo.py.
 * Scans events in order; escalation wins, then post_screening, default waiting.
 */
function deriveState(events: EventEntry[]): DerivedState {
  let state: DerivedState = "waiting_post_screening";
  for (const event of events) {
    if (event.event_type === "screening_completed") {
      state = "post_screening";
    }
    if (
      event.event_type === "red_flag" ||
      event.event_type === "escalation" ||
      event.red_flag_status ||
      event.escalation_status
    ) {
      state = "escalated";
    }
  }
  return state;
}

function eventColor(event: EventEntry): string {
  if (event.escalation_status || event.event_type === "escalation") {
    return "text-red-400";
  }
  if (event.event_type === "red_flag" || event.red_flag_status) {
    return "text-red-400";
  }
  if (event.event_type === "task_pending") {
    return "text-amber-300";
  }
  return "text-white/70";
}

export function EventLog({ userId }: { userId: string }) {
  const [events, setEvents] = useState<EventEntry[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);

  useEffect(() => {
    if (!userId) return;
    let cancelled = false;
    const poll = async () => {
      try {
        const res = await fetch(`/api/events?user_id=${userId}`);
        const data = await res.json();
        if (cancelled) return;
        setEvents(data.events ?? []);
        setIsStreaming(true);
      } catch {
        if (!cancelled) setIsStreaming(false);
      }
    };
    poll();
    const interval = setInterval(poll, 2000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [userId]);

  const derivedState = useMemo<DerivedState>(() => deriveState(events), [events]);

  return (
    <div className="flex flex-col gap-1 p-3 bg-black/20 rounded-lg text-xs font-mono max-h-64 overflow-y-auto">
      <div className="flex items-center justify-between mb-1">
        <p className="text-white/50 text-[10px] uppercase tracking-wider">
          MongoDB Event Log ({events.length} {events.length === 1 ? "event" : "events"})
        </p>
        <span
          className="flex items-center gap-1 text-[10px] text-white/40"
          aria-label={isStreaming ? "Streaming events" : "Not streaming"}
        >
          <span
            className={`inline-block h-1.5 w-1.5 rounded-full ${
              isStreaming ? "bg-emerald-400 animate-pulse" : "bg-white/30"
            }`}
          />
          {isStreaming ? "live" : "idle"}
        </span>
      </div>

      <div className="mb-2">
        <span
          className={`inline-block rounded border px-2 py-0.5 text-[10px] font-medium ${STATE_STYLES[derivedState]}`}
          title="Derived state computed client-side from event history (mirrors derive_state in mongo_event_repo.py)"
        >
          state: {STATE_LABELS[derivedState]}
        </span>
      </div>

      {events.length === 0 && (
        <p className="text-white/30 italic">No events yet</p>
      )}
      {events.map((e, i) => (
        <div key={i} className={`flex gap-2 ${eventColor(e)}`}>
          <span className="text-white/30 shrink-0">
            {new Date(e.timestamp).toLocaleTimeString("en-GB", {
              hour: "2-digit",
              minute: "2-digit",
              second: "2-digit",
            })}
          </span>
          <span>{EVENT_LABELS[e.event_type] ?? e.event_type}</span>
        </div>
      ))}
    </div>
  );
}
