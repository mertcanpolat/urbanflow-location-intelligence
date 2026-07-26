from fastapi.testclient import TestClient

import api.routers.forecast as forecast_router


def test_daily_demand_forecast(
    client: TestClient,
    monkeypatch,
) -> None:
    expected_result = [
        {
            "forecast_date": "2026-02-02",
            "weekday": 1,
            "predicted_trip_count": 118450,
            "lower_bound": 105200,
            "upper_bound": 131700,
            "sample_count": 4,
        },
        {
            "forecast_date": "2026-02-03",
            "weekday": 2,
            "predicted_trip_count": 121300,
            "lower_bound": 109500,
            "upper_bound": 133100,
            "sample_count": 4,
        },
    ]

    def fake_get_daily_demand_forecast(
        filters,
        forecast_days,
        history_weeks,
    ):
        assert forecast_days == 7
        assert history_weeks == 4

        return expected_result

    monkeypatch.setattr(
        forecast_router,
        "get_daily_demand_forecast_service",
        fake_get_daily_demand_forecast,
    )

    response = client.get(
        "/api/v1/forecast/daily-demand"
    )

    assert response.status_code == 200
    assert response.json() == expected_result
    

def test_invalid_forecast_days_returns_422(
    client: TestClient,
) -> None:
    response = client.get(
        "/api/v1/forecast/daily-demand"
        "?forecast_days=31"
    )

    assert response.status_code == 422


def test_invalid_history_weeks_returns_422(
    client: TestClient,
) -> None:
    response = client.get(
        "/api/v1/forecast/daily-demand"
        "?history_weeks=1"
    )

    assert response.status_code == 422