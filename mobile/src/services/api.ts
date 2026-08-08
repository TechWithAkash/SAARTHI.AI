import axios from 'axios';
import Constants from 'expo-constants';

// ── Backend base URL ────────────────────────────────────────────────────────
// The previous value here was a hardcoded ngrok tunnel from a prior hackathon
// session — ngrok URLs are ephemeral and that one is long dead, so every
// request from this app was silently failing before anything else about it
// could even be tested.
//
// A phone on the same demo WiFi as the dev laptop can't reach "localhost" —
// that's the phone's own loopback, not the laptop's. Expo already knows the
// laptop's LAN IP (it's how Metro's dev server reaches the phone in the first
// place) via Constants.expoConfig.hostUri, e.g. "192.168.1.23:8081" — reusing
// that host with the backend's port (8000) auto-derives the right address for
// the common single-laptop hackathon setup, with zero manual config most of
// the time. MANUAL_BACKEND_HOST is the escape hatch for anything else
// (a real deployed backend, a different machine, tunnelling for a remote demo).
const MANUAL_BACKEND_HOST: string | null = null; // e.g. "192.168.1.23:8000" or "https://your-tunnel.example.com"
const BACKEND_PORT = 8000;

function resolveBaseUrl(): string {
  if (MANUAL_BACKEND_HOST) {
    return MANUAL_BACKEND_HOST.startsWith('http')
      ? MANUAL_BACKEND_HOST
      : `http://${MANUAL_BACKEND_HOST}`;
  }
  const hostUri = Constants.expoConfig?.hostUri; // "192.168.1.23:8081"
  const lanIp = hostUri?.split(':')[0];
  if (lanIp) return `http://${lanIp}:${BACKEND_PORT}`;

  // Fallback for the iOS simulator specifically (shares the Mac's localhost).
  // A physical device will not reach this — set MANUAL_BACKEND_HOST above.
  return `http://localhost:${BACKEND_PORT}`;
}

export const API_BASE_URL = resolveBaseUrl();

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 15000,
});

// ── Health data (manual check-in — mirrors the web dashboard's slider form) ──

export interface HealthDataInput {
  user_id: string;
  heart_rate: number;
  sleep: number;
  steps: number;
  stress_level: number;
  diet_score: number;
  bmi: number;
  source?: 'manual' | 'garmin';
}

export const submitHealthData = async (data: HealthDataInput) => {
  const response = await apiClient.post('/health-data', data);
  return response.data;
};

export const fetchLatestHealth = async (userId: string) => {
  const response = await apiClient.get(`/health-data/${encodeURIComponent(userId)}`);
  return response.data;
};

// ── Risk ─────────────────────────────────────────────────────────────────────

export interface RiskResponse {
  user_id: string;
  risk_score: number;
  risk_category: string;
  timestamp: string;
  top_risk_factors: string[];
  diabetes_risk?: number | null;
  cvd_risk?: number | null;
  hypertension_risk?: number | null;
  // True when the input pushed the model outside its normal operating range —
  // show a caution state instead of trusting the number outright, same as web.
  model_saturated?: boolean | null;
}

export const fetchRiskScore = async (userId: string): Promise<RiskResponse> => {
  const response = await apiClient.get('/risk', { params: { user_id: userId } });
  return response.data;
};

export const fetchRiskHistory = async (userId: string): Promise<RiskResponse[]> => {
  const response = await apiClient.get('/risk/history', { params: { user_id: userId } });
  return response.data;
};

// ── Garmin (server-side sync — no on-device SDK, no Apple Developer account
// needed; the backend pulls real wearable data using stored credentials, the
// exact same endpoint the web dashboard's "Sync Garmin" button calls) ────────

export interface GarminStatus {
  provider: string;
  configured: boolean;
  tokens_cached: boolean;
  login_blocked: boolean;
  login_attempts: number;
  max_login_attempts: number;
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

export const fetchGarminStatus = async (userId: string): Promise<GarminStatus> => {
  const response = await apiClient.get('/garmin/status', { params: { user_id: userId } });
  return response.data;
};

export interface GarminSyncResult {
  status: string;
  source: string;
  days_ingested: number;
  date_range: { start: string; end: string };
  note: string;
}

// A sync makes the backend call out to Garmin's real servers for each day
// requested — that's several sequential external HTTP calls, not a local DB
// read, so it legitimately takes much longer than the app's other endpoints.
// The shared 15s apiClient timeout is fine for those but too tight here; give
// this one call more room before giving up.
const GARMIN_SYNC_TIMEOUT_MS = 60000;

export const syncGarmin = async (userId: string, days = 14): Promise<GarminSyncResult> => {
  const response = await apiClient.post(
    '/garmin/sync',
    { user_id: userId, days },
    { timeout: GARMIN_SYNC_TIMEOUT_MS }
  );
  return response.data;
};

// axios/RN's XHR layer reports both "the connection actually dropped" and
// "our own client-side timeout fired" as generic, indistinguishable errors —
// there's no separate "still running on the server" state to check against.
// This just labels the timeout case honestly instead of claiming "failed"
// when the backend may well still be completing the sync in the background.
export const isTimeoutError = (e: any): boolean =>
  e?.code === 'ECONNABORTED' || /timeout/i.test(e?.message ?? '');
