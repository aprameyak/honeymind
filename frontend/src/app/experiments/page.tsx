"use client";

import { useEffect, useState } from "react";
import { api, ExperimentRow } from "@/lib/api";

export default function ExperimentsPage() {
  const [rows, setRows] = useState<ExperimentRow[]>([]);

  useEffect(() => {
    api.experiments().then(setRows).catch(() => undefined);
  }, []);

  return (
    <div className="space-y-4">
      <h1 className="text-3xl font-semibold">Deception Experiments</h1>
      <p className="text-mute text-sm">
        Safe synthetic artifacts used to compare how actor classes respond. No external attack instructions.
      </p>
      <div className="space-y-3">
        {rows.map((e) => (
          <article key={e.id} className="border border-line bg-panel/60 p-4">
            <div className="flex items-center justify-between gap-3">
              <h2 className="font-mono text-accent">{e.name}</h2>
              <span className={`text-xs ${e.enabled ? "text-accent" : "text-mute"}`}>
                {e.enabled ? "ENABLED" : "DISABLED"}
              </span>
            </div>
            <p className="text-sm mt-2 text-slate-300">{e.description}</p>
            <pre className="mt-3 text-xs font-mono text-mute overflow-x-auto">
              {JSON.stringify({ expected: e.expected_observations, artifact: e.config }, null, 2)}
            </pre>
          </article>
        ))}
      </div>
    </div>
  );
}
