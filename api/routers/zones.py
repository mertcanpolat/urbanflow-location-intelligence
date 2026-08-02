from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query


from api.models.filters import (
    DashboardFilters,
    get_dashboard_filters,
)
from api.models.responses import (
    GeoJSONFeatureCollection,
    HourlyDemandItem,
    ZoneRankingItem,
    ZoneHotspotFeatureCollection,
    ZoneScoreFeatureCollection,
    ZoneDetailResponse,
    ZoneTrendResponse,
    ZoneAnomalyResponse,
)

from api.services.zone_service import (
    get_boroughs as get_boroughs_service,
    get_top_zones as get_top_zones_service,
    get_zone_hourly_demand as get_zone_hourly_demand_service,
    get_zone_ranking as get_zone_ranking_service,
    get_zones_geojson as get_zones_geojson_service,
    get_zone_hotspots as get_zone_hotspots_service,
    get_zone_scores as get_zone_scores_service,
    get_zone_details as get_zone_details_service,
    get_zone_trend as get_zone_trend_service,
    get_zone_anomalies as get_zone_anomalies_service,    
)

router = APIRouter(
    prefix="/api/v1",
    tags=["Zones"],
)

@router.get(
    "/boroughs",
    response_model=list[str],
)
def get_boroughs() -> list[str]:
    """Return distinct Taxi Zone borough names."""

    return get_boroughs_service()

@router.get("/zones/top")
def get_top_zones(
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
        description="Döndürülecek bölge sayısı.",
    ),
) -> list[dict[str, Any]]:
    """Return zones with the highest pickup demand."""

    return get_top_zones_service(limit)

@router.get(
    "/zones/geojson",
    response_model=GeoJSONFeatureCollection,
)
def get_zones_geojson(
    filters: DashboardFilters = Depends(
        get_dashboard_filters
    ),
) -> dict[str, Any]:
    """Return filtered Taxi Zones as GeoJSON."""

    return get_zones_geojson_service(filters)

@router.get(
    "/zones/hotspots",
    response_model=ZoneHotspotFeatureCollection,
)
def get_zone_hotspots(
    filters: DashboardFilters = Depends(
        get_dashboard_filters
    ),
) -> dict[str, Any]:
    """Return spatial hotspot classifications."""

    return get_zone_hotspots_service(filters)

@router.get(
    "/zones/scores",
    response_model=ZoneScoreFeatureCollection,
)
def get_zone_scores(
    filters: DashboardFilters = Depends(
        get_dashboard_filters
    ),
) -> dict[str, Any]:
    """Return weighted zone-priority scores."""

    return get_zone_scores_service(filters)

@router.get(
    "/zones/ranking",
    response_model=list[ZoneRankingItem],
)
def get_zone_ranking(
    filters: DashboardFilters = Depends(
        get_dashboard_filters
    ),
    limit: int = Query(
        default=10,
        ge=1,
        le=50,
        description="Döndürülecek bölge sayısı.",
    ),
) -> list[dict[str, Any]]:
    """Return the highest-demand Taxi Zones."""

    return get_zone_ranking_service(
        filters=filters,
        limit=limit,
    )

@router.get(
    "/zones/{location_id}/details",
    response_model=ZoneDetailResponse,
)
def get_zone_details(
    location_id: int,
    filters: DashboardFilters = Depends(
        get_dashboard_filters
    ),
) -> dict[str, Any]:
    """Return detailed analytics for one Taxi Zone."""

    result = get_zone_details_service(
        location_id=location_id,
        filters=filters,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Taxi Zone bulunamadı.",
        )

    return result

@router.get(
    "/zones/{location_id}/trend",
    response_model=ZoneTrendResponse,
)
def get_zone_trend(
    location_id: int,
    filters: DashboardFilters = Depends(
        get_dashboard_filters
    ),
    period_days: int = Query(
        default=7,
        ge=2,
        le=30,
        description=(
            "Karşılaştırılacak dönemlerin gün sayısı."
        ),
    ),
) -> dict[str, Any]:
    """Return demand trend for one Taxi Zone."""

    result = get_zone_trend_service(
        location_id=location_id,
        filters=filters,
        period_days=period_days,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Taxi Zone bulunamadı.",
        )

    return result

@router.get(
    "/zones/{location_id}/anomalies",
    response_model=ZoneAnomalyResponse,
)
def get_zone_anomalies(
    location_id: int,
    filters: DashboardFilters = Depends(
        get_dashboard_filters
    ),
    analysis_days: int = Query(
        default=28,
        ge=14,
        le=90,
        description=(
            "Anomali analizinde kullanılacak "
            "takvim günü sayısı."
        ),
    ),
    z_threshold: float = Query(
        default=2.0,
        ge=1.0,
        le=4.0,
        description=(
            "Bir gözlemin anomali kabul edilmesi "
            "için gereken mutlak Z-score sınırı."
        ),
    ),
) -> dict[str, Any]:
    """Return anomalous daily demand for one Taxi Zone."""

    result = get_zone_anomalies_service(
        location_id=location_id,
        filters=filters,
        analysis_days=analysis_days,
        z_threshold=z_threshold,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Taxi Zone bulunamadı.",
        )

    return result

@router.get(
    "/zones/{location_id}/hourly",
    response_model=list[HourlyDemandItem],
)
def get_zone_hourly_demand(
    location_id: int,
    filters: DashboardFilters = Depends(
        get_dashboard_filters
    ),
) -> list[dict[str, Any]]:
    """Return hourly demand totals for one Taxi Zone."""

    result = get_zone_hourly_demand_service(
        location_id=location_id,
        filters=filters,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Taxi Zone bulunamadı.",
        )

    return result