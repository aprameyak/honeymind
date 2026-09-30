"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, ClusterRow } from "@/lib/api";

export default function ClustersPage() {
  const [clusters, setClusters] = useState<ClusterRow[]>([]);

  useEffect(() => {
    api.clusters().then(setClusters).catch(() => undefined);
  }, []);

  return (
    <div className="space-y-4">
      <h1 className="text-3xl font-semibold">Behavioral Clusters</h1>
      <p className="text-mute text-sm">
        Unsupervised DBSCAN groups. Labels are discovered behavioral cohorts — not malice verdicts.
      </p>
      <div className="grid md:grid-cols-2 gap-4">
        {clusters.map((c) => (
          <article key={c.id} className="border border-line bg-panel/60 p-4 space-y-3">
            <div className="flex justify-between">
              <h2 className="font-mono text-accent">Cluster {c.external_id}</h2>
              <span className="text-mute text-sm">size {c.size}</span>
            </div>
            <div className="text-xs text-mute uppercase tracking-wide">Common behaviors</div>
            <ul className="text-sm font-mono space-y-1">
              {Object.entries(c.common_behaviors || {})
                .slice(0, 6)
                .map(([k, v]) => (
                  <li key={k}>
                    {k} <span className="text-mute">×{v}</span>
                  </li>
                ))}
            </ul>
            <div className="text-xs text-mute">Representative sessions</div>
            <div className="flex flex-wrap gap-2">
              {(c.representative_session_ids || []).map((id) => (
                <Link key={id} href={`/sessions/${id}`} className="font-mono text-xs text-accent underline">
                  {String(id).slice(0, 8)}
                </Link>
              ))}
            </div>
          </article>
        ))}
        {clusters.length === 0 && <p className="text-mute font-mono text-sm">No clusters yet — run recompute after traffic.</p>}
      </div>
    </div>
  );
}
