# SAARTHI.AI — Working Context & Decisions

**Last updated:** 2026-08-08
**Team:** Refactor · ZEN-T245 · SIES Graduate School of Technology · 4 members
**Event:** ZEN Club hackathon — **resubmission** (placed **3rd** previously)
**Domain:** Healthcare & MedTech *(decision: stay — do not switch)*
**Branch:** `web+app` · audit performed at commit `5c0a0de`
**Time budget:** 20+ hours to build

> This file is the shared context record for the team, including the teammate
> who was absent. Read the "Start here" section, then jump to your track.

---

## Start here — the three things that matter

1. **The training labels are synthetic.** R²=0.995 is not a good result, it is
   evidence the labels came from a formula. This is the main reason we placed
   3rd and not 1st. See [Data provenance](#data-provenance-the-central-finding).
2. **The interactive step/risk predictor does not exist.** We thought it did.
   What exists is three hardcoded scenarios. See [What we actually have](#what-we-actually-have-verified).
3. **`estimated_risk_reduction` (the "−3.2 pts" on recommendation cards) is
   invented by the LLM.** Nothing computes it. Fix already exists in dead code.

---

## Situation

- The iOS/HealthKit path is **blocked** — the teammate holding the Apple Developer
  account and provisioned device is ill and absent.
- **Pivot: Garmin Connect** via `python-garminconnect` (server-side, no dev account,
  no app build). Owned by the returning/remote teammate.
- Decision: **do not switch domains and do not switch projects.** With <4h that was
  suicide; with 20h it's simply unnecessary. The engineering is already strong.

### Why we placed 3rd (judge's-eye diagnosis)

| Criterion             | Score          | Note                                               |
| --------------------- | -------------- | -------------------------------------------------- |
| Problem & impact      | 8/10           | Diabetes/CVD/hypertension in India — right target |
| Technical depth       | 9/10           | Top-decile for a student hackathon                 |
| Completeness          | 7/10           | Works end-to-end, but working ≠ correct           |
| Presentation & Q&A    | 5/10           | Lost the room on one question                      |
| **Originality** | **5/10** | ⬅ the real gap                                    |

**Core problem: our best engineering is invisible in the demo.** A judge sees
sliders → a number → cards → a chatbot. They do not see the transformer, the
causal DAG, or the meta-learner. We score 9/10 on engineering and present like 5/10.

**Unanswered judge question last time:** *"Did you only cover diabetes and heart rate?"*
Answer prepared below.

---

## Data provenance — the central finding

### What we found

| Model                                         | Training data                                                                                                                   | Verdict                                                                                                                                                                       |
| --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `risk_model.pkl` (old, 7-feature)           | `backend/ml/generate_dataset.py`                                                                                              | **Provably synthetic.** 5,000 rows from a hand-written weighted formula + Gaussian noise, lines 23–33. R²=0.785 measures how well XGBoost learned our own arithmetic. |
| `darpan_*_icmr.*` (ensemble v2, 12-feature) | `timeseries_health_data_icmr.csv` from **`generate_timeseries_data.py`** (per docstring `train_l40s_sequence.py:7`) | **Almost certainly synthetic.** Generator script, not in repo — lived at `/home/soc/.local/share/.cache-icmr/` on the rented GPU box.                                |

Reported metrics (`darpan_ensemble_v2_12feature/log_3_meta.txt`), 50,000 users × 30 days × 12 features:

```
Diabetes      R²=0.9953   MAE=1.28%
CVD           R²=0.9972   MAE=1.03%
Hypertension  R²=0.9934   MAE=1.62%
```

### Why R²=0.995 is bad news, not good news

Write `y = 2x + 3`, generate 50,000 rows, train a transformer → R²=0.9999.
Nothing was learned about the world; the network proved it can do arithmetic.

Real epidemiological risk models land at **AUC 0.70–0.85**. Framingham, QRISK3,
ICMR-INDIAB-derived scores — none approach 0.99. Human biology is not 99.5%
predictable from twelve lifestyle variables.

Two consequences:

1. **No real patient's outcome was ever in training** → we cannot answer
   "how do you know this works?", and prediction *is* the product.
2. **R²=0.995 is a tell.** Any judge with ML training sees it and knows.
   We were advertising it as a badge on our own dashboard.

⚠️ **`generate_timeseries_data.py` was never read** (not in this repo). Confirm
with whoever ran the GPU training before stating anything on stage.

### The honest framing (this is a strength when stated correctly)

> "We trained on a 50,000-patient synthetic cohort built from ICMR-INDIAB
> population statistics, because real Indian longitudinal wearable data with
> outcome labels isn't publicly available. R²=0.995 shows our architecture
> recovers the generative process — it validates the *model*, not clinical
> accuracy. Clinical validation needs a real cohort, which is what our
> intervention-tracking loop is designed to start collecting."

Do **not** let "ICMR" imply we trained on real ICMR patient records.

---

## What we actually have (verified)

### The interactive predictor — does NOT exist

- **No what-if endpoint.** Only POST routes: `alerts/{id}/acknowledge`,
  `health-data`, `telegram/generate-token`, `telegram/unlink`, `profile`,
  `chat/stream`, `chat/upload`.
- **Simulation is hardcoded.** `simulation_service.py:41`
  `IMPROVED_DELTAS = {sleep: +2.0, steps: +3000, stress: -2.0, diet: +1.5}`.
  Three preset futures, computed once during ingestion, stored as JSON.
  Not user-adjustable.
- **Frontend only does `GET /simulate?user_id=`** (`lib/api.ts:164`). No way to
  send modified vitals.

### `estimated_risk_reduction` is LLM-invented

- `cognitive_agent_service.py:280` — the *prompt* asks the LLM for `"estimated_risk_reduction": 3.2`
- `:305` — `r.setdefault("estimated_risk_reduction", 0.0)` backfills a default
- `RecommendationCard.tsx:59` renders `−{value} pts` next to real model output

**The fix already exists in dead code:** `recommendation_service.py:229` does
`"estimated_risk_reduction": abs(ate)` — the real causal ATE. The abandoned
service was more rigorous than the live one. ~30 min to wire back.

### Blood pressure is collected but never reaches the model

- `HealthDataInput` accepts `systolic_bp` / `diastolic_bp`
- `ingestion_service.py:69` stores them
- `anomaly_service.py:40` sets clinical bounds on them
- `ensemble_service.py:54` `FEATURE_COLS` — **contains no blood pressure**

**We predict hypertension risk without using blood pressure.** Also unused by the
model: `blood_oxygen`, `active_minutes`, `water_intake_ml`. Disclose before a
clinician judge finds it.

---

## Audit

Full 76-finding audit (10 domains, severity-graded, with a phased roadmap):
**https://claude.ai/code/artifact/540ff729-6b4f-4fb7-99e5-9b295d0574bb**

Distribution: **6 critical · 25 high · 33 medium · 12 low**

Context on the count: the audit was graded against *production healthcare
software* standards, not hackathon standards. Only ~5–6 findings are visible to a
judge in a 10-minute demo. "No auth" and "no tests" are expected absences in a
hackathon build.

### The 6 criticals

| ID        | Finding                                                                                                                                   |
| --------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `SEC-1` | No authentication —`user_id` is an untrusted query param on every route (IDOR over PHI)                                                |
| `SEC-2` | Prompt injection — uploaded doc text goes into the**system** prompt (`chat_service.py:148`)                                      |
| `COR-1` | Anomaly detection runs**twice** per submission, duplicating every alert (`health_data.py:19` and `:57`) — **10-min fix** |
| `PRF-1` | CPU-bound ML inference runs on the async event loop;`to_thread` used only for mem0                                                      |
| `QA-1`  | No test suite at all — no pytest, no CI, no frontend tests                                                                               |
| `PRD-1` | Core loop never closes —`store_intervention_response()` has zero callers                                                               |

### Highest-value quick wins

- `COR-1` — remove duplicate `detect_anomalies` call · **10 min**
- `COR-5` — `SEVERITY_RANK.get(sev, 0)` guard against `KeyError` · **5 min**
- Kill/relabel the `R²=0.995` badge (`dashboard/page.tsx:663`) · **5 min**
- "Predicted 5-year onset probability" → "Relative risk index" (`:837`) · **5 min**
- Wire causal ATE into `estimated_risk_reduction` · **30 min**

---

## Changes already applied

| Change                                                                                                                                   | File                       |
| ---------------------------------------------------------------------------------------------------------------------------------------- | -------------------------- |
| Added missing`telegram_connections` table (all 7 queries in `telegram_service.py` were hitting a non-existent table)                 | `backend/db/schema.sql`  |
| Fixed false stack claims in PDF export: "Qdrant + mem0" → pgvector, "Apple HealthKit + NHANES III" → Garmin + ICMR; added ensemble row | `dashboard/page.tsx:448` |

---

## Corrections to earlier statements

Recorded so nobody acts on the wrong version:

- **`.env` is NOT committed.** It is gitignored and git has never tracked it.
  An earlier claim that it was leaked is **wrong**. Real issue is narrower:
  no `.env.example`, no rotation, and `Settings` defaults every key to `""`
  so a missing `GROQ_API_KEY` fails at request time instead of at boot.
- **The interactive predictor does not exist** — we believed it did.
- **`estimated_risk_reduction` is LLM-generated**, not computed.

---

## Garmin Connect (owned separately)

- `garminconnect 0.3.2` installed into the `darpanai` conda env.
- Probe script (run this **first**, before writing adapter code):
  `<scratchpad>/garmin_probe.py` — caches tokens, dumps raw JSON, prints field shapes.
- Credentials go in `.env` as `GARMIN_EMAIL` / `GARMIN_PASSWORD`. Never in chat or git.

### API surface (v0.3.2, verified by introspection)

```
Garmin(email, password, is_cn=False, prompt_mfa=None, return_on_mfa=False)
login(tokenstore=None) -> tuple

get_stats_and_body(cdate)        get_hrv_data(cdate)
get_heart_rates(cdate)           get_stress_data(cdate)
get_sleep_data(cdate)            get_all_day_stress(cdate)
get_daily_steps(start, end)   ←  RANGE
get_body_battery(start, end)  ←  RANGE
```

### Key notes

- **`get_daily_steps` and `get_body_battery` take date ranges** → 90 days of
  history in 2 calls, not 180. Nearly eliminates rate-limit risk.
- **`get_hrv_data` exists** → real RMSSD, replacing the fake
  `hrv_rmssd = 65 - |HR-65|` at `ensemble_service.py:231`.
- **Body Battery / `averageStressLevel`** → real HRV-derived stress, replacing the
  crude client-side `deriveStressLevel()` in `mobile/src/services/derivationEngine.ts`.
- **Login is the failure mode, not data reads.** Cache tokens so SSO is hit once.
  Stop after two failed attempts — repeated tries get the venue IP banned.
- Cache every response to disk; demo falls back to cache if the live call fails.
- The watch must have **synced to Garmin Connect** — the API reads Garmin's cloud,
  not the watch. Unsynced = clean auth, empty payloads.
- Sleep/HRV/stats are per-date → add ~1s sleep between calls when backfilling.

### Why the 90-day backfill matters beyond "more data"

It activates features that currently sit dead on a fresh DB:

| Feature               | Requirement               | Status without history                    |
| --------------------- | ------------------------- | ----------------------------------------- |
| z-score anomaly layer | ≥5 readings              | inactive                                  |
| IsolationForest layer | ≥30 readings             | inactive                                  |
| DoWhy causal ATE      | ≥3 joined log↔risk rows | falls back to`_causal_from_shap_priors` |

We currently *say* "DoWhy causal inference" while the code runs SHAP priors.

---

## Decision: retraining

**Tiered — pick one. Tier 1 is worth doing even if we reject the rest.**

| Tier                          | Effort | What we get                                                                                                                                                            |
| ----------------------------- | ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **1 — Calibrate only** | ~2h    | Map existing outputs onto real NHANES population prevalence. Nothing retrained, nothing discarded. Honest claim: scores anchored to real epidemiology. Fixes`MDL-2`. |
| **2 — One real model** | ~5h    | Diabetes only on NHANES (best labels), run beside the ensemble as a clinical baseline. Real AUC on real people.                                                        |
| **3 — Full retrain**   | ~11h   | All three conditions + measured BP as a feature + IDRS benchmark. Kills the synthetic-label criticism outright.**Recommended with 20h.**                         |

**The transformer is not discarded in any tier.** Keep both models:

- Transformer → temporal wearable patterns (Garmin sequences)
- NHANES model → clinically grounded cross-sectional baseline
- Ensemble them, report each separately

### NHANES logistics

- **Free, public, no registration, no application.** CDC. SAS transport (XPT) files
  per cycle, joined on `SEQN`, read with `pandas.read_sas(path, format='xport')`.
- **How much is needed:** ~10–20 outcome events per feature. NHANES adult diabetes
  prevalence ≈13%, so 5,000 adults ≈ 650 cases ≈ 43 events/feature across 15
  features. **5,000 real patients > 50,000 synthetic ones.** Not a scale problem.
- **"Would the old data suffice?"** Our synthetic 50k → **no**, that's the thing
  being fixed. Older *NHANES cycles* → **yes**, pooling is standard: `_H` (2013–14)
  + `_I` (2015–16) + `_J` (2017–18) ≈ 15,000 adults.
- **Cross-sectional, not longitudinal** — will not give 30-day sequences. Don't
  fight it; that's why we keep both models.

Files for the 2017–2018 cycle (verify suffixes against the codebook — `_J` should
be 2017–18, cited from memory):

| File                                 | Provides                                                         |
| ------------------------------------ | ---------------------------------------------------------------- |
| `DEMO_J`                           | age (`RIDAGEYR`), sex (`RIAGENDR`)                           |
| `BMX_J`                            | BMI (`BMXBMI`), waist (`BMXWAIST`), hip (`BMXHIP`) → WHR  |
| `BPX_J`                            | **measured** systolic/diastolic                            |
| `GHB_J` / `GLU_J`                | HbA1c (`LBXGH`), fasting glucose (`LBXGLU`)                  |
| `DIQ_J` / `BPQ_J`                | diabetes dx (`DIQ010`), hypertension dx (`BPQ020`)           |
| `MCQ_J`                            | cardiac events (`MCQ160` series), family history (`MCQ300C`) |
| `SLQ_J` / `PAQ_J` / `DR1TOT_J` | sleep, activity minutes, sugar grams (`DR1TSUGR`)              |

**Expected outcome: AUC 0.78–0.85.** Lower than R²=0.995 and worth vastly more.

**Go/no-go at hour 9.** If NHANES isn't training cleanly, fall back to Tier 1.
Do not let the retrain eat the whole night.

---

## Interactive features to build

**Enabler:** `predict_risk()` runs ~1ms on CPU → brute-force search is viable.

**Build the engine once:** `POST /simulate/whatif` → modified vitals → three
disease scores, **no DB writes**. Everything below is a view on top of it.
Put it behind a separate "Explore" toggle so it can't break the main flow.
Debounce at 300ms (inference still blocks the event loop — `PRF-1`).

| # | Feature                                                                                                                                           | Effort | Value                                                                        |
| - | ------------------------------------------------------------------------------------------------------------------------------------------------- | ------ | ---------------------------------------------------------------------------- |
| 1 | **Goal predictor** — drag steps to 12,000 → "−4.1 pts over 8 weeks"                                                                      | ~1h    | The thing we thought we had. Instantly graspable.                            |
| 2 | **Inverse solver** — "what do I need to reach Low risk?" Brute-force each feature until the category flips. Reports the *cheapest* path. | ~3h    | ⭐**Top originality pick.** Nobody builds this. Calculator → advisor. |
| 3 | **Sensitivity tornado** — perturb each feature ±1, plot sorted bars. The model's local gradient.                                          | ~2h    | ⭐ Best credibility-per-hour. Real XAI, and it sidesteps`COR-2` entirely.  |
| 4 | **Marginal returns curve** — sweep steps 0→20k, show diminishing returns                                                                  | ~1.5h  | Feels clinical, reveals model structure                                      |
| 5 | **Time-to-threshold** — "you cross into High in 7 weeks" (reuses `_simulate_current` drift)                                              | ~1h    | Urgency, cheap                                                               |

**Recommended order:** engine → #2 → #3.

---

## 20-hour plan — 3 people parallel

| Hours  | ML (A)                                                                                        | Backend (B)                           | Frontend (C)                                 |
| ------ | --------------------------------------------------------------------------------------------- | ------------------------------------- | -------------------------------------------- |
| 0–1   | **All:** `COR-1`, `COR-5`, kill R² badge, fix "5-year probability" label, wire ATE |                                       |                                              |
| 1–5   | NHANES download + parse                                                                       | Garmin ingest + 90-day backfill       | what-if endpoint contract + "one lever" hero |
| 5–9   | Feature engineering, merge cycles                                                             | `interventions` table + accept flow | slider wiring + honesty panel                |
| 9–13  | Train, validate, calibrate*(go/no-go at 9)*                                                 | Adherence check-in + outcome compare  | Inverse solver UI                            |
| 13–16 | IDRS benchmark + calibration curve                                                            | Integrate NHANES model into pipeline  | Sensitivity tornado                          |
| 16–18 | **All:** integration, n=4 real team profiles, bug bash                                  |                                       |                                              |
| 18–20 | **All:** two timed run-throughs, backup recordings, Q&A drill                           |                                       |                                              |

### Additions that signal rigor

- **IDRS benchmark** (~2h) — implement the Indian Diabetes Risk Score (MDRF) as a
  baseline and compare on the same held-out set. Almost no student team benchmarks
  against a published clinical standard.
- **Model disagreement as a feature** (~2h) — "Clinical baseline 22%, wearable model
  38% — the gap is your 3-week sleep decline, which a cross-sectional model
  structurally cannot see."
- **Real humans, n=4** (~1h) — every member syncs their actual wearable. Not science,
  but real, and it demos far better than `user_demo_001`.

### Do NOT build

- No fourth disease (answers the wrong question — breadth, not depth)
- No auth, no tests, no job queue (correct for production, invisible to judges)
- Don't productize the Arena — keep it as the demo flourish it already is

---

## Judge Q&A — rehearse out loud

**1. "Did you only cover diabetes and heart rate?"**
Three conditions — diabetes, CVD, hypertension — as three model heads. Heart rate
is an *input*, not an output. A fourth condition is a config change; breadth isn't
the hard part. Telling you *which one behaviour to change* is.

**2. "How accurate is it really?"**
The synthetic-cohort answer above. Architecture validation, not clinical accuracy.
After the retrain: real AUC on real held-out NHANES patients.

**3. "Is that real data?"**
Real Garmin telemetry for inference; synthetic cohort for training (or NHANES after
the retrain). Both stated on the honesty panel. **Never say Apple Watch.**

**4. "How did you compute that risk reduction?"**
Only answerable *after* the ATE fix. Until then it's an LLM guess — fix it first.

**5. "What's next?"**
Phase 1 of the audit roadmap. We have the best answer in the room to this question.

---

## Open items

- [ ] **Confirm the synthetic-label question** with whoever ran the GPU training
- [ ] **Check ZEN Club rules on resubmission** — many events prohibit or require
  disclosure of prior submissions. If allowed, disclose and lead with the delta.
- [ ] Choose retrain tier (recommend **3**, fall back to **1**)
- [ ] Run `garmin_probe.py` and confirm the watch has synced
- [ ] Decide: keep or cut the "Prakriti Stratification" framing (Ayurvedic framing
  beside clinical ML claims can read as unscientific to a medical judge)

### Delta since last submission (for the "what's new" question)

Ensemble v2 (one opaque score → 3 disease-specific heads) · Model Arena ·
Garmin ingestion replacing the dead HealthKit path · two-way Telegram bot ·
document RAG · per-user dynamic causal graph · **+ NHANES grounding and the
interactive what-if engine, if built.**

---

## Roadmap table audit — "Current capability → Future evolution"

Assessment of the 8-row capability/future-scope table researched for the pitch.
**Verified against source, 2026-08-08.**

### ⚠️ First: four of eight "Current capability" claims are overstated

Ambitious *future* scope is fine — judges expect it. **Overstated *present*
capability is what loses Q&A.**

| Claim in left column | Verified reality |
| --- | --- |
| "Real-time **Digital Twin**" | A snapshot scorer. `build_sequence_from_snapshot` tiles one reading 30× (`ensemble_service.py:258`). Nothing longitudinal in the inference path. |
| "**What-If** Simulation" | Does not exist. Three hardcoded scenarios (`IMPROVED_DELTAS`), no user input, no endpoint. |
| "Wearable + **ECG** + lifestyle + **environment**" | **Zero ECG code. Zero environmental code.** Grepped whole repo: no hits for ecg, afib, rhythm, aqi, pollution, weather, latitude/longitude. |
| "**Graph**-RAG patient memory" | Not a graph. mem0 → `pgvector` (vector store, `memory_service.py:62`); doc RAG → `TfidfVectorizer` + `cosine_similarity` (`doc_rag_service.py:34`) — not even embeddings. Also mem0 is empty (zero callers). |

**Action: delete the ECG claim from every slide.** If a judge asks to see ECG
analysis there is nothing to show. Restate row 7 as "vector memory + causal
graph" — both true.

### Verdict on all eight rows

| # | Future evolution | Verdict | Effort | Gimmick? |
| --- | --- | --- | --- | --- |
| 1 | Longitudinal Health Twin | 🔨 **Build now** | ~4h | No — biggest ML win available |
| 2 | Disease-agnostic Risk Engine | ⏳ Future scope | — | Partly — "validated" is load-bearing |
| 3 | Personalized Intervention Simulator | 🔨 **Build first** | ~5h | No — most demoable item |
| 4 | Early Deterioration Detection | ✅ **70% already built** | ~2h | No |
| 5 | Cross-domain Health Intelligence | 🔨 Partial — environment only | ~3h | ECG part is fiction; AQI part is real |
| 6 | Outcome-based Adaptive AI | 🔨 Buildable but **cut** | ~7h | No — best product feature, worst demo |
| 7 | Clinical Health Graph | ⏳ Scoped version only | ~4h | Medium |
| 8 | Population Health Twins | ⏳ B2B no / percentile view yes | ~3h | Mostly, as written |

**Scorecard: 3 rows shippable now · 1 already built (needs surfacing) ·
2 half-real (keep the good half) · 2 genuine future scope.**

### Build these

**Row 1 — Longitudinal Twin** (`MDL-1`, ~4h). Already ~80% built. The transformer
*wants* 30-day sequences; we feed the same day 30× which zeroes every std-dev and
trend feature in the XGBoost layer. Query last 30 days from `health_logs` instead.
Garmin backfill supplies the data. Highest accuracy gain per hour on the table.

**Row 3 — Intervention Simulator** (~5h). The what-if engine + inverse solver.
Fixes a false claim *and* creates the demo surprise. Build `POST /simulate/whatif`
once; goal predictor and inverse solver ride on top. **Do this first — three other
items depend on it.**

**Row 4 — Early Deterioration** (~2h). Already built, just unrecognised:
`anomaly_service.py` layer 2 = personal z-score |z|>2.5σ, layer 3 = IsolationForest.
"Before conventional thresholds are crossed" is exactly z-score vs the hard bounds
in layer 1. Missing piece is **"sustained"** — a single reading currently trips it.
Add a 3-consecutive-days rule. Dead on a fresh DB (needs ≥5 / ≥30 readings) → the
backfill activates it.

**Row 5 — environment, NOT ECG** (~3h). Drop ECG entirely. **AQI is cheap, real,
and India-specific** — free API keyed on city, and the air-quality →
cardiovascular/respiratory link is well established. Add as a *correlational
insight* ("risk rises on high-AQI weeks"), not a model input, so no retrain needed.
**Best originality-per-hour on the table; no other team will have it.**

**Row 8 — the honest version** (~3h). Skip hospitals/insurers — we have one
hardcoded user and no auth (`SEC-1`). But after NHANES we have 5,000–15,000 **real**
people, so show where this user sits in that real distribution: *"73rd percentile
for your age band."* Truthful population intelligence, nearly free as a retrain
byproduct.

### Leave in future scope

**Row 2 — more diseases.** AFib needs rhythm analysis (no data). Sleep apnea needs
overnight SpO2 desaturation *events*; we store a single `blood_oxygen` value.
"Validated" needs labelled training data we don't have for any of them. An
unvalidated 4th head makes the credibility problem *worse*. Also answers breadth
when depth is the differentiator.

**Row 6 — outcome loop.** Philosophically the best feature and the real moat, but a
4-week outcome loop cannot be demoed in 5 minutes — only the mechanism. **Cut it
and use it as the "what's next" answer:** *"we're building the loop that measures
whether our advice worked — that's the dataset nobody has."*

**Row 7 — Clinical Graph.** Fix the claim first. Scoped honest version = add
intervention→outcome edges to the existing causal DAG, which depends on Row 6.

### Allocation (fits inside 20h)

Cannot do NHANES Tier 3 **and** all six buildable rows. This fits:

| Person | Work | Hours |
| --- | --- | --- |
| **A (ML)** | NHANES Tier 3 retrain + IDRS benchmark | ~11h |
| **B (backend)** | what-if engine (3) + longitudinal sequences (4) + sustained detection (2) + AQI (3) | ~12h |
| **C (frontend)** | what-if UI + inverse solver + tornado (5) + hero + honesty panel (2) + percentile view (2) | ~9h |

Plus the shared hour-0 block and ~2h rehearsal. Net result: four table rows
genuinely advanced, one false claim removed, real training data.
