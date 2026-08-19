# SAARTHI.AI — Smart AI for Adaptive Risk Tracking & Health Intelligence

<div align="center">

![SAARTHI.AI Banner](https://img.shields.io/badge/SAARTHI.AI-Preventive%20Health%20Intelligence-00B4D8?style=for-the-badge&logo=heart&logoColor=white)

[![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16.2.4-black?style=flat-square&logo=next.js&logoColor=white)](https://nextjs.org)
[![React Native](https://img.shields.io/badge/React%20Native-Expo%2054-61DAFB?style=flat-square&logo=react&logoColor=black)](https://expo.dev)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.3.1-EE4C2C?style=flat-square&logo=pytorch&logoColor=white)](https://pytorch.org)
[![XGBoost](https://img.shields.io/badge/XGBoost-2.0.3-217346?style=flat-square&logo=xgboost&logoColor=white)](https://xgboost.readthedocs.io)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-336791?style=flat-square&logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![Groq](https://img.shields.io/badge/LLM-Groq%20Llama%203.3-F55036?style=flat-square&logo=meta&logoColor=white)](https://groq.com)
[![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)

*An enterprise-grade, privacy-first preventive healthcare intelligence platform that bridges the gap between consumer wearables (Garmin Connect) and clinical-grade predictive modeling.*

</div>

---

## 📑 Table of Contents

- [Overview](#-overview)
- [System Architecture & Data Flow](#-system-architecture--data-flow)
- [Key Features](#-key-features)
  - [1. DarpanEnsemble v2 ML Engine](#1-darpanensemble-v2-ml-engine)
  - [2. Explainable AI (XAI) & Causal Inference](#2-explainable-ai-xai--causal-inference)
  - [3. 120-Day Simulation & Real-Time Counterfactuals](#3-120-day-simulation--real-time-counterfactuals)
  - [4. Tri-Channel Grounded AI Assistant](#4-tri-channel-grounded-ai-assistant)
  - [5. 4-Step Cognitive Recommendation Agent](#5-4-step-cognitive-recommendation-agent)
  - [6. Garmin Connect Hardware Sync](#6-garmin-connect-hardware-sync)
  - [7. Environmental Telemetry (AQI & Weather)](#7-environmental-telemetry-aqi--weather)
  - [8. Independent Clinical Validation Study](#8-independent-clinical-validation-study)
  - [9. Omnichannel Platform (Web, Mobile, Telegram)](#9-omnichannel-platform-web-mobile-telegram)
- [Tech Stack](#-tech-stack)
- [Repository Structure](#-repository-structure)
- [API Reference](#-api-reference)
- [Getting Started & Installation](#-getting-started--installation)
  - [Prerequisites](#prerequisites)
  - [Environment Configuration](#environment-configuration)
  - [Automated Startup (`run.sh`)](#automated-startup-runsh)
  - [Manual Setup](#manual-setup)
- [Research & Clinical Citations](#-research--clinical-citations)
- [Safety & Medical Disclaimer](#-safety--medical-disclaimer)

---

## 🌟 Overview

Non-communicable diseases (NCDs) such as **Type 2 Diabetes**, **Cardiovascular Disease (CVD)**, and **Hypertension** develop silently over years before clinical diagnosis. While millions of people wear smartwatches tracking heart rate, sleep stages, stress levels, and daily movement, this raw data is rarely translated into clinically meaningful, forward-looking preventive intelligence.

**SAARTHI.AI** (Smart AI for Adaptive Risk Tracking & Health Intelligence) transforms continuous physiological signals from Garmin wearables and self-reported health check-ins into:
1. **Dynamic multi-disease risk probabilities** using a multi-model sequence + tree ensemble.
2. **Transparent feature attributions and causal mechanisms** using SHAP values and DoWhy Directed Acyclic Graphs (DAGs).
3. **Actionable 120-day forward projections** with sub-10ms counterfactual "what-if" modeling.
4. **Clinical-grade, contextual AI guidance** grounded across live user vitals, long-term semantic memory (`pgvector`), and published clinical literature (ICMR, WHO, ADA, AHA).

---

## 🏗 System Architecture & Data Flow

```mermaid
flowchart TD
    subgraph INGESTION["1. Data Ingestion Layer"]
        G[Garmin Connect API] --> |Sync Daily Vitals| HL[(PostgreSQL health_logs)]
        M[Manual Check-in UI] --> |Log Daily Metrics| HL
        TG[Telegram Bot Check-in] --> |Log via Chat| HL
        ENV[Open-Meteo AQI / Weather] --> |Environmental Context| HL
    end

    subgraph PIPELINE["2. Asynchronous Analytical Pipeline (FastAPI)"]
        HL --> ANOM[Isolation Forest Anomaly Detection]
        HL --> FE[36-D Feature Engineering & Rolling Window]
        FE --> ENS[DarpanEnsemble v2 ML Engine]
        ENS --> |Risk Scores| RS[(PostgreSQL risk_scores)]
        
        FE --> SHAP_MOD[SHAP TreeExplainer Attributions]
        FE --> DOWHY_MOD[DoWhy Causal DAG Inference]
        SHAP_MOD & DOWHY_MOD --> INS[(PostgreSQL insights)]
        
        FE --> SIM[120-Day Trajectory Simulation]
        SIM --> SIM_DB[(PostgreSQL simulations)]
        
        HL --> MEM[mem0 Vector Embeddings via MiniLM]
        MEM --> PGV[(PostgreSQL pgvector memory)]
    end

    subgraph REASONING["3. Clinical Reasoning & AI Layer"]
        RS & INS & PGV --> COG[4-Step Cognitive Agent via Groq Llama 3.3]
        RAG_CORPUS[ICMR / WHO / ADA Medical Guidelines] --> TFIDF[TF-IDF & Document RAG]
        USER_PDF[Uploaded Lab Reports via pdfplumber] --> DOC_RAG[Document Vector RAG]
        TFIDF & DOC_RAG --> COG
        COG --> REC[(PostgreSQL recommendations)]
    end

    subgraph CLIENTS["4. Omnichannel Delivery Layer"]
        RS & SIM_DB & INS & REC --> WEB[Next.js 16 Dashboard & AuraChat]
        RS & SIM_DB & INS & REC --> MOB[Expo React Native Mobile App]
        ANOM & REC --> BOT[Telegram Notification & Alert Bot]
    end
```

---

## 🚀 Key Features

### 1. DarpanEnsemble v2 ML Engine
- **Sequence + Specialist Architecture**: Combines a PyTorch sequence Transformer with three specialized gradient-boosted models (**XGBoost** for Diabetes, CVD, and Hypertension) and a **Ridge Regression Meta-Learner**.
- **36-Dimensional Feature Engineering**: Computes rolling 7-day, 14-day, and 30-day means, standard deviations, min/max, rate-of-change trends, and threshold breach counts across 5 core vitals (*steps, sleep duration, stress levels, diet quality, resting heart rate*).
- **Out-of-Distribution Saturation Check (`XGB_SATURATION_MARGIN`)**: Detects when incoming vital combinations deviate from the learned distribution, surfacing transparent confidence intervals to prevent false precision in clinical scoring.

### 2. Explainable AI (XAI) & Causal Inference
- **SHAP Feature Attributions**: Unpacks every prediction into per-feature risk impact percentages (e.g., *“High resting HR contributed +14.2% to CVD risk, while 8,500 daily steps contributed -9.1%”*).
- **DoWhy Causal Directed Acyclic Graphs (DAG)**: Moves beyond pure correlation to estimate true causal average treatment effects (ATE). Answers clinical queries like: *“What is the causal impact of increasing sleep by 1.5 hours on systolic blood pressure risk?”*

### 3. 120-Day Simulation & Real-Time Counterfactuals
- **Forward Trajectory Modeling**: Projects risk trajectory curves over 120 days across three scenarios:
  - `Current`: Baseline trajectory based on existing lifestyle habits.
  - `Improved`: Realistic +15% incremental improvements.
  - `Optimal`: Clinically recommended targets (e.g. 10,000 steps, 7.5h sleep, stress < 3.0).
- **Sub-10ms Interactive What-If Counterfactuals (`POST /simulate/whatif`)**: Debounced endpoint computing real-time delta calculations as users slide hypothetical changes in steps, sleep, stress, or diet.

### 4. Tri-Channel Grounded AI Assistant
The conversational assistant (mounted globally via `AuraChat` and on `/chat`) is grounded with three strictly isolated context channels to prevent hallucinations:
1. **Direct Live SQL State Injection**: Directly queries the user's latest vitals, risk metrics, and top SHAP drivers into the LLM system prompt.
2. **Long-Term Semantic User Memory**: Utilizes `mem0` backed by PostgreSQL `pgvector` and HuggingFace MiniLM embeddings to remember user preferences, medical history, and habit shifts across sessions.
3. **Medical Guideline & Document RAG**: TF-IDF retrieval over an evidence-based corpus of medical guideline literature (`guideline_corpus/` containing ICMR, WHO, AHA, and ADA guidelines) plus user-uploaded lab reports extracted with `pdfplumber`.

### 5. 4-Step Cognitive Recommendation Agent
Powered by **Groq** (`llama-3.3-70b-versatile` / `mixtral-8x7b-32768`), executing a structured 4-step clinical chain of thought:
1. **Analyze**: Evaluate physiological anomalies and highest-contributing SHAP risk factors.
2. **Prioritize**: Identify the single highest-leverage lifestyle intervention.
3. **Formulate**: Generate actionable, culturally-adapted micro-interventions (e.g., diet, walking, sleep hygiene).
4. **Project**: Calculate expected risk point reductions backed by causal inference.

### 6. Garmin Connect Hardware Sync
- Direct server-side integration via `python-garminconnect`.
- Safe disk-cached OAuth sessions (`.garmin_tokens/` and `.garmin_cache/`) with strict rate limiting (`garmin_max_login_attempts`) to prevent account lockouts.
- Automatic daily ingestion of total steps, sleep architecture, stress scores, resting heart rate, and body battery metrics.

### 7. Environmental Telemetry (AQI & Weather)
- Real-time environmental tracking via Open-Meteo & OpenAQ APIs.
- Captures PM2.5, PM10, AQI, temperature, and humidity for the user's geographical location.
- Correlates environmental pollution spikes with acute cardiopulmonary and hypertensive strain.

### 8. Independent Clinical Validation Study
- Located in `ml_validation/`, benchmarking models on real **NHANES** (National Health and Nutrition Examination Survey) data against published clinical risk calculators (**IDRS** - Indian Diabetes Risk Score, Framingham Risk Score).
- Live performance dashboard accessible via `/validation` in the web frontend.

### 9. Omnichannel Platform (Web, Mobile, Telegram)
- **Web**: Next.js 16 (React 19, Tailwind CSS, Recharts, Lucide Icons, Server-Sent Events streaming).
- **Mobile**: React Native & Expo 54 with custom health charts, offline caching, and biometric theme tokens.
- **Telegram Bot**: Long-polling asynchronous bot for daily health check-ins, threshold alerts, and instant risk queries.

---

## 💻 Tech Stack

| Domain | Technologies |
|---|---|
| **Backend & API** | Python 3.11+, FastAPI, Uvicorn, Pydantic v2, Asyncpg, Python-dotenv |
| **Machine Learning** | PyTorch, XGBoost, Scikit-Learn, Joblib, NumPy, Pandas |
| **Explainability & Causality** | SHAP (TreeExplainer / KernelExplainer), DoWhy Causal Graphs |
| **LLM & Reasoning** | Groq API (`llama-3.3-70b-versatile`), HTTPX (Server-Sent Events) |
| **Memory & Embeddings** | mem0, HuggingFace Sentence-Transformers (`all-MiniLM-L6-v2`), PyTorch |
| **Databases** | PostgreSQL 15+ with `pgvector` extension |
| **Wearables & Ingestion** | `garminconnect` (Garmin Connect OAuth & Telemetry), `pdfplumber` |
| **Frontend (Web)** | Next.js 16.2 (App Router), React 19, TypeScript, Tailwind CSS v4, Recharts, Lucide React |
| **Mobile (iOS/Android)** | Expo 54, React Native 0.81, React Navigation, React Native Chart Kit |
| **Messaging & Bot** | Python-Telegram-Bot / HTTPX asynchronous long-polling |

---

## 📂 Repository Structure

```
├── backend/                            # FastAPI backend application
│   ├── config.py                       # Pydantic environment & application settings
│   ├── main.py                         # FastAPI initialization, CORS, lifespan & router mounting
│   ├── db/
│   │   ├── postgres.py                 # Asyncpg connection pooling & database lifecycle
│   │   └── schema.sql                  # PostgreSQL table schemas (vitals, risks, memory, alerts)
│   ├── models/                         # Pydantic request/response schemas
│   │   ├── health.py                   # Health logs, simulation, & what-if schemas
│   │   └── risk.py                     # Risk and SHAP response models
│   ├── routes/                         # API route endpoints
│   │   ├── alerts.py                   # Anomaly threshold & alert management
│   │   ├── arena.py                    # Multi-model benchmarking comparison
│   │   ├── chat.py                     # Streaming chat & PDF upload endpoints
│   │   ├── environment.py              # AQI & meteorological context endpoints
│   │   ├── garmin.py                   # Garmin Connect login & sync endpoints
│   │   ├── health_data.py              # Ingestion pipeline & timeline retrieval
│   │   ├── insights.py                 # SHAP attributions & DoWhy causal endpoints
│   │   ├── memory.py                   # mem0 long-term memory queries
│   │   ├── profile.py                  # User demographic & medical baseline profile
│   │   ├── rag.py                      # Clinical guidelines RAG search
│   │   ├── recommend.py                # Cognitive agent recommendations (SSE stream)
│   │   ├── risk.py                     # Current & historical composite risk scores
│   │   ├── simulate.py                 # 120-day projections & /simulate/whatif counterfactual
│   │   └── telegram.py                 # Telegram bot linking & token generation
│   ├── services/                       # Core ML, analytical, and domain logic
│   │   ├── air_quality_service.py      # OpenAQ / Open-Meteo environmental integration
│   │   ├── anomaly_service.py          # Isolation Forest anomaly scoring
│   │   ├── arena_service.py            # Model Arena benchmarking logic
│   │   ├── causal_service.py           # DoWhy Causal DAG formulation & ATE estimation
│   │   ├── chat_service.py             # Grounded chat streaming with 3-channel context
│   │   ├── cognitive_agent_service.py  # 4-step Groq clinical recommendation pipeline
│   │   ├── doc_rag_service.py          # Document vector RAG for lab reports
│   │   ├── ensemble_service.py         # DarpanEnsemble v2 sequence + XGBoost + Meta-learner
│   │   ├── explain_service.py          # SHAP TreeExplainer feature attributions
│   │   ├── garmin_service.py           # Garmin OAuth session handling & telemetry mapping
│   │   ├── ingestion_service.py        # Pipeline orchestrator (DB -> ML -> SHAP -> mem0)
│   │   ├── memory_service.py           # mem0 pgvector semantic user memory
│   │   ├── pdf_extraction.py           # pdfplumber clinical lab report parser
│   │   ├── personalized_rag_service.py # TF-IDF guideline retrieval service
│   │   ├── recommendation_service.py   # Recommendation retrieval & caching
│   │   ├── risk_service.py             # Risk calculation orchestration
│   │   ├── simulation_service.py       # 120-day forward simulation & counterfactual engine
│   │   └── telegram_service.py         # Asynchronous Telegram bot polling & notifications
├── frontend/                           # Next.js 16 Web Dashboard
│   ├── app/
│   │   ├── (auth)/                     # Authentication & login views
│   │   ├── (dashboard)/                # Dashboard views
│   │   │   ├── alerts/                 # Health alerts & anomaly history
│   │   │   ├── arena/                  # ML Model Arena benchmark comparison
│   │   │   ├── chat/                   # Dedicated clinical AI conversational interface
│   │   │   ├── dashboard/              # Primary health analytics & vitals dashboard
│   │   │   ├── insights/               # SHAP feature attributions & causal DAG viewer
│   │   │   ├── recommend/              # 4-step Cognitive Agent recommendations
│   │   │   ├── settings/               # Profile, Garmin credentials, & notification config
│   │   │   ├── simulation/             # 120-day trajectory & interactive what-if sliders
│   │   │   └── validation/             # NHANES clinical validation study dashboard
│   │   └── layout.tsx                  # Global root layout & theme wrappers
│   ├── components/                     # Reusable React UI components
│   │   ├── AuraChat.tsx                # Globally mounted floating AI assistant
│   │   ├── RiskCard.tsx                # Disease-specific risk probability display
│   │   ├── Sidebar.tsx                 # Dashboard navigation drawer
│   │   └── WhatIfSimulator.tsx         # Interactive counterfactual slider widget
│   └── lib/api.ts                      # Typed client-side API SDK
├── mobile/                             # Expo / React Native Mobile Application
│   ├── src/
│   │   ├── screens/                    # Mobile tab screens (Insights, Vitals, Assistant, Sync)
│   │   ├── components/                 # Native UI widgets, risk meters, & vital tiles
│   │   ├── services/                   # Mobile API client & offline storage
│   │   ├── theme.ts                    # Design system color tokens & typography
│   │   └── Navigation.tsx              # Bottom tab navigator configuration
│   └── App.tsx                         # Mobile entry point
├── darpan_ensemble_v2_12feature/       # Serialized PyTorch & XGBoost model weights
├── guideline_corpus/                   # Evidence-based medical guidelines (ICMR, WHO, ADA, AHA)
├── ml_validation/                      # NHANES survey dataset validation & benchmark scripts
├── docs/                               # Engineering documentation & architecture specifications
├── rag.py                              # Core TF-IDF guideline retrieval module
├── requirements.txt                    # Python dependencies
├── run.sh                              # Complete multi-service startup script with pre-flight port checks
└── ARCHITECTURE.md                     # Detailed system lifecycle and component architecture
```

---

## 📡 API Reference

### Core Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/health-data` | Ingest daily physiological vitals & triggers the full analytical pipeline |
| `GET` | `/health-data/{user_id}/timeline` | Retrieve historical timeseries of vitals and anomaly flags |
| `GET` | `/risk?user_id={id}` | Get current composite & per-disease risk probabilities |
| `GET` | `/risk/history?user_id={id}` | Retrieve historical risk progression over time |
| `GET` | `/insights?user_id={id}` | Fetch SHAP feature attributions & DoWhy causal DAG analysis |
| `GET` | `/simulate?user_id={id}` | Retrieve 120-day forward trajectory projections |
| `POST` | `/simulate/whatif` | Real-time counterfactual calculation for modified lifestyle vitals |
| `GET` | `/recommend?user_id={id}` | Retrieve latest recommendations generated by the Cognitive Agent |
| `GET` | `/recommend/stream?user_id={id}` | Stream 4-step Cognitive Agent reasoning in real time via SSE |
| `POST` | `/chat/stream` | Multi-turn conversational health assistant stream (SSE) |
| `POST` | `/chat/upload` | Upload and vectorize PDF clinical reports via `pdfplumber` |
| `GET` | `/garmin/status?user_id={id}` | Check Garmin Connect authentication and sync state |
| `POST` | `/garmin/sync?user_id={id}` | Force instantaneous sync of wearable telemetry |
| `GET` | `/environment/current` | Retrieve live AQI, PM2.5, and meteorological data for city |
| `GET` | `/arena/models` | Retrieve Model Arena benchmark metrics across architectures |
| `GET` | `/health` | Application health check endpoint |

---

## ⚡ Getting Started & Installation

### Prerequisites
- **Python**: `3.11+` (Conda recommended)
- **Node.js**: `18.x` or `20.x+` & `npm`
- **PostgreSQL**: `15+` with the [`pgvector`](https://github.com/pgvector/pgvector) extension enabled
- **Groq Cloud API Key**: For LLM reasoning and Cognitive Agent recommendations ([Get key here](https://console.groq.com))

---

### Environment Configuration

Create a `.env` file in the root directory:

```env
# Database Configuration
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/darpanai_db

# Groq LLM API (Required for Chat & Cognitive Agent)
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile

# Garmin Connect Integration (Optional for live device testing)
GARMIN_EMAIL=your_garmin_account@example.com
GARMIN_PASSWORD=your_garmin_password
GARMIN_TOKEN_STORE=.garmin_tokens
GARMIN_MAX_LOGIN_ATTEMPTS=2

# Environmental Data (Optional, falls back to built-in stations)
OPENAQ_API_KEY=your_openaq_api_key
DEFAULT_CITY=Mumbai

# Telegram Bot (Optional for push alerts)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
```

---

### Automated Startup (`run.sh`)

We provide a comprehensive startup script that performs pre-flight socket collision checks, activates the Python environment, starts the FastAPI backend, and launches the Next.js frontend:

```bash
chmod +x run.sh
./run.sh
```

- **Backend API**: `http://localhost:8000` (Swagger UI at `http://localhost:8000/docs`)
- **Frontend Web UI**: `http://localhost:3000`

---

### Manual Setup

#### 1. Database Setup
```bash
# Ensure PostgreSQL is running, then create database
createdb darpanai_db

# Initialize tables and pgvector extension
psql -d darpanai_db -f backend/db/schema.sql
```

#### 2. Backend Setup
```bash
# Create and activate virtual environment
conda create -n darpanai python=3.11 -y
conda activate darpanai

# Install dependencies
pip install -r requirements.txt

# Run FastAPI backend from repo root
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 3. Frontend Web Setup
```bash
cd frontend
npm install
npm run dev
```

#### 4. Mobile App Setup
```bash
cd mobile
npm install
npx expo start -c
```

---

## 📚 Research & Clinical Citations

SAARTHI.AI's clinical thresholds and benchmark models are informed by published medical and epidemiological literature:

1. **Indian Diabetes Risk Score (IDRS)**: Mohan, V., et al. (2005). *A simplified Indian Diabetes Risk Score for screening for undiagnosed diabetic subjects.* J Assoc Physicians India, 53, 759-763.
2. **INTERHEART Study (South Asia)**: Yusuf, S., et al. (2004). *Effect of potentially modifiable risk factors associated with myocardial infarction in 52 countries.* The Lancet, 364(9438), 937-952.
3. **ICMR-INDIAB Study**: Anjana, R. M., et al. (2023). *Metabolic non-communicable disease health report of India: the ICMR-INDIAB national cross-sectional study.* The Lancet Diabetes & Endocrinology, 11(7), 474-489.
4. **SHAP (SHapley Additive exPlanations)**: Lundberg, S. M., & Lee, S. I. (2017). *A Unified Approach to Interpreting Model Predictions.* Advances in Neural Information Processing Systems (NeurIPS).
5. **DoWhy Causal Inference**: Sharma, A., & Kiciman, E. (2020). *DoWhy: An End-to-End Library for Causal Inference.* arXiv:2011.04216.

---

## ⚠️ Safety & Medical Disclaimer

> [!IMPORTANT]
> **SAARTHI.AI is an AI-assisted preventive wellness and risk estimation tool designed for informational and educational purposes only.**
> 
> - It **does not** provide clinical medical diagnoses, prescribe medications, or replace the advice of qualified healthcare professionals.
> - The risk probabilities generated by DarpanEnsemble v2 represent statistical likelihoods derived from wearable telemetry patterns and synthetic cohort baselines.
> - Users experiencing acute symptoms (chest pain, shortness of breath, severe dizziness) must seek immediate emergency medical care.

---

