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


class GeoJSONGeometry(BaseModel):
    type: str
    coordinates: Any


class GeoJSONFeature(BaseModel):
    type: str
    geometry: GeoJSONGeometry
    properties: ZoneProperties


class GeoJSONFeatureCollection(BaseModel):
    type: str
    features: list[GeoJSONFeature]