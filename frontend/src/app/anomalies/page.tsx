"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, AnomalyRow } from "@/lib/api";

export default function AnomaliesPage() {
  const [rows, setRows] = useState<AnomalyRow[]>([]);

  useEffect(() => {
    api.anomalies().then(setRows).catch(() => undefined);
  }, []);

  return (
    <div className="space-y-4">
      <h1 className="text-3xl font-semibold">Anomalies</h1>
      <p className="text-mute text-sm">Isolation Forest scores ranked for analyst review.</p>
      <div className="border border-line overflow-x-auto">
        <table className="w-full text-sm min-w-[800px]">
          <thead className="bg-panel text-mute text-left">
            <tr>
              {["Session", "Score", "Flagged", "Service", "Top features"].map((h) => (
                <th key={h} className="px-3 py-2 font-medium">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const top = Object.entries(r.feature_contributions || {})
                .sort((a, b) => b[1] - a[1])
                .slice(0, 3)
                .map(([k, v]) => `${k}:${v.toFixed(2)}`)
                .join(", ");
              return (
                <tr key={r.session_id} className="border-t border-line/70">
                  <td className="px-3 py-2 font-mono text-accent">
                    <Link href={`/sessions/${r.session_id}`}>{r.session_id.slice(0, 8)}</Link>
                  </td>
                  <td className="px-3 py-2 font-mono">{r.score.toFixed(3)}</td>
                  <td className="px-3 py-2">{r.is_anomaly ? <span className="text-danger">yes</span> : "no"}</td>
                  <td className="px-3 py-2 uppercase">{r.service || "—"}</td>
                  <td className="px-3 py-2 font-mono text-xs text-mute">{top || "—"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
