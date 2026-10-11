"""
Weather Tool
Fetches current weather data from OpenWeatherMap or returns labelled demo data.
"""
from __future__ import annotations

import os
import requests

from models.schemas import WeatherData

# Read at call time (not module level) so load_dotenv() in app.py always wins.
OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
TIMEOUT_SECONDS = 10

# Demo data used when no API key is configured (clearly labelled)
_DEMO_WEATHER = WeatherData(
    location="Demo Location",
    temperature_c=24.0,
    humidity_pct=68.0,
    description="partly cloudy (DEMO DATA — not a real observation)",
    wind_speed_ms=3.5,
    rainfall_mm=0.0,
    forecast_summary=(
        "[DEMO DATA] This is sample weather data shown because no live weather "
        "API key is configured. Configure OPENWEATHER_API_KEY in your .env file "
        "to receive real weather information."
    ),
    is_demo=True,
)


def get_weather(location: str) -> WeatherData:
    """
    Retrieve current weather for *location*.

    Uses OpenWeatherMap if OPENWEATHER_API_KEY is set.
    Falls back to clearly labelled demo data when the key is absent.
    Never fabricates real weather values.

    Args:
        location: City name or region provided by the farmer.

    Returns:
        WeatherData instance.
    """
    # Read key at call time so load_dotenv() in app.py is guaranteed to have run first
    api_key = os.environ.get("OPENWEATHER_API_KEY", "").strip()

    if not api_key:
        demo = _DEMO_WEATHER.model_copy(update={"location": f"{location} (demo)"})
        return demo

    params = {
        "q": location,
        "appid": api_key,
        "units": "metric",
    }

    try:
        response = requests.get(OPENWEATHER_BASE_URL, params=params, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        data = response.json()

        main = data.get("main", {})
        wind = data.get("wind", {})
        weather_desc = data.get("weather", [{}])[0].get("description", "N/A")
        rain = data.get("rain", {}).get("1h", 0.0)

        return WeatherData(
            location=data.get("name", location),
            temperature_c=main.get("temp"),
            humidity_pct=main.get("humidity"),
            description=weather_desc,
            wind_speed_ms=wind.get("speed"),
            rainfall_mm=rain,
            forecast_summary=None,
            is_demo=False,
        )

    except requests.exceptions.ConnectionError:
        return WeatherData(
            location=location,
            error="Could not connect to the weather service. Check your internet connection.",
            is_demo=False,
        )
    except requests.exceptions.Timeout:
        return WeatherData(
            location=location,
            error="Weather service request timed out. Please try again later.",
            is_demo=False,
        )
    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        if status == 401:
            msg = "Invalid or missing OpenWeatherMap API key (HTTP 401)."
        elif status == 404:
            msg = f"Location '{location}' not found by the weather service. Try a nearby city name."
        else:
            msg = f"Weather API returned an error (HTTP {status})."
        return WeatherData(location=location, error=msg, is_demo=False)
    except Exception as exc:  # noqa: BLE001
        return WeatherData(
            location=location,
            error=f"Unexpected weather error: {exc}",
            is_demo=False,
        )
