"""Standalone LLM endpoints that don't live under a specific trip."""
from fastapi import APIRouter, Depends
from app.api.deps import get_current_user
from app.models.all_models import User
from app.schemas.brainstorm import PlanTripRequest, PlanTripResponse, BrainstormItemBase
from app.services.google_maps import get_google_maps_service
from app.services.llm.registry import get_dashboard_client

router = APIRouter()


@router.post("/plan-trip", response_model=PlanTripResponse)
async def plan_trip(
    body: PlanTripRequest,
    current_user: User = Depends(get_current_user),
):
    """Return a trip preview (name + duration + seed items). Not persisted —
    the client decides whether to actually create the trip.

    Enrichment policy: ``plan_trip`` items are enriched **inline** via
    GoogleMapsService.  In mock mode this is essentially free; with the
    real key, ``enrich_items`` runs in parallel (Sem(5)) and short-circuits
    cleanly if the circuit breaker is open.
    """
    client = get_dashboard_client()
    result = await client.plan_trip(body.prompt, user_id=current_user.id)
    maps_svc = get_google_maps_service()
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
