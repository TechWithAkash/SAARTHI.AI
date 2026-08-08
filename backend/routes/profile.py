"""
DarpanAI — User Profile Route
==============================
Handles saving and reading the clinical profile fields that wearables
cannot provide: age, gender, whr, and family history flags.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from backend.db.postgres import get_db

router = APIRouter()


class UserProfileUpdate(BaseModel):
    user_id: str
    age: Optional[int] = None
    gender: Optional[str] = None          # 'male' | 'female' | 'other'
    whr: Optional[float] = None           # waist-hip ratio
    fam_diabetes: Optional[int] = None    # 0 or 1
    fam_cvd: Optional[int] = None         # 0 or 1
    fam_hypertension: Optional[int] = None  # 0 or 1


class UserProfileResponse(BaseModel):
    user_id: str
    age: Optional[int] = None
    gender: Optional[str] = None
    whr: Optional[float] = None
    fam_diabetes: Optional[int] = None
    fam_cvd: Optional[int] = None
    fam_hypertension: Optional[int] = None
    profile_complete: bool = False


@router.get("/profile", response_model=UserProfileResponse)
async def get_profile(user_id: str):
    pool = get_db()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT user_id, age, gender, whr, fam_diabetes, fam_cvd, fam_hypertension
            FROM users WHERE user_id = $1
            """,
            user_id,
        )

    if not row:
        return UserProfileResponse(user_id=user_id, profile_complete=False)

    complete = all([
        row["age"] is not None,
        row["gender"] is not None,
        row["fam_diabetes"] is not None,
        row["fam_cvd"] is not None,
        row["fam_hypertension"] is not None,
    ])

    return UserProfileResponse(
        user_id=user_id,
        age=row["age"],
        gender=row["gender"],
        whr=row["whr"],
        fam_diabetes=row["fam_diabetes"],
        fam_cvd=row["fam_cvd"],
        fam_hypertension=row["fam_hypertension"],
        profile_complete=complete,
    )


@router.post("/profile", response_model=UserProfileResponse)
async def update_profile(data: UserProfileUpdate):
    pool = get_db()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO users (user_id, age, gender, whr, fam_diabetes, fam_cvd, fam_hypertension)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (user_id) DO UPDATE SET
                age              = COALESCE(EXCLUDED.age, users.age),
                gender           = COALESCE(EXCLUDED.gender, users.gender),
                whr              = COALESCE(EXCLUDED.whr, users.whr),
                fam_diabetes     = COALESCE(EXCLUDED.fam_diabetes, users.fam_diabetes),
                fam_cvd          = COALESCE(EXCLUDED.fam_cvd, users.fam_cvd),
                fam_hypertension = COALESCE(EXCLUDED.fam_hypertension, users.fam_hypertension)
            """,
            data.user_id,
            data.age,
            data.gender,
            data.whr,
            data.fam_diabetes,
            data.fam_cvd,
            data.fam_hypertension,
        )

        row = await conn.fetchrow(
            "SELECT * FROM users WHERE user_id = $1", data.user_id
        )

    complete = all([
        row["age"] is not None,
        row["gender"] is not None,
        row["fam_diabetes"] is not None,
        row["fam_cvd"] is not None,
        row["fam_hypertension"] is not None,
    ])

    return UserProfileResponse(
        user_id=row["user_id"],
        age=row["age"],
        gender=row["gender"],
        whr=row["whr"],
        fam_diabetes=row["fam_diabetes"],
        fam_cvd=row["fam_cvd"],
        fam_hypertension=row["fam_hypertension"],
        profile_complete=complete,
    )
