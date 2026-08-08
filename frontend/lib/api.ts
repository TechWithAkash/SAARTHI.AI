const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  detail?: string;

  constructor(status: number, statusText: string, detail?: string) {
    super(detail || `${status} ${statusText}`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail: string | undefined;
    try {
      const data = await res.json();
      if (data && typeof data.detail === "string") {
        detail = data.detail;
      }
    } catch {
      // non-JSON response body
    }
    throw new ApiError(res.status, res.statusText, detail);
  }
  return res.json();
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: "no-store" });
  return handleResponse<T>(res);
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return handleResponse<T>(res);
}

async function del<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { method: "DELETE" });
  return handleResponse<T>(res);
}

export interface RiskResponse {
  user_id: string;
  log_id: string;
  risk_score: number;
  risk_category: "Low" | "Moderate" | "High" | "Critical";
  top_risk_factors: string[];
  shap_contributions: Record<string, number>;
  timestamp: string;
  // Ensemble v2 disease-specific scores
  diabetes_risk?: number | null;
  cvd_risk?: number | null;
  hypertension_risk?: number | null;
  // True when extreme input (e.g. a 30-day history with a huge spread) pushed
  // the model outside its training distribution — the score was clipped to a
  // floor/ceiling rather than genuinely computed. Show a caution state, don't
  // present the number as a confident finding, when this is true.
  model_saturated?: boolean | null;
  saturated_after_fallback?: boolean | null;
}

export interface SimulationResponse {
  user_id: string;
  scenarios: { current: number[]; improved: number[]; optimal: number[] };
  timeline_days: number[];
  projected_risk_reduction: { improved: number; optimal: number };
  generated_at: string;
}

export interface Recommendation {
  priority: number;
  action: string;
  reason: string;
  impact: "high" | "medium" | "low";
  timeframe: string;
  estimated_risk_reduction?: number | null;
  causal_mechanism?: string | null;
  // Provenance: "causal_ate" | "shap_prior" | "unavailable" — see BP-3 fix.
  risk_reduction_source?: string | null;
  causal_factor?: string | null;
}

export interface AgentTraceStep {
  step: number;
  type: "tool_call" | "synthesis";
  tool?: string;
  query?: Record<string, unknown>;
  summary?: string;
  content?: string;
}

export interface AgentMeta {
  reasoning: string;
  primary_lever: string;
  agent_confidence: "high" | "medium" | "low";
  tools_called: string[];
  n_tool_calls: number;
  trace: AgentTraceStep[];
}

export interface RecommendResponse {
  user_id: string;
  recommendations: Recommendation[];
  risk_score?: number | null;
  method?: string;
  generated_at?: string;
  agent?: AgentMeta;
}

export interface InsightsFactor {
  factor: string;
  contribution: number;
  description: string;
}

export interface InsightsResponse {
  user_id: string;
  shap_contributions: Record<string, number>;
  primary_cause?: string;
  causal_chain?: string;
  // computed on the frontend from shap_contributions
  risk_drivers?: InsightsFactor[];
  protective_factors?: InsightsFactor[];
}

export interface Alert {
  id: string;
  metric: string;
  severity: string;
  message: string;
  value: number;
  timestamp?: string;
}

export interface AlertsResponse {
  user_id: string;
  alerts: Alert[];
}

export interface ChatMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

export interface ChatResponse {
  reply: string;
  timestamp: string;
}

export interface HealthDataInput {
  user_id: string;
  heart_rate: number;
  sleep: number;
  steps: number;
  stress_level: number;
  diet_score: number;
  bmi: number;
}

export interface MemoryItem {
  id: string;
  memory: string;
  metadata?: Record<string, unknown>;
}

export interface MemoryResponse {
  user_id: string;
  memories: MemoryItem[];
}

export interface GarminStatus {
  provider: string;
  configured: boolean;
  tokens_cached: boolean;
  login_blocked: boolean;
  login_attempts: number;
  max_login_attempts: number;
  cached_responses: number;
  unavailable_from_garmin: string[];
  hint?: string;
  last_sync?: {
    display_name: string | null;
    last_synced_at: string | null;
    days_synced: number;
    last_status: string | null;
    last_error: string | null;
  } | null;
  garmin_rows_in_db?: number;
}

export interface GarminSyncResult {
  user_id: string;
  status: string;
  source: string;
  days_requested: number;
  days_ingested: number;
  date_range: { start: string; end: string };
  ingested: { date: string; measured: string[]; defaulted: string[]; hrv_rmssd?: number | null }[];
  failed: { date: string; reason: string }[];
  unavailable_from_garmin: string[];
  note: string;
}

export interface UserProfile {
  user_id: string;
  age?: number | null;
  gender?: string | null;
  whr?: number | null;
  fam_diabetes?: number | null;
  fam_cvd?: number | null;
  fam_hypertension?: number | null;
  profile_complete?: boolean;
}

export const api = {
  submitHealth: (data: HealthDataInput) =>
    post<{ log_id: string; status: string }>("/health-data", data),
  getRisk: (userId: string) =>
    get<RiskResponse>(`/risk?user_id=${encodeURIComponent(userId)}`),
  getRiskHistory: (userId: string) =>
    get<RiskResponse[]>(`/risk/history?user_id=${encodeURIComponent(userId)}`),
  getSimulation: (userId: string) =>
    get<SimulationResponse>(`/simulate?user_id=${encodeURIComponent(userId)}`),
  getRecommend: (userId: string) =>
    get<RecommendResponse>(`/recommend?user_id=${encodeURIComponent(userId)}`),
  getInsights: (userId: string) =>
    get<InsightsResponse>(`/insights?user_id=${encodeURIComponent(userId)}`),
  getAlerts: (userId: string) =>
    get<AlertsResponse>(`/alerts?user_id=${encodeURIComponent(userId)}`),
  chat: (userId: string, message: string, history: ChatMessage[]) =>
    post<ChatResponse>("/chat", { user_id: userId, message, history }),
  acknowledgeAlert: (alertId: string) =>
    post<{ status: string }>(`/alerts/${encodeURIComponent(alertId)}/acknowledge`, {}),
  getMemories: (userId: string) =>
    get<MemoryResponse>(`/memory/${encodeURIComponent(userId)}`),
  clearMemories: (userId: string) =>
    del<{ status: string }>(`/memory/${encodeURIComponent(userId)}`),
  getLatestHealth: (userId: string) =>
    get<HealthDataInput>(`/health-data/${encodeURIComponent(userId)}`),
  getProfile: (userId: string) =>
    get<UserProfile>(`/profile?user_id=${encodeURIComponent(userId)}`),
  updateProfile: (data: UserProfile) =>
    post<UserProfile>("/profile", data),
  getGarminStatus: (userId: string) =>
    get<GarminStatus>(`/garmin/status?user_id=${encodeURIComponent(userId)}`),
  syncGarmin: (userId: string, days: number = 14) =>
    post<GarminSyncResult>("/garmin/sync", { user_id: userId, days }),
};
