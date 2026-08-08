from fastapi import APIRouter, HTTPException
from backend.db.postgres import get_db
from backend.models.health import Alert, AlertsResponse

router = APIRouter()


@router.get("/alerts", response_model=AlertsResponse)
async def get_alerts(user_id: str):
    pool = get_db()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM anomalies WHERE user_id=$1 AND acknowledged=FALSE ORDER BY detected_at DESC LIMIT 20",
            user_id,
        )

    alerts = [
        Alert(
            id=str(row["id"]),
            metric=row["metric"],
            value=row["observed_value"],
            severity=row["severity"],
            message=row["message"],
            timestamp=row["detected_at"],
        )
        for row in rows
    ]

    return AlertsResponse(user_id=user_id, alerts=alerts)


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    pool = get_db()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE anomalies SET acknowledged=TRUE, acknowledged_at=NOW() WHERE id=$1::uuid",
            alert_id,
        )

    # asyncpg execute returns a status string like "UPDATE 1"
    updated_count = int(result.split()[-1]) if result else 0
    if updated_count == 0:
        raise HTTPException(status_code=404, detail="Alert not found or already acknowledged")

    return {"status": "success", "message": "Alert acknowledged"}
