from fastapi.testclient import TestClient

import api.routers.zones as zones_router


def test_get_boroughs(
    client: TestClient,
    monkeypatch,
) -> None:
    expected_result = [
        "Bronx",
        "Brooklyn",
        "Manhattan",
        "Queens",
        "Staten Island",
    ]

    monkeypatch.setattr(
        zones_router,
        "get_boroughs_service",
        lambda: expected_result,
    )

    response = client.get(
        "/api/v1/boroughs"
    )

    assert response.status_code == 200
    assert response.json() == expected_result


def test_zone_ranking(
    client: TestClient,
    monkeypatch,
) -> None:
    expected_result = [
        {
            "location_id": 161,
            "zone_name": "Midtown Center",
            "borough": "Manhattan",
            "trip_count": 8500,
            "avg_total_amount": 24.50,
            "avg_trip_distance": 3.25,
        }
    ]

    def fake_get_zone_ranking(
        filters,
        limit,
    ):
        assert limit == 10
        return expected_result

    monkeypatch.setattr(
        zones_router,
        "get_zone_ranking_service",
        fake_get_zone_ranking,
    )

    response = client.get(
        "/api/v1/zones/ranking"
    )

    assert response.status_code == 200
    assert response.json() == expected_result


def test_unknown_zone_returns_404(
    client: TestClient,
    monkeypatch,
) -> None:
    def fake_get_hourly(
        location_id,
        filters,
    ):
        assert location_id == 9999
        return None

    monkeypatch.setattr(
        zones_router,
        "get_zone_hourly_demand_service",
        fake_get_hourly,
    )

    response = client.get(
        "/api/v1/zones/9999/hourly"
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Taxi Zone bulunamadı."
    }


def test_zone_hourly_demand(
    client: TestClient,
    monkeypatch,
) -> None:
    expected_result = [
        {
            "pickup_hour": 8,
            "trip_count": 125,
            "avg_total_amount": 22.40,
        },
        {
            "pickup_hour": 9,
            "trip_count": 180,
            "avg_total_amount": 23.10,
        },
    ]

    def fake_get_hourly(
        location_id,
        filters,
    ):
        assert location_id == 161
        return expected_result

    monkeypatch.setattr(
        zones_router,
        "get_zone_hourly_demand_service",
        fake_get_hourly,
    )

    response = client.get(
        "/api/v1/zones/161/hourly"
    )

    assert response.status_code == 200
    assert response.json() == expected_result
    
def test_zone_hotspots(
    client: TestClient,
    monkeypatch,
) -> None:
    expected_result = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-73.99, 40.75],
                            [-73.98, 40.75],
                            [-73.98, 40.76],
                            [-73.99, 40.75],
                        ]
                    ],
                },
                "properties": {
                    "location_id": 161,
                    "zone_name": "Midtown Center",
                    "borough": "Manhattan",
                    "trip_count": 8500,
                    "neighbour_count": 4,
                    "neighbour_avg_trip_count": 7200.5,
                    "hotspot_score": 2,
                    "hotspot_class": "Hotspot",
                },
            }
        ],
    }

    def fake_get_zone_hotspots(filters):
        return expected_result

    monkeypatch.setattr(
        zones_router,
        "get_zone_hotspots_service",
        fake_get_zone_hotspots,
    )

    response = client.get(
        "/api/v1/zones/hotspots"
    )

    assert response.status_code == 200
    assert response.json() == expected_result
    
def test_zone_scores(
    client: TestClient,
    monkeypatch,
) -> None:
    expected_result = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-73.99, 40.75],
                            [-73.98, 40.75],
                            [-73.98, 40.76],
                            [-73.99, 40.75],
                        ]
                    ],
                },
                "properties": {
                    "location_id": 161,
                    "zone_name": "Midtown Center",
                    "borough": "Manhattan",
                    "trip_count": 146221,
                    "active_day_count": 31,
                    "total_day_count": 33,
                    "demand_score": 99.23,
                    "hotspot_component_score": 100.0,
                    "consistency_score": 93.94,
                    "zone_score": 98.4,
                    "priority_class": "Çok Yüksek",
                },
            }
        ],
    }

    def fake_get_zone_scores(filters):
        return expected_result

    monkeypatch.setattr(
        zones_router,
        "get_zone_scores_service",
        fake_get_zone_scores,
    )

    response = client.get(
        "/api/v1/zones/scores"
    )

    assert response.status_code == 200
    assert response.json() == expected_result
    
    
def test_zone_details(
    client: TestClient,
    monkeypatch,
) -> None:
    expected_result = {
        "location_id": 161,
        "zone_name": "Midtown Center",
        "borough": "Manhattan",
        "trip_count": 146221,
        "avg_total_amount": 24.50,
        "avg_trip_distance": 3.25,
        "active_day_count": 31,
        "total_day_count": 33,
        "peak_weekday": 5,
        "peak_weekday_name": "Cuma",
        "peak_hour": 18,
        "demand_score": 99.23,
        "hotspot_component_score": 100.0,
        "consistency_score": 93.94,
        "zone_score": 98.40,
        "priority_class": "Çok Yüksek",
        "hotspot_class": "Hotspot",
    }

    def fake_get_zone_details(
        location_id,
        filters,
    ):
        assert location_id == 161
        return expected_result

    monkeypatch.setattr(
        zones_router,
        "get_zone_details_service",
        fake_get_zone_details,
    )

    response = client.get(
        "/api/v1/zones/161/details"
    )

    assert response.status_code == 200
    assert response.json() == expected_result
    
def test_unknown_zone_details_returns_404(
    client: TestClient,
    monkeypatch,
) -> None:
    def fake_get_zone_details(
        location_id,
        filters,
    ):
        assert location_id == 9999
        return None

    monkeypatch.setattr(
        zones_router,
        "get_zone_details_service",
        fake_get_zone_details,
    )

    response = client.get(
        "/api/v1/zones/9999/details"
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Taxi Zone bulunamadı."
    }