"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, SessionRow } from "@/lib/api";

export default function AnalysisPage() {
  const [sessions, setSessions] = useState<SessionRow[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [summary, setSummary] = useState<any>(null);

  useEffect(() => {
    api.sessions().then((s) => {
      setSessions(s);
      if (s[0]) setSelected(s[0].id);
    });
  }, []);

  useEffect(() => {
    if (!selected) return;
    api.analysis(selected).then(setSummary).catch(() => setSummary(null));
  }, [selected]);

  return (
    <div className="space-y-4">
      <h1 className="text-3xl font-semibold">AI Analysis</h1>
      <p className="text-mute text-sm max-w-3xl">
        Concise analyst-oriented summaries. AI-agent likelihood is experimental and probabilistic — never treat as
        definitive attribution of real-world actors.
      </p>
      <select
        className="bg-panel border border-line px-3 py-2 font-mono text-sm w-full max-w-xl"
        value={selected}
        onChange={(e) => setSelected(e.target.value)}
      >
        {sessions.map((s) => (
          <option key={s.id} value={s.id}>
            {s.id.slice(0, 8)} · {s.service} · {s.experimental_classification || s.actor_label || "UNKNOWN"}
          </option>
        ))}
      </select>
      {summary && (
        <section className="border border-line bg-panel/60 p-5 space-y-3">
          <p className="leading-relaxed text-sm">{summary.summary}</p>
          <div className="text-xs font-mono text-mute">
            class={summary.experimental_classification} confidence={Number(summary.confidence).toFixed(2)}
          </div>
          <p className="text-xs text-warn">{summary.caveats}</p>
          <Link href={`/sessions/${selected}`} className="text-accent text-sm underline">
            Open session timeline
          </Link>
        </section>
      )}
    </div>
  );
}
