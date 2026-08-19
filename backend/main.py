# ── macOS ARM: must be set before importing torch or xgboost ──────────────────
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
# ──────────────────────────────────────────────────────────────────────────────

import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from backend.db.postgres import connect_db, close_db
from backend.routes import health_data, risk, simulate, insights, recommend, alerts, chat, memory, telegram as telegram_route, arena, profile, garmin, environment, rag as rag_route
from backend.services.telegram_service import start_bot_polling
from backend.services.ensemble_service import get_ensemble
from backend.services.memory_service import _get_memory


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    # Warm-load the DarpanEnsemble so first request is instant (~1.6s cold start)
    await asyncio.to_thread(get_ensemble)
    # Pre-warm mem0 BERT singleton — prevents 2-3s block on first chat/recommend request
    await asyncio.to_thread(_get_memory)
    polling_task = asyncio.create_task(start_bot_polling())
    yield
    polling_task.cancel()
    await close_db()


app = FastAPI(
    title="SAARTHI.AI",
    description="SAARTHI.AI - Smart AI for Adaptive Risk Tracking & Health Intelligence",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    # localhost for continued local dev + the known production Vercel alias,
    # plus every Vercel preview deployment for this project (a new
    # <hash>-techwithakashs-projects.vercel.app subdomain gets minted on
    # every deploy) — a fixed origin list would silently break the very next
    # deploy.
    allow_origins=["http://localhost:3000", "https://saarthi-ai-lovat.vercel.app"],
    allow_origin_regex=r"https://saarthi.*-techwithakashs-projects\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_data.router, tags=["Ingestion"])
app.include_router(risk.router, tags=["Risk"])
app.include_router(simulate.router, tags=["Simulation"])
app.include_router(insights.router, tags=["Insights"])
app.include_router(recommend.router, tags=["Recommendations"])
app.include_router(alerts.router, tags=["Alerts"])
app.include_router(chat.router, tags=["Chatbot"])
app.include_router(memory.router, tags=["Memory Management"])
app.include_router(telegram_route.router, tags=["Telegram"])
app.include_router(arena.router, tags=["Model Arena"])
app.include_router(profile.router, tags=["Profile"])
app.include_router(garmin.router, tags=["Wearables"])
app.include_router(environment.router, tags=["Environment"])
app.include_router(rag_route.router, tags=["RAG"])


@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok", "service": "SAARTHI.AI"}
