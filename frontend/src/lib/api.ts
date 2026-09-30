export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
  return res.json();
}

export type Overview = {
  total_sessions: number;
  total_events: number;
  anomalies_detected: number;
  cluster_count: number;
  sessions_over_time: { date: string; count: number }[];
  service_distribution: Record<string, number>;
  actor_classifications: Record<string, number>;
};

export type SessionRow = {
  id: string;
  service: string;
  started_at: string;
  ended_at?: string;
  actor_label?: string;
  cluster_id?: string;
  deception_mode: string;
  event_count: number;
  anomaly_score?: number;
  experimental_classification?: string;
  confidence?: number;
};

export type EventRow = {
  id: string;
  timestamp: string;
  action_type: string;
  action: string;
  response_preview: string;
  latency_ms: number;
  session_depth: number;
};

export type ClusterRow = {
  id: string;
  external_id: number;
  size: number;
  common_behaviors: Record<string, number>;
  representative_session_ids: string[];
};

export type AnomalyRow = {
  session_id: string;
  score: number;
  is_anomaly: boolean;
  feature_contributions: Record<string, number>;
  service?: string;
  actor_label?: string;
};

export type ExperimentRow = {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  expected_observations: Record<string, unknown>;
  config: Record<string, unknown>;
};

export const api = {
  overview: () => get<Overview>("/analytics/overview"),
  sessions: () => get<SessionRow[]>("/sessions"),
  session: (id: string) => get<any>(`/sessions/${id}`),
  events: (id: string) => get<EventRow[]>(`/sessions/${id}/events`),
  analysis: (id: string) => get<any>(`/sessions/${id}/analysis`),
  clusters: () => get<ClusterRow[]>("/analytics/clusters"),
  anomalies: () => get<AnomalyRow[]>("/analytics/anomalies"),
  experiments: () => get<ExperimentRow[]>("/experiments"),
  recompute: async () => {
    const res = await fetch(`${API_URL}/analysis/recompute`, { method: "POST" });
    if (!res.ok) throw new Error("recompute failed");
    return res.json();
  },
};
