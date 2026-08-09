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

// ── Health timeline (real per-day history, DB-only — never calls Garmin) ────
// Every field the backend actually stores, including `extras` (hrv_rmssd,
// spo2_avg, respiration_avg, body_battery, weight_kg) and, critically,
// `measured_fields` / `defaulted_fields` — the backend's own record of which
// numbers on a Garmin day came from the device vs. an app fallback default.
// A UI must gate on `measured_fields` (for source: 'garmin' rows) rather than
// show every non-null number as real — several fields here are silently
// defaulted (e.g. diet_score, which Garmin has no food log for at all).

export interface HealthDayExtras {
  hrv_rmssd?: number | null;
  spo2_avg?: number | null;
  respiration_avg?: number | null;
  body_battery_charged?: number | null;
  body_battery_drained?: number | null;
  weight_kg?: number | null;
  measured_fields?: string[] | null; // only present for source: 'garmin'
  defaulted_fields?: string[] | null;
  garmin_date?: string;
  [key: string]: unknown;
}

export interface HealthDay {
  date: string; // "YYYY-MM-DD"
  timestamp: string;
  source: 'garmin' | 'manual' | string;
  heart_rate: number | null;
  steps: number | null;
  sleep: number | null;
  bmi: number | null;
  stress_level: number | null;
  diet_score: number | null;
  systolic_bp: number | null;
  diastolic_bp: number | null;
  blood_oxygen: number | null;
  active_minutes: number | null;
  water_intake_ml: number | null;
  extras: HealthDayExtras;
}

export interface HealthTimeline {
  user_id: string;
  days: HealthDay[]; // oldest first
}

export const fetchHealthTimeline = async (userId: string, days = 30): Promise<HealthTimeline> => {
  const response = await apiClient.get(`/health-data/${encodeURIComponent(userId)}/timeline`, {
    params: { days },
  });
  return response.data;
};

// A field counts as a real, device-measured reading only if the row says so.
// Manual entries have no measured_fields list at all — every non-null value
// on a manual row was typed in directly by the user, so it's trusted as-is.
export function isFieldMeasured(day: HealthDay, field: string): boolean {
  if (day[field as keyof HealthDay] == null) return false;
  if (day.source !== 'garmin') return true;
  const measured = day.extras?.measured_fields;
  if (!measured) return false;
  return measured.includes(field);
}

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
// this one call more room before giving up. Bumped alongside the 14->30 day
// default below — steps/body-battery are 2 bulk calls regardless of range,
// but sleep/HRV/stress are one call *per day*, so 30 days is meaningfully
// more real network time than 14 was.
const GARMIN_SYNC_TIMEOUT_MS = 90000;

export const syncGarmin = async (userId: string, days = 30): Promise<GarminSyncResult> => {
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

// ── AI chat (same /chat/stream SSE endpoint the web app's assistant uses —
// context (risk, SHAP, causal chain, guideline RAG, personal mem0 memory) is
// already built server-side per user_id; this is just a client for it) ──────
//
// It's Server-Sent Events, and React Native's fetch() doesn't reliably expose
// a readable streaming body across Hermes/Expo Go the way a browser does —
// the standard, dependency-free workaround (same one react-native-sse uses
// internally) is XMLHttpRequest: xhr.responseText grows as bytes arrive, and
// `onprogress` fires on each chunk, so reading only the newly-appended slice
// each time reconstructs the stream without pulling in a native module.

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatStreamHandlers {
  onToken: (content: string) => void;
  onDone: (chips: string[]) => void;
  onError: (message: string) => void;
}

export function streamChat(
  userId: string,
  message: string,
  history: ChatMessage[],
  handlers: ChatStreamHandlers,
  docSessionId?: string
): () => void {
  const xhr = new XMLHttpRequest();
  let cursor = 0;
  let buffer = '';

  const processNewData = () => {
    const newChunk = xhr.responseText.slice(cursor);
    cursor = xhr.responseText.length;
    if (!newChunk) return;
    buffer += newChunk;

    // SSE events are separated by a blank line; the last split segment may
    // be an event that hasn't fully arrived yet — hold it for the next pass.
    const parts = buffer.split('\n\n');
    buffer = parts.pop() ?? '';

    for (const raw of parts) {
      const line = raw.trim();
      if (!line.startsWith('data:')) continue;
      const jsonStr = line.slice(5).trim();
      if (!jsonStr) continue;
      try {
        const evt = JSON.parse(jsonStr);
        if (evt.type === 'token') handlers.onToken(evt.content ?? '');
        else if (evt.type === 'done') handlers.onDone(evt.chips ?? []);
        else if (evt.type === 'error') handlers.onError(evt.message ?? 'Something went wrong.');
      } catch {
        // Shouldn't happen once an event has a full blank-line terminator —
        // if it does, drop just that malformed fragment, not the connection.
      }
    }
  };

  xhr.open('POST', `${API_BASE_URL}/chat/stream`);
  xhr.setRequestHeader('Content-Type', 'application/json');
  xhr.onprogress = processNewData;
  xhr.onreadystatechange = () => {
    if (xhr.readyState === 4) {
      processNewData();
      if (xhr.status !== 200 && xhr.status !== 0) {
        handlers.onError(`Connection failed (HTTP ${xhr.status}).`);
      }
    }
  };
  xhr.onerror = () => handlers.onError('Network error — check the backend connection.');
  xhr.timeout = 45000;
  xhr.ontimeout = () => handlers.onError('The assistant took too long to respond.');

  xhr.send(JSON.stringify({ user_id: userId, message, history, doc_session_id: docSessionId }));

  return () => xhr.abort();
}
