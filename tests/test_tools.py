"""
Tests for the tools layer (knowledge base, weather tool).
"""
import pytest
from unittest.mock import patch, MagicMock

from tools.agricultural_knowledge import search_knowledge_base
from tools.weather_tool import get_weather
from models.schemas import ResearchResult, WeatherData


# ---------------------------------------------------------------------------
# Agricultural Knowledge Tool
# ---------------------------------------------------------------------------

class TestAgriculturalKnowledge:

    def test_search_returns_result_type(self):
        result = search_knowledge_base("wheat", "yellow stripes on leaves")
        assert isinstance(result, ResearchResult)

    def test_search_finds_wheat_rust(self):
        result = search_knowledge_base("wheat", "yellow stripes on leaves rust")
        assert len(result.entries) > 0
        topics = [e.topic for e in result.entries]
        assert any("rust" in t for t in topics)

    def test_search_finds_rice_blast(self):
        result = search_knowledge_base("rice", "diamond shaped brown lesions blast")
        assert len(result.entries) > 0
        topics = [e.topic for e in result.entries]
        assert any("blast" in t for t in topics)

    def test_search_finds_tomato_late_blight(self):
        result = search_knowledge_base("tomato", "water soaked dark brown lesions late blight")
        assert len(result.entries) > 0
        topics = [e.topic for e in result.entries]
        assert any("blight" in t for t in topics)

    def test_search_finds_maize_fall_armyworm(self):
        result = search_knowledge_base("maize", "holes in leaves frass caterpillar armyworm")
        assert len(result.entries) > 0

    def test_no_results_returns_empty_with_note(self):
        result = search_knowledge_base("exotic_unknown_crop_xyz", "completely unknown symptom xyz abc")
        assert isinstance(result, ResearchResult)
        assert result.entries == []
        assert result.note is not None

    def test_top_k_limit(self):
        result = search_knowledge_base("wheat", "yellow spots rust blight fungal", top_k=2)
        assert len(result.entries) <= 2

    def test_general_category_matches_drought(self):
        result = search_knowledge_base("wheat", "wilting curling leaves drought stress")
        # Should find general drought entry even if not exact crop
        assert len(result.entries) > 0

    def test_relevance_scores_are_valid(self):
        result = search_knowledge_base("rice", "blast lesions brown")
        for entry in result.entries:
            assert 0.0 <= entry.relevance_score <= 1.0

    def test_is_demo_false_for_kb(self):
        result = search_knowledge_base("tomato", "brown spots blight")
        assert result.is_demo is False


# ---------------------------------------------------------------------------
# Weather Tool
# ---------------------------------------------------------------------------

class TestWeatherTool:

    def test_no_api_key_returns_demo_data(self):
        with patch.dict("os.environ", {}, clear=True):
            # Reload module to pick up cleared env
            import importlib
            import tools.weather_tool as wt
            importlib.reload(wt)
            result = wt.get_weather("Nairobi")
        assert isinstance(result, WeatherData)
        assert result.is_demo is True
        assert result.error is None

    def test_demo_data_includes_location(self):
        with patch.dict("os.environ", {}, clear=True):
            import importlib
            import tools.weather_tool as wt
            importlib.reload(wt)
            result = wt.get_weather("Accra")
        assert "Accra" in result.location or "demo" in result.location.lower()

    def test_connection_error_returns_error_field(self):
        import tools.weather_tool as wt
        with patch.dict("os.environ", {"OPENWEATHER_API_KEY": "fake_key_for_test"}):
            import importlib
            importlib.reload(wt)
            with patch("tools.weather_tool.requests.get", side_effect=ConnectionError("no connection")):
                result = wt.get_weather("Lagos")
        assert isinstance(result, WeatherData)
        assert result.error is not None
        assert result.is_demo is False

    def test_timeout_returns_error_field(self):
        import requests
        import tools.weather_tool as wt
        with patch.dict("os.environ", {"OPENWEATHER_API_KEY": "fake_key_for_test"}):
            import importlib
            importlib.reload(wt)
            with patch("tools.weather_tool.requests.get", side_effect=requests.exceptions.Timeout()):
                result = wt.get_weather("Kampala")
        assert result.error is not None
        assert "timed out" in result.error.lower()

    def test_invalid_api_key_401_returns_error(self):
        import requests
        import tools.weather_tool as wt
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        http_err = requests.exceptions.HTTPError(response=mock_resp)
        with patch.dict("os.environ", {"OPENWEATHER_API_KEY": "bad_key"}):
            import importlib
            importlib.reload(wt)
            with patch("tools.weather_tool.requests.get") as mock_get:
                mock_get.return_value.__enter__ = lambda s: s
                mock_get.return_value.raise_for_status = MagicMock(side_effect=http_err)
                mock_get.return_value.status_code = 401
                # Use HTTPError directly
                with patch("tools.weather_tool.requests.get", side_effect=http_err):
                    result = wt.get_weather("Unknown City")
        assert result.error is not None
        assert "401" in result.error or "API key" in result.error.lower() or result.error != ""

    def test_location_not_found_404(self):
        import requests
        import tools.weather_tool as wt
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        http_err = requests.exceptions.HTTPError(response=mock_resp)
        with patch.dict("os.environ", {"OPENWEATHER_API_KEY": "some_key"}):
            import importlib
            importlib.reload(wt)
            with patch("tools.weather_tool.requests.get", side_effect=http_err):
                result = wt.get_weather("NonExistentPlace99999")
        assert result.error is not None

    def test_successful_api_response(self):
        import tools.weather_tool as wt
        mock_data = {
            "name": "Nairobi",
            "main": {"temp": 22.5, "humidity": 75},
            "wind": {"speed": 4.2},
            "weather": [{"description": "partly cloudy"}],
            "rain": {},
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_data
        mock_resp.raise_for_status = MagicMock()
        with patch.dict("os.environ", {"OPENWEATHER_API_KEY": "valid_key"}):
            import importlib
            importlib.reload(wt)
            with patch("tools.weather_tool.requests.get", return_value=mock_resp):
                result = wt.get_weather("Nairobi")
        assert result.location == "Nairobi"
        assert result.temperature_c == 22.5
        assert result.humidity_pct == 75
        assert result.is_demo is False
        assert result.error is None
