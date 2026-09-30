"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, EventRow } from "@/lib/api";

export default function SessionDetailPage() {
  const params = useParams<{ id: string }>();
  const [session, setSession] = useState<any>(null);
  const [events, setEvents] = useState<EventRow[]>([]);
  const [analysis, setAnalysis] = useState<any>(null);

  useEffect(() => {
    if (!params.id) return;
    api.session(params.id).then(setSession);
    api.events(params.id).then(setEvents);
    api.analysis(params.id).then(setAnalysis).catch(() => undefined);
  }, [params.id]);

  if (!session) return <p className="text-mute font-mono text-sm">Loading session…</p>;

  const t0 = events[0] ? new Date(events[0].timestamp).getTime() : 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold font-mono">{params.id.slice(0, 13)}…</h1>
        <p className="text-mute text-sm mt-1">
          {session.service?.toUpperCase()} · {session.deception_mode} ·{" "}
          {session.experimental_classification || session.actor_label || "UNKNOWN"}
        </p>
      </div>

      {session.session_summary && (
        <p className="border border-line bg-panel/60 p-4 text-sm leading-relaxed">{session.session_summary}</p>
      )}

      {analysis && (
        <section className="border border-accent/30 bg-accent/5 p-4">
          <h2 className="text-accent text-sm mb-2">Analyst summary</h2>
          <p className="text-sm leading-relaxed">{analysis.summary}</p>
          <p className="text-xs text-mute mt-2">{analysis.caveats}</p>
        </section>
      )}

      <section>
        <h2 className="text-lg mb-3">Timeline</h2>
        <ol className="space-y-2 font-mono text-sm">
          {events.map((e) => {
            const offset = Math.max(0, Math.round((new Date(e.timestamp).getTime() - t0) / 1000));
            const mm = String(Math.floor(offset / 60)).padStart(2, "0");
            const ss = String(offset % 60).padStart(2, "0");
            return (
              <li key={e.id} className="border border-line/80 bg-panel/40 px-3 py-2 flex gap-4">
                <span className="text-accent shrink-0">
                  {mm}:{ss}
                </span>
                <span className="text-mute shrink-0 w-28">{e.action_type}</span>
                <span className="break-all">{e.action}</span>
              </li>
            );
          })}
        </ol>
      </section>
    </div>
  );
}
