from datetime import date
from typing import Any
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    database: str


class DashboardSummaryResponse(BaseModel):
    total_trips: int
    active_zones: int
    avg_total_amount: float | None
    avg_trip_distance: float | None


class BoroughResponse(BaseModel):
    borough: str


class DailyTrendItem(BaseModel):
    pickup_date: date
    trip_count: int
    avg_total_amount: float | None

class WeekdayHourHeatmapItem(BaseModel):
    weekday: int
    pickup_hour: int
    trip_count: int

class ZoneRankingItem(BaseModel):
    location_id: int
    zone_name: str
    borough: str
    trip_count: int
    avg_total_amount: float | None
    avg_trip_distance: float | None

class GeoJSONGeometry(BaseModel):
    type: str
    coordinates: Any

class ZoneScoreProperties(BaseModel):
    location_id: int
    zone_name: str
    borough: str
    trip_count: int
    active_day_count: int
    total_day_count: int
    demand_score: float
    hotspot_component_score: float
    consistency_score: float
    zone_score: float
    priority_class: str


class ZoneScoreFeature(BaseModel):
    type: str
    geometry: GeoJSONGeometry
    properties: ZoneScoreProperties


class ZoneScoreFeatureCollection(BaseModel):
    type: str
    features: list[ZoneScoreFeature]

class ZoneHotspotProperties(BaseModel):
    location_id: int
    zone_name: str
    borough: str
    trip_count: int
    neighbour_count: int
    neighbour_avg_trip_count: float
    hotspot_score: int
    hotspot_class: str

class ZoneHotspotFeature(BaseModel):
    type: str
    geometry: GeoJSONGeometry
    properties: ZoneHotspotProperties


class ZoneHotspotFeatureCollection(BaseModel):
    type: str
    features: list[ZoneHotspotFeature]

class ZoneDetailResponse(BaseModel):
    location_id: int
    zone_name: str
    borough: str

    trip_count: int
    avg_total_amount: float | None
    avg_trip_distance: float | None

    active_day_count: int
    total_day_count: int

    peak_weekday: int | None
    peak_weekday_name: str | None
    peak_hour: int | None

    demand_score: float
    hotspot_component_score: float
    consistency_score: float
    zone_score: float

    priority_class: str
    hotspot_class: str
        
class HourlyDemandItem(BaseModel):
    pickup_hour: int
    trip_count: int
    avg_total_amount: float | None


class ZoneProperties(BaseModel):
    location_id: int
    zone_name: str
    borough: str
    trip_count: int
    avg_total_amount: float | None
    avg_trip_distance: float | None
    demand_class_id: int
    demand_class: str

class GeoJSONFeature(BaseModel):
    type: str
    geometry: GeoJSONGeometry
    properties: ZoneProperties


class GeoJSONFeatureCollection(BaseModel):
    type: str
    features: list[GeoJSONFeature]
    
class DailyDemandForecastItem(BaseModel):
    forecast_date: date
    weekday: int
    predicted_trip_count: int
    lower_bound: int
    upper_bound: int
    sample_count: int