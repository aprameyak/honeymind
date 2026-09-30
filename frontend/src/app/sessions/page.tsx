"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, SessionRow } from "@/lib/api";

export default function SessionsPage() {
  const [sessions, setSessions] = useState<SessionRow[]>([]);

  useEffect(() => {
    api.sessions().then(setSessions).catch(() => undefined);
  }, []);

  return (
    <div className="space-y-4">
      <h1 className="text-3xl font-semibold">Session Explorer</h1>
      <div className="border border-line overflow-x-auto">
        <table className="w-full text-sm min-w-[900px]">
          <thead className="bg-panel text-mute text-left">
            <tr>
              {["Session", "Duration", "Service", "Actions", "Cluster", "Anomaly", "Classification", "Mode"].map((h) => (
                <th key={h} className="px-3 py-2 font-medium">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sessions.map((s) => {
              const start = new Date(s.started_at).getTime();
              const end = s.ended_at ? new Date(s.ended_at).getTime() : start;
              const dur = Math.max(0, Math.round((end - start) / 1000));
              return (
                <tr key={s.id} className="border-t border-line/70 hover:bg-panel/40">
                  <td className="px-3 py-2 font-mono text-accent">
                    <Link href={`/sessions/${s.id}`}>{s.id.slice(0, 8)}</Link>
                  </td>
                  <td className="px-3 py-2 font-mono">{dur}s</td>
                  <td className="px-3 py-2 uppercase">{s.service}</td>
                  <td className="px-3 py-2 font-mono">{s.event_count}</td>
                  <td className="px-3 py-2 font-mono text-mute">{s.cluster_id ? s.cluster_id.slice(0, 8) : "—"}</td>
                  <td className="px-3 py-2 font-mono">{s.anomaly_score?.toFixed(3) ?? "—"}</td>
                  <td className="px-3 py-2 text-xs">{s.experimental_classification || "UNKNOWN"}</td>
                  <td className="px-3 py-2">{s.deception_mode}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
