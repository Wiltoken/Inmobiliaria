"""Frontend user action audit logging and BI analytics endpoints.

POST /api/v1/audit/user-action  — Log frontend user action
GET  /api/v1/admin/analytics     — Get BI dashboard data

"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, get_db
from app.domain.models import User, UserAction

router = APIRouter(prefix="/audit", tags=["audit"])


# ── Pydantic Schemas ───────────────────────────────────────────────────────────


class UserActionRequest(BaseModel):
    action: str = Field(..., max_length=100, description="Action name, e.g. page_view, search_performed")
    details: dict | None = Field(default_factory=dict, description="Additional event details")


class UserActionResponse(BaseModel):
    id: str
    status: str = "ok"


class AnalyticsDashboard(BaseModel):
    dau: int = Field(description="Daily active users")
    searches_today: int
    properties_viewed: int
    inquiries_sent: int
    events_over_time: list[dict]
    user_roles: list[dict]
    top_properties: list[dict]
    recent_actions: list[dict]


# ── POST /api/v1/audit/user-action ─────────────────────────────────────────────


@router.post(
    "/user-action",
    response_model=UserActionResponse,
    status_code=201,
)
async def log_user_action(
    request: Request,
    body: UserActionRequest,
    current_user: User | None = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> UserActionResponse:
    """Log a frontend user action for BI/analytics.

    This endpoint is public-ish — it accepts requests without full auth
    so we can track anonymous browsing too, but ties actions to a user
    when authenticated.
    """
    entry = UserAction(
        user_id=current_user.id if current_user else None,
        action=body.action,
        details=body.details,
        ip_address=request.client.host if request.client else None,
    )
    session.add(entry)
    await session.commit()

    return UserActionResponse(id=str(entry.id), status="ok")
