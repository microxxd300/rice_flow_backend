import requests

from .cache import cached_by_location

FORECAST_URL  = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL   = "https://archive-api.open-meteo.com/v1/archive"
ELEVATION_URL = "https://api.open-meteo.com/v1/elevation"

HOUR = 60 * 60
DAY  = 24 * HOUR


@cached_by_location("openmeteo:elevation", ttl=30 * DAY)
def get_elevation(lat: float, lon: float) -> float:
    resp = requests.get(ELEVATION_URL, params={"latitude": lat, "longitude": lon}, timeout=10)
    resp.raise_for_status()
    return resp.json().get("elevation", [0])[0]


@cached_by_location("openmeteo:current_weather", ttl=HOUR // 2)
def get_current_weather(lat: float, lon: float) -> dict:
    params = {
        "latitude":    lat,
        "longitude":   lon,
        "daily":       ["temperature_2m_max", "temperature_2m_min", "precipitation_sum",
                        "relative_humidity_2m_max", "shortwave_radiation_sum", "windspeed_10m_max",
                        "sunshine_duration"],
        "timezone":    "Asia/Manila",
        "forecast_days": 7,
    }
    resp = requests.get(FORECAST_URL, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json().get("daily", {})

    temp_max  = data.get("temperature_2m_max", [27])[0]
    temp_min  = data.get("temperature_2m_min", [24])[0]
    avg_temp  = round((temp_max + temp_min) / 2, 1)
    rainfall  = sum(data.get("precipitation_sum", [0]))
    humidity  = data.get("relative_humidity_2m_max", [80])[0]
    radiation = data.get("shortwave_radiation_sum", [17])[0]
    wind      = data.get("windspeed_10m_max", [3])[0]
    sunshine  = data.get("sunshine_duration", [21600])[0] / 3600  # convert seconds to hours

    return {
        "avg_temperature":        avg_temp,
        "temp_at_flowering":      avg_temp,
        "weekly_rainfall_mm":     round(rainfall, 1),
        "humidity_pct":           humidity,
        "solar_radiation":        round(radiation, 1),
        "wind_speed_ms":          round(wind / 3.6, 1),  # km/h to m/s
        "sunshine_hours":         round(sunshine, 1),
    }


# Cropping seasons in Davao del Norte (DA reports): wet May-October, dry November-April
WET_MONTHS = range(5, 11)


def current_season(today=None) -> str:
    from datetime import date
    return 'wet' if (today or date.today()).month in WET_MONTHS else 'dry'


@cached_by_location("openmeteo:rainfall_summary", ttl=DAY)
def get_rainfall_summary(lat: float, lon: float) -> dict:
    """Rain over the last 365 days: the whole year, and the wet- and dry-season months."""
    from datetime import date, timedelta
    end   = date.today() - timedelta(days=5)
    start = end - timedelta(days=365)
    params = {
        "latitude":   lat,
        "longitude":  lon,
        "start_date": start.isoformat(),
        "end_date":   end.isoformat(),
        "daily":      "precipitation_sum",
        "timezone":   "Asia/Manila",
    }
    resp = requests.get(ARCHIVE_URL, params=params, timeout=15)
    resp.raise_for_status()
    daily = resp.json().get("daily", {})
    wet = dry = 0.0
    for day, mm in zip(daily.get("time", []), daily.get("precipitation_sum", [])):
        if mm is None:
            continue
        if int(day[5:7]) in WET_MONTHS:
            wet += mm
        else:
            dry += mm
    return {"annual": round(wet + dry, 1), "wet_season": round(wet, 1), "dry_season": round(dry, 1)}


MONTHLY_YEARS = 3


@cached_by_location("openmeteo:monthly_rainfall", ttl=7 * DAY)
def get_monthly_rainfall(lat: float, lon: float) -> list[float]:
    """Average rain per calendar month (mm, Jan..Dec) over the last 3 full years at the farm."""
    from datetime import date
    last_year = date.today().year - 1
    params = {
        "latitude":   lat,
        "longitude":  lon,
        "start_date": f"{last_year - MONTHLY_YEARS + 1}-01-01",
        "end_date":   f"{last_year}-12-31",
        "daily":      "precipitation_sum",
        "timezone":   "Asia/Manila",
    }
    resp = requests.get(ARCHIVE_URL, params=params, timeout=20)
    resp.raise_for_status()
    daily = resp.json().get("daily", {})
    totals = [0.0] * 12
    for day, mm in zip(daily.get("time", []), daily.get("precipitation_sum", [])):
        if mm is not None:
            totals[int(day[5:7]) - 1] += mm
    return [round(t / MONTHLY_YEARS, 1) for t in totals]
