"""Admin-specific endpoints.

Provides lightweight API surface needed by the client UI, including
leaderboard information used by power users.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.database import get_async_database_session
from app.schemas import AdminLeaderboardResponse, AdminLeaderboardEntry

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/leaderboard",
    response_model=AdminLeaderboardResponse,
    summary="Fetch aggregated admin transcription counts",
)
async def get_admin_leaderboard(
    range: str = "all",
    db: AsyncSession = Depends(get_async_database_session),
) -> AdminLeaderboardResponse:
    """Return leaderboard stats for admins across common date ranges."""

    try:
        rng = (range or "all").lower()
        if rng not in {"all", "week", "month"}:
            rng = "all"

        time_filter = ""
        if rng == "week":
            time_filter = " AND created_at >= date_trunc('week', now())"
        elif rng == "month":
            time_filter = " AND created_at >= date_trunc('month', now())"

        query = text(
            f"""
            SELECT admin, COUNT(*) AS count
            FROM "Transcriptions"
            WHERE admin IS NOT NULL {time_filter}
            GROUP BY admin
            ORDER BY count DESC, admin ASC;
            """
        )

        result = await db.execute(query)
        rows = result.fetchall()

        leaders = [
            AdminLeaderboardEntry(admin=row[0], count=int(row[1]) if row[1] is not None else 0)
            for row in rows
            if row[0]
        ]
        total = sum(entry.count for entry in leaders)

        return AdminLeaderboardResponse(success=True, range=rng, total=total, leaders=leaders)
    except Exception as exc:
        logger.error("Error generating admin leaderboard: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load leaderboard data")
