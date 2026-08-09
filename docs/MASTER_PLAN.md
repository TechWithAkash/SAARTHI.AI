./

# MASTER PLAN — two parallel tracks, remaining 16 hours (Sat 7:00pm → Sun 11:00am)

Hackathon: Sat 12pm → Sun 11am (23h total). **7h spent, 16h left.**
**Two people, two machines from here:** you on the **MacBook Pro M4** own
the ML track; your teammate on the other machine owns the sprint track.
This is good news — running in parallel, both tracks finish and merge at
**checkpoint #2, 4:15am**, leaving a genuine surplus before the 11am deadline.
Don't waste that surplus on more scope by default — see the back half.

**Repo coordination:** work on separate branches, merge at the sync
checkpoints below, not continuously. The one real collision risk is the
dashboard/insights frontend page where AgentTrace, the tornado, and the ML
track's arbitration panel all need to get inserted — whoever lands there
first adds a clearly delimited block, the other inserts alongside it, don't
both touch the same file live at the same time.

**0. 7:00pm — 10 min joint sync before splitting.** Both need a shared
mental model of `ensemble_service.py` (`FEATURE_COLS`, the 3 XGBoost heads,
the meta-learner) before working on adjacent code independently. Do this
together, then split.

---

# ML TRACK — you, MacBook Pro M4

## E. 7:10–8:40pm (1.5h) — wire in `ICMRRuleScorer` — YOUR FLOOR, ALL 3 DISEASES

From `VIT hackathon/darpan_ensemble_deploy/icmr_rule_scorer.py`. Deterministic
point-scoring, real published citations **per disease already in the
recovered code's own comments**: diabetes → IDRS (Mohan et al. 2005) + MDRF;
CVD → Framingham + INTERHEART (South Asian-adapted); hypertension → JNC-8 /
Indian HTN guidelines. Port from its 9-feature schema onto the live
12-feature `FEATURE_COLS`, surface as a 4th visible signal for all three
conditions. No dependency on the sprint track — start immediately.

**Do this first, protect it above everything else in your track.** This is
what makes the "committed to the judge on hypertension and CVD" promise true
no matter what happens with NHANES tonight — it's real, cited, and it
doesn't depend on a dataset download or a training run succeeding.

## F. 8:40pm–1:40am (5h) — NHANES retrain, ALL THREE conditions + Arbitration Panel

Promoted from "diabetes only" — all three diseases are core scope now,
because you've committed to the judge on hypertension and CVD specifically.
Each has a real NHANES-derived label already identified in your own prior
research: diabetes → `DIQ010`; hypertension → measured BP (`BPX_J`) or
`BPQ020`; CVD → composite of `MCQ160` series (heart attack/CHD/angina/
stroke). All from the same 2017–18 `_J` cycle, joined on `SEQN` — one
download covers all three.

**F1a — 8:40–9:40pm (1h) — download + parse + join, once for all three:**
`DEMO_J`, `BMX_J`, `BPX_J`, `GHB_J`/`GLU_J`, `DIQ_J`, `BPQ_J`, `MCQ_J`,
`SLQ_J`/`PAQ_J`/`DR1TOT_J`.

**F1b/c/d — 9:40pm–11:55pm (2.25h, ~45min each) — train one model per
condition:** XGBoost or logistic, minutes each on M4 CPU. Report each AUC
honestly (expect 0.78–0.85 range, varies per condition). Cite: diabetes →
**NHANES+XGBoost (Archives of Med Sci)**; hypertension → **NHANES+Stacking
(Frontiers)**.

**Per-disease go/no-go at 11:55pm — this is the critical rule:** if any one
of the three doesn't train cleanly (data too sparse, label too imbalanced,
whatever), **that disease falls back to its `ICMRRuleScorer` score from
block E as its real-data-backed answer, not to a fabricated NHANES number.**
Label it correctly in the panel either way — "NHANES-trained baseline" vs
"clinical guideline score (Framingham/INTERHEART)" are both honest and both
real; silently presenting one as the other is a Rule 0 violation. You are
not blocked from covering all three tonight even if NHANES only converges
for one or two of them.

