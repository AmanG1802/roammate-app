"""Standalone LLM endpoints that don't live under a specific trip."""
from fastapi import APIRouter, Depends
from app.api.deps import get_current_user
from app.models.all_models import User
from app.schemas.brainstorm import PlanTripRequest, PlanTripResponse, BrainstormItemBase
from app.services import llm_client

router = APIRouter()


@router.post("/plan-trip", response_model=PlanTripResponse)
async def plan_trip(
    body: PlanTripRequest,
    current_user: User = Depends(get_current_user),
):
    """Return a trip preview (name + duration + seed items). Not persisted —
    the client decides whether to actually create the trip."""
    result = await llm_client.plan_trip(body.prompt)
    return PlanTripResponse(
        trip_name=result["trip_name"],
        start_date=result.get("start_date"),
        duration_days=result["duration_days"],
        items=[BrainstormItemBase(**it) for it in result["items"]],
    )
