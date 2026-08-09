# SAARTHI.AI — Architecture & Project Lifecycle

A preventive-health platform that turns real Garmin wearable data into a
personalized disease-risk score (diabetes / CVD / hypertension), explains
*why* via SHAP + causal inference, projects it forward via simulation, and
lets the user ask an AI assistant about their own data in plain language.

Three apps share one backend:

```
backend/    FastAPI + Postgres — the ML engine and all business logic
frontend/   Next.js 16 (App Router) — web dashboard
mobile/     Expo / React Native — mobile app (Insights, Vitals, Assistant, Sync)
```

## Data lifecycle — from a wearable to a risk score

```
Garmin Connect (real API)  ──┐
                              ├─▶ health_logs (Postgres, one row per calendar day)
Manual check-in (web form) ──┘
                                        │
                                        ▼
                    Background pipeline (routes/health_data.py)
        ┌────────────┬────────────┬────────────┬────────────┬────────────┐
   anomaly       risk score    SHAP        causal        simulation   memory
   detection    (ensemble)   explanation  inference      (120-day)   (mem0)
                                (DoWhy)
                                        │
                                        ▼
              4-step Cognitive Agent (Groq) → recommendations
                                        │
                                        ▼
        Dashboard / Vitals / Simulation / Assistant / Alerts (web + mobile)
```

Each pipeline stage is independently try/excepted — one stage failing (e.g.
Groq being rate-limited) doesn't take down the ones before it. The risk
score itself never depends on an LLM call; only the qualitative narrative
layer (recommendations, chat) does.

## The ML model

`backend/services/ensemble_service.py` — **DarpanEnsemble v2**: a Transformer
sequence model + 3 XGBoost disease specialists (diabetes / CVD /
hypertension) + a Ridge meta-learner, trained on 12 ICMR-derived features
built from 5 tracked vitals (steps, sleep, stress, diet, heart rate) engineered
into a 36-dimensional feature vector (rolling mean/std/min/max/trend + threshold
counts). Includes a saturation check (`XGB_SATURATION_MARGIN`) that flags when
an input falls outside the model's training distribution, so the UI can show
a "low confidence" warning instead of a falsely-precise number.

`ml_validation/` — a **separate, independent validation study**: simple
XGBoost models trained on NHANES survey data, benchmarked against a published
clinical score (IDRS). Not wired into the live app — see `/validation` in the
web frontend for the results and an honest note on where one of the three
results has a methodology caveat (HbA1c-as-feature leakage on the diabetes
model specifically; hypertension and CVD are clean).

## Three separate AI "context" channels — don't confuse these

The assistant (web `/chat`, the `AuraChat` floating widget, and mobile's
Assistant tab) is grounded in real data through three distinct, deliberately
un-merged mechanisms:

1. **Direct current-state injection** — every chat request runs a live SQL
   query for the user's *latest* risk score, SHAP values, and vitals and
   drops them straight into the system prompt. No vector DB involved.
2. **Personal memory** (`memory_service.py`, mem0 + **pgvector**) — every
   health submission (including Garmin syncs) is converted into a
   natural-language observation and embedded for semantic recall across
   sessions.
3. **Static guideline RAG** (`rag.py` + `personalized_rag_service.py`,
   TF-IDF, not vectors) — a fixed corpus of medical guideline PDFs
   (`guideline_corpus/`), kept deliberately separate from personal data.

There is no ChromaDB in this stack — pgvector already serves that role via
mem0.

## Garmin integration — safety-first by design

`backend/services/garmin_service.py` — server-side only, no on-device SDK.
Cached-tokens-first login; a hard cap on login attempts per process
(`max_login_attempts`) so a bug can't repeatedly hammer the real Garmin
account. `.garmin_cache/` and `.garmin_tokens/` persist state to disk so a
single successful login isn't a single point of failure during a demo.
`/garmin/status` is always safe to call (never triggers a real login itself).

## Key backend routes

| Route | Purpose |
|---|---|
| `/health-data`, `/health-data/{user}/timeline` | submit / read raw vitals |
| `/risk`, `/risk/history` | current + historical risk score |
| `/insights` | SHAP + causal chain explanation |
| `/simulate`, `/simulate/whatif` | 120-day trajectory + interactive what-if |
| `/recommend`, `/recommend/stream` | 4-step Cognitive Agent (Groq) |
| `/chat/stream`, `/chat/upload` | AI assistant (SSE) + document RAG |
| `/garmin/status`, `/garmin/sync` | Garmin Connect integration |

## Frontend (web)

`app/(dashboard)/` — dashboard, simulation, chat, insights, alerts, arena
(model benchmarks), settings, validation. `components/Sidebar.tsx` is the
nav; `components/AuraChat.tsx` is a second, globally-mounted floating
assistant (separate from the `/chat` page — both share `MarkdownText.tsx`
for rendering the model's markdown output).

## Mobile

4 tabs: **Insights** (AI-derived risk only), **Health Data** (raw Garmin
metrics + trends), **Assistant** (chat), **Sync**. Built around one rule
enforced throughout: a value only renders if the backend's own
`measured_fields` says it was actually read off the device that day —
otherwise it shows "not tracked" rather than silently displaying a
backend-defaulted fallback as if it were real. `mobile/src/theme.ts` is the
shared design system (colors/spacing/type) every screen pulls from.

## Running it locally

```bash
# Backend (from repo root — rag.py is imported as a bare module,
# which only resolves if the process is started from here)
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

# Frontend
cd frontend && npm run dev

# Mobile
cd mobile && npx expo start -c
```

Requires `GROQ_API_KEY` in `.env` at repo root (powers every AI feature —
chat, recommendations, the cognitive agent; there is no separate OpenAI key
needed anywhere in this stack) and Garmin credentials if testing real sync.

## Project docs

- `docs/CONTEXT.md`, `docs/MASTER_PLAN.md` — working notes and planning
  history from development, not required reading to run the app.
- `README.md` — quick start.
- `CLAUDE.md` / `AGENTS.md` / `GEMINI.md` — AI coding assistant instructions,
  auto-loaded by their respective tools. Kept at repo root deliberately;
  moving them breaks that auto-loading.
