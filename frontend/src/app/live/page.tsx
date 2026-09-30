"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, SessionRow } from "@/lib/api";

export default function LivePage() {
  const [sessions, setSessions] = useState<SessionRow[]>([]);

  useEffect(() => {
    const tick = () => api.sessions().then(setSessions).catch(() => undefined);
    tick();
    const id = setInterval(tick, 4000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <h1 className="text-3xl font-semibold">Live Sessions</h1>
        <span className="h-2.5 w-2.5 rounded-full bg-accent animate-live" />
      </div>
      <p className="text-mute text-sm">Polling inbound honeypot interactions every 4s.</p>
      <div className="border border-line overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-panel text-mute text-left">
            <tr>
              <th className="px-3 py-2 font-medium">Session</th>
              <th className="px-3 py-2 font-medium">Service</th>
              <th className="px-3 py-2 font-medium">Events</th>
              <th className="px-3 py-2 font-medium">Started</th>
              <th className="px-3 py-2 font-medium">Class</th>
            </tr>
          </thead>
          <tbody>
            {sessions.slice(0, 25).map((s) => (
              <tr key={s.id} className="border-t border-line/70 hover:bg-panel/40">
                <td className="px-3 py-2 font-mono text-accent">
                  <Link href={`/sessions/${s.id}`}>{s.id.slice(0, 8)}</Link>
                </td>
                <td className="px-3 py-2 uppercase">{s.service}</td>
                <td className="px-3 py-2 font-mono">{s.event_count}</td>
                <td className="px-3 py-2 font-mono text-mute">{new Date(s.started_at).toLocaleTimeString()}</td>
                <td className="px-3 py-2 text-xs">{s.experimental_classification || s.actor_label || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
