"""
Weather Agent
Retrieves current weather for the farmer's location.
Returns structured WeatherData; never fabricates observations.
"""
from __future__ import annotations

from models.schemas import FarmerInput, WeatherData
from tools.weather_tool import get_weather


def run_weather(farmer_input: FarmerInput) -> WeatherData:
    """
    Retrieve current weather data for the farmer's location.

    Returns a WeatherData object. If no API key is configured, returns
    clearly labelled demo data. If the API fails, the error field is
    populated and no weather values are invented.

    Args:
        farmer_input: Validated farmer problem submission.

    Returns:
        WeatherData instance.
    """
    return get_weather(farmer_input.location)
