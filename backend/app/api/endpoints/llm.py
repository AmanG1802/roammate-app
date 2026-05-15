"""Standalone LLM endpoints that don't live under a specific trip."""
import logging

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from app.api.deps import get_current_user
from app.models.all_models import User
from app.schemas.brainstorm import PlanTripRequest, PlanTripResponse, BrainstormItemBase
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
):
    """Return a trip preview (name + duration + seed items). Not persisted —
    the client decides whether to actually create the trip.

    Enrichment policy: items are enriched **inline** via the platform-appropriate
    Maps service.  In mock mode this is essentially free; with the real key,
    ``enrich_items`` runs in parallel (Sem(5)) and short-circuits cleanly if
    the circuit breaker is open.
    """
    client = get_dashboard_client()
    try:
        result = await client.plan_trip(body.prompt, user_id=current_user.id)
    except Exception as exc:
        log.exception("plan_trip LLM call failed")
        raise HTTPException(
            status_code=502,
            detail="AI planner is temporarily unavailable. Please try again.",
        ) from exc

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
    return PlanTripResponse(
        trip_name=result["trip_name"],
        start_date=result.get("start_date"),
        duration_days=result["duration_days"],
        items=[BrainstormItemBase(**it) for it in enriched_items],
        enrichment=enr,
    )