**F2 — 11:55pm–12:40am (0.75h) — deterministic arbitration factors, all
three:** Same formula per disease — (a) provenance (synthetic ensemble vs
real NHANES vs guideline rule-score, whichever actually produced the
number), (b) signal type (ensemble's 30-day trajectory if real Garmin
history exists — check with teammate), (c) divergence
`|ensemble_score - baseline_score|`. Compute, never hand raw scores to the
LLM to reason about from scratch — repeats the `HC-11` mistake.

**F3 — 12:40–1:40am (1h) — narrate + panel UI, loop over 3 diseases:**
Feed only the F2 factors per disease to the existing Groq client, strictly
phrasing not inventing. Panel shows three disease rows, each with its own
verdict and its own honestly-labeled provenance. Build as its own
component, insert into the shared dashboard page at sync checkpoint #1.

## G. 1:40–2:10am (0.5h) — IDRS benchmark (diabetes only, correctly)

IDRS is diabetes-specific by name — don't force a parallel "IDRS-equivalent"
benchmark for CVD/hypertension where none exists as cleanly. Compare
diabetes model against IDRS on the NHANES held-out set. Honest scope, not a
gap — say so if asked, it's a defensible answer on its own.

---

## SYNC CHECKPOINT #1 — now async, ~1:00–2:10am while ML track finishes F

Sprint track reaches its own first checkpoint-worthy point around
12:40–1:00am (end of block D) — don't block waiting on the ML track, which
now runs later due to the three-disease expansion. Merge branches whenever
both have a stable commit. Confirm Garmin status — if real profiles exist,
wire at least one into the arbitration panel. Resolve the shared
dashboard-page insertion before both tracks touch it further.

---

## STRETCH (ML track) — 2:10–4:15am (~2h, until sprint track's J finishes) — pick in this order

1. **Calibration curve for `HC-01`** (`DIABETES_SCALE`/`CVD_SCALE=0.73`) —
   real NHANES prevalence data from F now exists; use it to justify the
   0.73 or replace it with a real number. Last major undefended constant on
   the ML side.
2. If any disease fell back to the rule scorer at the F go/no-go, use spare
   time here to retry NHANES for it with a simpler label definition —
   second attempt, not a blocker for anything else.
3. If solid: help the sprint track — Garmin edge cases and AgentTrace both
   touch `ensemble_service.py` context you now know best.

---

# SPRINT TRACK — teammate, other machine

## A. 7:10–8:40pm (1.5h) — BP-1: fix the model mismatch

`explain_service.py`/`simulation_service.py` load the legacy 7-feature
`risk_model.pkl` while the dashboard score comes from the ensemble.
Repoint both at the ensemble. SHAP over the 3 XGBoost specialist heads
(fast, honest — label it "explains the XGBoost specialists"), not
`KernelExplainer` (too slow live). Bundle in: kill the `R²=0.995` badge,
relabel "predicted 5-year onset probability" → "relative risk index,"
verify BP-5's stack-claim fixes are actually in this working tree.

## B. 8:40–11:10pm (2.5h) — Garmin integration (BP-6)

1. `garmin_probe.py` first — confirm auth, cache tokens, real field shapes
   before adapter code.
2. `.env` + `GARMIN_EMAIL`/`GARMIN_PASSWORD` + `config.py` fields.
3. `models/health.py:19` — add `garmin` to the source pattern.
4. Schema: JSONB `extras` column on `health_logs`, not a full migration.
5. Adapter: `fetch_core()` + `fetch_enhancements()`.
6. `get_daily_steps`/`get_body_battery` take date ranges (2 calls, not 90)
   — real backfill is fast. Get ≥14 days per synced watch.
7. Kills `HC-03` (fake HRV) and `HC-05` (`[day]*30`) for backfilled users.

## C. 11:10–11:40pm (0.5h) — AQI/CVD (your new ask)

OpenAQ, advisory factor next to the CVD score, not folded into
`composite_risk` silently. Static fallback JSON for demo safety.

## D. 11:40pm–12:40am (1h) — BP-3 + BP-4

