from datetime import date

from fastapi.testclient import TestClient

import api.routers.dashboard as dashboard_router


def test_dashboard_summary(
    client: TestClient,
    monkeypatch,
) -> None:
    expected_result = {
        "total_trips": 1250,
        "active_zones": 42,
        "avg_total_amount": 28.75,
        "avg_trip_distance": 4.15,
    }

    def fake_fetch_dashboard_summary(filters):
        return expected_result

    monkeypatch.setattr(
        dashboard_router,
        "get_dashboard_summary_service",
        fake_fetch_dashboard_summary,
    )

    response = client.get(
        "/api/v1/dashboard/summary"
    )

    assert response.status_code == 200
    assert response.json() == expected_result


def test_daily_trend(
    client: TestClient,
    monkeypatch,
) -> None:
    expected_result = [
        {
            "pickup_date": date(
                2026,
                1,
                1,
            ),
            "trip_count": 500,
            "avg_total_amount": 25.50,
        },
        {
            "pickup_date": date(
                2026,
                1,
                2,
            ),
            "trip_count": 600,
            "avg_total_amount": 27.25,
        },
    ]

    def fake_fetch_daily_trend(filters):
        return expected_result

    monkeypatch.setattr(
        dashboard_router,
        "get_daily_trend_service",
        fake_fetch_daily_trend,
    )

    response = client.get(
        "/api/v1/dashboard/daily-trend"
    )

    assert response.status_code == 200

    assert response.json() == [
        {
            "pickup_date": "2026-01-01",
            "trip_count": 500,
            "avg_total_amount": 25.5,
        },
        {
            "pickup_date": "2026-01-02",
            "trip_count": 600,
            "avg_total_amount": 27.25,
        },
    ]

def test_invalid_hour_returns_422(
    client: TestClient,
) -> None:
    response = client.get(
        "/api/v1/dashboard/summary?hour=25"
    )

    assert response.status_code == 422


def test_invalid_weekday_returns_422(
    client: TestClient,
) -> None:
    response = client.get(
        "/api/v1/dashboard/summary?weekday=8"
    )

    assert response.status_code == 422


def test_invalid_date_range_returns_400(
    client: TestClient,
) -> None:
    response = client.get(
        (
            "/api/v1/dashboard/summary"
            "?date_from=2026-01-20"
            "&date_to=2026-01-10"
        )
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Start date cannot be later than end date."
    )