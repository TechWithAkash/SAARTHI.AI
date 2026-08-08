import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from backend.db.postgres import get_db
from backend.models.health import RecommendResponse, Recommendation, AgentMeta, AgentTraceStep
from backend.services.cognitive_agent_service import stream_cognitive_agent

router = APIRouter()


@router.get("/recommend/stream")
async def stream_recommendations(user_id: str):
    """
    Real-time SSE stream of the 4-step Cognitive Health Agent.
    Frontend connects via EventSource — each step emits as it completes.
    """
    return StreamingResponse(
        stream_cognitive_agent(user_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/recommend", response_model=RecommendResponse)
async def get_recommendations(user_id: str):
    """
    Reads the latest agent result from DB (fast path for non-SSE clients).
    Returns full recommendations + agent metadata including trace.
    """
    pool = get_db()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM recommendations WHERE user_id=$1 ORDER BY generated_at DESC LIMIT 1",
            user_id,
        )

    if not row:
        raise HTTPException(status_code=404, detail="No recommendations found. Submit health data first.")

    recs_raw = row["recommendations"]
    if isinstance(recs_raw, str):
        recs_raw = json.loads(recs_raw)
    recs_raw = recs_raw or []

    agent_raw = row["agent_metadata"]
    if isinstance(agent_raw, str):
        agent_raw = json.loads(agent_raw)
    agent_raw = agent_raw or {}

    recs = [
        Recommendation(
            priority=r.get("priority", i + 1),
            action=r.get("action", ""),
            reason=r.get("reason", ""),
            impact=r.get("impact", "medium"),
            timeframe=r.get("timeframe", "2–4 weeks"),
            estimated_risk_reduction=r.get("estimated_risk_reduction"),
            causal_mechanism=r.get("causal_mechanism"),
        )
        for i, r in enumerate(recs_raw)
    ]

    agent_meta = None
    if agent_raw:
        trace_steps = [
            AgentTraceStep(
                step=t.get("step", i + 1),
                type=t.get("type", "tool_call"),
                tool=t.get("agent"),
                summary=t.get("summary"),
                content=t.get("detail", {}).get("risk_summary") if isinstance(t.get("detail"), dict) else None,
            )
            for i, t in enumerate(agent_raw.get("trace", []))
        ]
        agent_meta = AgentMeta(
            reasoning=agent_raw.get("reasoning", ""),
            primary_lever=agent_raw.get("primary_lever", ""),
            agent_confidence=agent_raw.get("agent_confidence", "medium"),
            tools_called=agent_raw.get("tools_called", []),
            n_tool_calls=agent_raw.get("n_tool_calls", 0),
            trace=trace_steps,
        )

    return RecommendResponse(
        user_id=user_id,
        recommendations=recs,
        method=row.get("method"),
        risk_score=row.get("risk_score"),
        generated_at=row.get("generated_at"),
        agent=agent_meta,
    )