Wire `recommendation_service.py`'s real `abs(ate)` into
`estimated_risk_reduction`. Fix `causal_service.py:460`'s method label.
Raise `MIN_HISTORY` once real Garmin history exists.

---

## SYNC CHECKPOINT #1 — 12:40–1:00am (join the ML track's checkpoint, runs long by 10 min — fine)

---

## H. 1:00–2:00am (1h) — AgentTrace live-render

Component + backend SSE both already exist (`AgentTrace.tsx`,
`cognitive_agent_service.py:345`) — wiring, not building. **Direct fix for
"originality 5/10, best engineering invisible in the demo"** — the exact
criterion that cost the placement last time, cheapest fix on the list
relative to its scoring impact. Do not let this slip.

## I. 2:00–3:15am (1.25h) — sensitivity tornado

Perturb each feature ±1, plot sorted bars — real local-gradient XAI,
sidesteps the COR-2 explainability gap. Shared what-if engine
(`predict_risk` ~1ms, brute-force viable) once, tornado consumes it.
Inverse solver stays out of scope.

## J. 3:15–4:15am (1h) — scoped hardening

- Per-stage `try`/`except` in `run_full_pipeline` — ~20 min, do not skip.
- `pipeline_triggered` set from what actually completed.
- Empty-payload path tested end-to-end (BP-2).
- Sync real profiles from every teammate present.
- `grep -rn "HARDCODED\[" | wc -l` == `HARDCODE_LEDGER.md` row count.

---

# JOINT BACK HALF — both tracks converge

## SYNC CHECKPOINT #2 — 4:15–4:45am (both)

Full merge. End-to-end smoke test: submit real data → risk score →
explanation panel → arbitration panel → simulation → recommendations →
AgentTrace visible. This is the first moment everything built tonight runs
together — budget real time for it, don't rush it.

## REST WINDOW — 4:45–7:30am (2.75h) — use this, don't skip it by default

Both tracks land around 4:15am with the 11am deadline still 6.75h away.
**That surplus is real — the highest-leverage use of some of it is rest,
not more features.** Last time's actual loss was Q&A performance (5/10),
not missing scope. Recommend: split it — one person sleeps 4:45–7:00am
while the other stays on light watch for anything that broke post-merge,
then swap for a short window, or both rest if the smoke test in checkpoint
#2 was clean. This is a judgment call on the night, not a hard rule — but
default to using it, not defaulting to more building.

## DEBUG BUFFER — 7:30–9:30am (2h) — MUST, genuinely open

Real open slack, not a task list. Fix whatever the smoke test or overnight
work actually surfaced. If everything's clean and there's time left, pull
from the cut list below — don't invent new scope.

## REHEARSAL — 9:30–10:45am (1.25h) — MUST

Multiple timed run-throughs — the parallel-track surplus makes more than
one realistic tonight, unlike the solo-track version of this plan. Record
a backup video (BP-9: ngrok/Garmin/Groq/Telegram all fail independently at
venues). Drill Q&A from `hinton_presentation_script.md` — both people
should be able to give the honest data-provenance answer cold, not just
whoever built it.

## BUFFER / SUBMIT — 10:45–11:00am

---

# If either track falls behind — cut in this order

**ML track:** calibration curve → G (IDRS) → F3 panel UI (keep F1+F2 for
the AUC numbers alone, report verbally) → individual F1b/c/d training runs
that miss their go/no-go fall back to `ICMRRuleScorer`, per-disease, per
the rule already in block F — **this is not a cut, it's the designed
fallback, and it's how "100% coverage on all three" stays true even under
time pressure.**

**Sprint track:** I (tornado) → C (AQI) → D (BP-3/BP-4).

**Never cut, either track: A (BP-1), B (Garmin core), E (`ICMRRuleScorer` —
this is the floor that makes the hypertension/CVD commitment true no matter
what else slips), F2 (arbitration factors, for whichever diseases have a
number by then), H (AgentTrace), J (hardening basics), checkpoint #2, debug
buffer, rehearsal.** These are what turn "we built something impressive"
into "we can defend it live and show it working on real data" — the exact
gap that lost last time.
