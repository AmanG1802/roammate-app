"""Standalone LLM endpoints that don't live under a specific trip."""
import logging

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.all_models import User
from app.schemas.brainstorm import PlanTripRequest, PlanTripResponse, BrainstormItemBase
from app.services import entitlements
from app.services.google_maps import get_google_maps_service
from app.services.google_maps.base import BaseMapService
from app.services.llm.registry import get_dashboard_client

log = logging.getLogger(__name__)

router = APIRouter()


def _get_enrichment_service(
    x_client_platform: Optional[str] = Header(None),
) -> BaseMapService:
    if x_client_platform and x_client_platform.lower() == "ios":
        from app.services.apple_maps import get_apple_maps_service
        svc = get_apple_maps_service()
        if svc is not None:
            return svc
    return get_google_maps_service()


@router.post("/plan-trip", response_model=PlanTripResponse)
async def plan_trip(
    body: PlanTripRequest,
    current_user: User = Depends(get_current_user),
    maps_svc: BaseMapService = Depends(_get_enrichment_service),
    db: AsyncSession = Depends(get_db),
):
    """Return a trip preview (name + duration + seed items). Not persisted —
    the client decides whether to actually create the trip.

    Counts against the user's free-tier brainstorm allowance: every Plan-Trip
    user message increments ``UsageCounter.brainstorm_messages`` the same way
    a Brainstorm chat does. Plus users bypass both the cap and the counter.

    Enrichment policy: items are enriched **inline** via the platform-appropriate
    Maps service.  In mock mode this is essentially free; with the real key,
    ``enrich_items`` runs in parallel (Sem(5)) and short-circuits cleanly if
    the circuit breaker is open.
    """
    await entitlements.enforce_brainstorm(db, current_user)
    client = get_dashboard_client()
    try:
        result = await client.plan_trip(body.prompt, user_id=current_user.id)
    except Exception as exc:
        log.exception("plan_trip LLM call failed")
        raise HTTPException(
            status_code=502,
            detail="AI planner is temporarily unavailable. Please try again.",
        ) from exc

    await entitlements.bump_brainstorm_counter(db, current_user)
    await db.commit()

    enriched_items, enrichment_summary = await maps_svc.enrich_items_with_summary(
        result["items"], user_id=current_user.id,
    )
    from app.schemas.enrichment import EnrichmentStatus
    enr = None if enrichment_summary.status == "full" else EnrichmentStatus(
        status=enrichment_summary.status,
        total=enrichment_summary.total,
        enriched=enrichment_summary.enriched,
        skipped=enrichment_summary.skipped,
        reason=enrichment_summary.reason,
    )

    # Default start_date to today (in caller's timezone) when the LLM/pre-extractor
    # didn't find one in the prompt. Guarantees create_trip will auto-create Day 1
    # so the dashboard widget can classify the trip as ongoing.
    start_date = result.get("start_date")
    if not start_date:
        from app.utils.tz import today_in_tz
        start_date = today_in_tz(body.timezone or "UTC").isoformat()

    # Timezone inference always goes through Google (Apple Maps has its own
    # timezone API but we haven't implemented that adapter). On mock/missing
    # key the call returns None, which the client falls back to device tz.
    tz_svc = get_google_maps_service()
    inferred_tz: Optional[str] = None
    for it in enriched_items:
        lat = it.get("lat")
        lng = it.get("lng")
        if lat is not None and lng is not None:
            inferred_tz = await tz_svc.timezone_for(
                float(lat), float(lng), user_id=current_user.id,
            )
            if inferred_tz:
                break

    return PlanTripResponse(
        trip_name=result["trip_name"],
        start_date=start_date,
        duration_days=result["duration_days"],
        items=[BrainstormItemBase(**it) for it in enriched_items],
        enrichment=enr,
        user_output=result.get("user_output", ""),
        timezone=inferred_tz,
    )
