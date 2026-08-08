# 🩺 SAARTHI.AI — Smart AI for Adaptive Risk Tracking & Health Intelligence

> **Repository:** `breaking_enigma` (Darpan AI Platform)  
> **Mission:** Multi-modal predictive health analytics, causal inference, and personalized lifestyle intervention powered by 30-day temporal sequence transformers, XGBoost gradient boosting, and cognitive LLM agents.

---

## 🌟 Key Features

### 🧠 1. Hybrid ML Stacking Ensemble (`darpan_ensemble_v2_12feature`)
Predicts multi-disease risk profiles (Diabetes, Cardiovascular Disease [CVD], Hypertension) from a 30-day rolling sequence of **12 ICMR health features**:
- **30-Day Sequence Transformer (`DarpanTransformer`)**: Deep learning architecture capturing temporal sequence trends over 30 days.
- **XGBoost Feature Extraction**: Parallel gradient boosted trees evaluating statistical aggregations, min/max bounds, 7-day deltas, and threshold breaches.
- **Meta-Learner**: Combines Transformer and XGBoost predictions into calibrated percentage risk scores (0–100%).

### 🔬 2. Causal Inference & Counterfactual Simulation
- Powered by **DoWhy** framework to estimate real causal impacts of lifestyle adjustments.
- Interactive "what-if" simulations allowing users to test interventions (e.g., *"What if I increase daily steps from 4,000 to 8,000 and reduce daily sugar by 20g?"*).

### ⚡ 3. Real-Time Anomaly Detection
- Integrates **Salesforce Merlion** time-series anomaly detection algorithms to flag abnormal vital patterns (sudden HRV drops, elevated stress levels, sleep irregularities).

### 🤖 4. Cognitive Assistant & Long-Term Memory
- **Cognitive Medical Agent**: LLM-powered assistant (Anthropic / OpenAI) offering context-aware medical reasoning and lifestyle guidance.
- **Personal Memory (`mem0`)**: Warm-loaded BERT embedding engine tracking long-term user health history, preferences, and dietary restrictions across sessions.

### 📱 5. Multi-Channel User Interfaces
- **Web Dashboard**: Modern, responsive UI built with Next.js 16 (App Router), React 19, Tailwind CSS v4, and Recharts.
- **Mobile Client**: Expo / React Native mobile application for on-the-go health metric logging and alert notifications.
- **Telegram Bot Integration**: Async Telegram bot for automated daily check-ins, quick logging, and instant risk alerts.

---

## 🏗️ Architecture & Project Structure

```
breaking_enigma/
├── backend/                        # FastAPI REST API & Services
│   ├── main.py                     # Entry point & lifespan model warm-loading
│   ├── config.py                   # App configuration & settings
│   ├── db/                         # Database adapters (MongoDB / PostgreSQL)
│   ├── routes/                     # FastAPI Router endpoints
│   │   ├── health_data.py          # Vital ingestion & metrics
│   │   ├── risk.py                 # Disease risk evaluation
│   │   ├── simulate.py             # Counterfactual simulation engine
│   │   ├── insights.py & alerts.py # Anomalies & health alerts
│   │   ├── recommend.py            # AI intervention plans
│   │   ├── chat.py & memory.py     # Cognitive agent & mem0 integration
│   │   ├── telegram.py             # Telegram bot webhook endpoints
│   │   ├── arena.py                # Model evaluation benchmarks
│   │   └── profile.py              # User demographic profiles
│   └── services/                   # Business logic & ML integrations
│       ├── ensemble_service.py     # ML ensemble wrapper
│       ├── causal_service.py       # DoWhy causal inference
│       ├── anomaly_service.py      # Merlion anomaly detector
│       ├── cognitive_agent_service.py # RAG & LLM agent logic
│       ├── memory_service.py       # mem0 long-term memory engine
│       └── telegram_service.py     # Async Telegram bot polling
│
├── darpan_ensemble_v2_12feature/   # Core ML Training & Inference Engine
│   ├── ensemble_predictor.py       # Production predictor class (DarpanEnsemble)
│   ├── train_l40s_sequence.py      # PyTorch Transformer model training
│   ├── train_xgboost.py            # XGBoost classifiers training
│   ├── train_meta_ensemble.py      # Stacking meta-learner training
│   └── *.pth / *.pkl               # Pre-trained ICMR model artifacts
│
├── frontend/                       # Next.js 16 Web Dashboard
│   ├── app/                        # Next.js App Router (pages & layouts)
│   ├── components/                 # UI components (Recharts graphs, metrics cards)
│   ├── lib/                        # API clients & utilities
│   └── package.json                # React 19 / Next.js / Tailwind dependencies
│
├── mobile/                         # Mobile Client Application
│   ├── App.tsx                     # Expo React Native root component
│   ├── app.json                    # Expo configuration
│   └── src/                        # Mobile screens & components
│
├── run.sh                          # One-command full stack launcher
└── requirements.txt                # Python backend & ML dependencies
```

---

## 🛠️ Technology Stack

| Domain | Technologies Used |
| :--- | :--- |
| **Backend & APIs** | Python 3.10+, FastAPI, Uvicorn, Pydantic, Motor/PyMongo, Asyncio |
| **Machine Learning** | PyTorch, XGBoost, Scikit-Learn, SHAP, NumPy, Pandas |
| **Causal & Anomalies** | DoWhy, Salesforce Merlion |
| **Cognitive & Memory** | Anthropic Claude API, `mem0ai` (BERT embeddings RAG) |
| **Web Frontend** | Next.js 16 (App Router), React 19, Tailwind CSS v4, Recharts, Lucide React |
| **Mobile App** | Expo, React Native, TypeScript |
| **Bot Integrations** | Python Telegram Bot API |

---

## 🚀 Quick Start & Setup

### Prerequisites
- **Python 3.10+** (Conda environment named `darpanai` recommended)
- **Node.js 18+** & `npm`
- **MongoDB / PostgreSQL** (configured via `.env`)

### 1. Environment Configuration
Create a `.env` file in the root directory (or inside `backend/`):
```env
ANTHROPIC_API_KEY=your_anthropic_key_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
DATABASE_URL=mongodb://localhost:27017/darpanai
```

### 2. Run Application (Single Command)
Run the automated launch script from the root directory:
```bash
chmod +x run.sh
./run.sh
```

`run.sh` automatically:
1. Starts the **Backend Uvicorn Server** on `http://localhost:8000` (with model warm-loading).
2. Starts the **Frontend Next.js Dev Server** on `http://localhost:3000`.

### 3. Manual Server Start

**Backend API:**
```bash
# In project root
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
- Interactive API Docs: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`

**Frontend Dashboard:**
```bash
cd frontend
npm install
npm run dev
```
- Open `http://localhost:3000` in your browser.

**Mobile App:**
```bash
cd mobile
npm install
npx expo start
```

---

## 📋 API Endpoints Reference

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/health` | `GET` | System operational health check |
| `/risk` | `POST` | Evaluate 30-day patient sequence risk scores |
| `/simulate` | `POST` | Perform counterfactual lifestyle simulations |
| `/insights` | `GET` | Fetch statistical trends & vital anomalies |
| `/recommend` | `POST` | Generate AI-backed intervention plans |
| `/chat` | `POST` | Converse with cognitive health assistant |
| `/memory` | `GET/POST` | Inspect and manage patient `mem0` memory |
| `/alerts` | `GET` | Retrieve critical user health notifications |

---

## 📄 License & Attribution
Developed as part of the **Darpan AI / SAARTHI.AI** project for preventive health intelligence and ICMR risk scoring research.
