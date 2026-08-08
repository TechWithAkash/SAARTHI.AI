from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime


class HealthDataInput(BaseModel):
    user_id: str
    heart_rate: float = Field(..., ge=30, le=250, description="BPM")
    steps: float = Field(..., ge=0, le=100000, description="Daily steps")
    sleep: float = Field(..., ge=0, le=24, description="Hours of sleep")
    bmi: float = Field(..., ge=10, le=70, description="Body Mass Index")
    stress_level: float = Field(..., ge=1, le=10, description="Stress 1-10")
    diet_score: float = Field(..., ge=1, le=10, description="Diet quality 1-10")
    systolic_bp: Optional[float] = Field(None, ge=70, le=250)
    diastolic_bp: Optional[float] = Field(None, ge=40, le=150)
    blood_oxygen: Optional[float] = Field(None, ge=70, le=100)
    active_minutes: Optional[float] = Field(None, ge=0, le=1440)
    water_intake_ml: Optional[float] = Field(None, ge=0, le=10000)
    source: str = Field(default="manual", pattern="^(manual|apple_health|google_fit|garmin)$")
    # Device-measured metrics that override derived proxies when present.
    # hrv_rmssd replaces the HC-03 heart-rate proxy; sugar_intake_g replaces HC-04.
    hrv_rmssd: Optional[float] = Field(None, ge=1, le=300, description="Measured RMSSD in ms")
    sugar_intake_g: Optional[float] = Field(None, ge=0, le=500, description="Measured sugar intake, grams/day")
    extras: Optional[dict] = Field(None, description="Additional device telemetry (body battery, spo2, …)")


class HealthDataResponse(BaseModel):
    log_id: str
    status: str
    anomalies_detected: bool
    pipeline_triggered: bool
    timestamp: datetime


class RiskResponse(BaseModel):
    user_id: str
    risk_score: float
    risk_category: str
    timestamp: datetime
    top_risk_factors: List[str]
    # Ensemble v2 disease-specific scores (optional for backward compat)
    diabetes_risk: Optional[float] = None
    cvd_risk: Optional[float] = None
    hypertension_risk: Optional[float] = None
    # Saturation disclosure: True when the input's engineered features (e.g. an
    # extreme 30-day spread) pushed the XGBoost heads out of their training
    # distribution, producing a clipped-to-floor/ceiling number rather than a
    # genuine finding. The UI should show a caution state, not trust the score
    # at face value, when this is True.
    model_saturated: Optional[bool] = None
    saturated_after_fallback: Optional[bool] = None


class SimulationScenarios(BaseModel):
    current: List[float]
    improved: List[float]
    optimal: List[float]


class SimulationResponse(BaseModel):
    user_id: str
    scenarios: SimulationScenarios
    timeline_days: List[int]
    projected_risk_reduction: dict
    # Per-disease trajectories: {scenario: {diabetes_risk: [...], ...}}
    by_disease: Optional[dict] = None
    scenario_assumptions: Optional[dict] = None


class WhatIfRequest(BaseModel):
    """
    Interactive counterfactual: change any subset of the modifiable metrics and
    see the projected effect. Unknown keys are reported back in `rejected`
    rather than silently ignored.
    """
    user_id: str
    sleep: Optional[float] = Field(None, ge=0, le=14)
    steps: Optional[float] = Field(None, ge=0, le=50000)
    stress_level: Optional[float] = Field(None, ge=1, le=10)
    diet_score: Optional[float] = Field(None, ge=1, le=10)
    heart_rate: Optional[float] = Field(None, ge=30, le=220)
    bmi: Optional[float] = Field(None, ge=12, le=60)

    def overrides(self) -> dict:
        return {
            k: v for k, v in self.model_dump(exclude={"user_id"}).items()
            if v is not None
        }


class WhatIfResponse(BaseModel):
    user_id: str
    baseline_state: dict
    applied: dict
    rejected: List[str]
    baseline: dict
    counterfactual: dict
    delta: dict
    risk_category: str
    model_saturated: bool = False
    note: str


class SHAPContributions(BaseModel):
    """
    Attribution per tracked vital. All optional with 0.0 defaults: the ensemble
    explains 12 ICMR features which map onto these 6, and a given run may not
    populate every one.
    """
    heart_rate: float = 0.0
    steps: float = 0.0
    sleep: float = 0.0
    stress_level: float = 0.0
    diet_score: float = 0.0
    bmi: float = 0.0
    age: float = 0.0


class InsightsResponse(BaseModel):
    user_id: str
    shap_contributions: SHAPContributions
    causal_chain: str
    primary_cause: str
    # What SHAP actually covers — the ensemble is Transformer + XGBoost, and
    # TreeExplainer only sees the XGBoost half.
    explains: Optional[str] = None
    explained_fraction: Optional[float] = None
    per_disease: Optional[dict] = None
    icmr_contributions: Optional[dict] = None


class Recommendation(BaseModel):
    priority: int
    action: str
    reason: str
    impact: str
    timeframe: str
    estimated_risk_reduction: Optional[float] = None
    causal_mechanism: Optional[str] = None
    # Provenance for estimated_risk_reduction: "causal_ate" when it comes from
    # the DoWhy/regression ATE, "unavailable" when we could not ground it and
    # therefore refuse to show a number. Never an LLM guess.
    risk_reduction_source: Optional[str] = None
    causal_factor: Optional[str] = None


class AgentTraceStep(BaseModel):
    step: int
    type: str  # "tool_call" | "synthesis"
    tool: Optional[str] = None
    query: Optional[dict] = None
    summary: Optional[str] = None
    content: Optional[str] = None


class AgentMeta(BaseModel):
    reasoning: str
    primary_lever: str
    agent_confidence: str  # "high" | "medium" | "low"
    tools_called: List[str]
    n_tool_calls: int
    trace: List[AgentTraceStep]


class RecommendResponse(BaseModel):
    user_id: str
    recommendations: List[Recommendation]
    method: Optional[str] = None
    risk_score: Optional[float] = None
    generated_at: Optional[datetime] = None
    agent: Optional[AgentMeta] = None


class Alert(BaseModel):
    id: str
    metric: str
    value: float
    severity: str
    message: str
    timestamp: datetime


class AlertsResponse(BaseModel):
    user_id: str
    alerts: List[Alert]
