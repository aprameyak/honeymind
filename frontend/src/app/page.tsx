"use client";

import { useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import { api, Overview } from "@/lib/api";

const COLORS = ["#3ecf8e", "#508cff", "#f0b429", "#ef5f5f", "#a78bfa"];

export default function OverviewPage() {
  const [data, setData] = useState<Overview | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const load = () =>
    api
      .overview()
      .then(setData)
      .catch((e) => setErr(String(e)));

  useEffect(() => {
    load();
  }, []);

  const recompute = async () => {
    setBusy(true);
    try {
      await api.recompute();
      await load();
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  };

  if (err && !data) {
    return <p className="text-danger font-mono text-sm">{err}</p>;
  }
  if (!data) {
    return <p className="text-mute font-mono text-sm">Loading telemetry…</p>;
  }

  const services = Object.entries(data.service_distribution).map(([name, value]) => ({ name, value }));
  const actors = Object.entries(data.actor_classifications).map(([name, value]) => ({ name, value }));

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Operations Overview</h1>
          <p className="text-mute mt-1 text-sm">Defensive deception telemetry for the isolated Nectar lab.</p>
        </div>
        <button
          onClick={recompute}
          disabled={busy}
          className="bg-accent/20 text-accent border border-accent/40 px-4 py-2 text-sm font-medium hover:bg-accent/30 disabled:opacity-50"
        >
          {busy ? "Recomputing…" : "Recompute Analysis"}
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          ["Sessions", data.total_sessions],
          ["Events", data.total_events],
          ["Anomalies", data.anomalies_detected],
          ["Clusters", data.cluster_count],
        ].map(([label, value]) => (
          <div key={String(label)} className="border border-line bg-panel/60 px-4 py-3">
            <div className="text-mute text-xs uppercase tracking-wider">{label}</div>
            <div className="text-2xl font-mono mt-1">{value}</div>
          </div>
        ))}
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <section className="border border-line bg-panel/60 p-4 h-72">
          <h2 className="text-sm text-mute mb-3">Sessions over time</h2>
          <ResponsiveContainer width="100%" height="85%">
            <AreaChart data={data.sessions_over_time}>
              <CartesianGrid stroke="#243049" strokeDasharray="3 3" />
              <XAxis dataKey="date" stroke="#8b9bb4" tick={{ fontSize: 11 }} />
              <YAxis stroke="#8b9bb4" tick={{ fontSize: 11 }} allowDecimals={false} />
              <Tooltip contentStyle={{ background: "#121a2b", border: "1px solid #243049" }} />
              <Area type="monotone" dataKey="count" stroke="#3ecf8e" fill="#3ecf8e33" />
            </AreaChart>
          </ResponsiveContainer>
        </section>

        <section className="border border-line bg-panel/60 p-4 h-72">
          <h2 className="text-sm text-mute mb-3">Service distribution</h2>
          <ResponsiveContainer width="100%" height="85%">
            <PieChart>
              <Pie data={services} dataKey="value" nameKey="name" outerRadius={90} label>
                {services.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ background: "#121a2b", border: "1px solid #243049" }} />
            </PieChart>
          </ResponsiveContainer>
        </section>

        <section className="border border-line bg-panel/60 p-4 h-72 md:col-span-2">
          <h2 className="text-sm text-mute mb-3">Experimental actor classifications</h2>
          <ResponsiveContainer width="100%" height="85%">
            <BarChart data={actors}>
              <CartesianGrid stroke="#243049" strokeDasharray="3 3" />
              <XAxis dataKey="name" stroke="#8b9bb4" tick={{ fontSize: 10 }} />
              <YAxis stroke="#8b9bb4" allowDecimals={false} />
              <Tooltip contentStyle={{ background: "#121a2b", border: "1px solid #243049" }} />
              <Bar dataKey="value" fill="#508cff" />
            </BarChart>
          </ResponsiveContainer>
        </section>
      </div>
    </div>
  );
}
