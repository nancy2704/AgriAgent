"""
Farming Planning Agent
Combines research results, weather data, and farmer symptoms to produce
a structured, uncertainty-aware action plan using the configured LLM.

Falls back to a template-based plan when no LLM API key is available,
clearly labelling it as a demo plan.
"""
from __future__ import annotations

import os
import json

from models.schemas import (
    ActionPlan,
    ActionStep,
    FarmerInput,
    ResearchResult,
    WeatherData,
)

# NOTE: do NOT read the key at module level — the module is imported before
# load_dotenv() has populated os.environ in some execution paths (Streamlit
# reloads, test collection, etc.).  Always read from os.environ at call time.

# System prompt enforcing safety and honesty constraints
_SYSTEM_PROMPT = """
You are AgriAgent's Farming Planning Assistant. You help smallholder farmers
understand crop problems and create practical action plans.

RULES you must always follow:
1. Never invent crop diagnoses. Base conclusions on the provided research evidence.
2. Do not prescribe specific pesticide dosages. Refer farmers to local extension services or labels.
3. Clearly communicate uncertainty. Use language like "may indicate", "consistent with", "possible".
4. Recommend consulting a qualified agronomist for severe or ambiguous problems.
5. Never claim to perform searches you did not perform.
6. Keep recommendations practical and accessible for smallholder farmers.
7. Return ONLY valid JSON matching the schema provided — no extra text before or after.

RESPONSE FORMAT — strict JSON:
{
  "summary": "...",
  "likely_issues": ["...", "..."],
  "steps": [
    {"step_number": 1, "action": "...", "rationale": "...", "urgency": "normal"},
    ...
  ],
  "observations_needed": ["...", "..."],
  "expert_consultation_recommended": true/false,
  "uncertainty_notes": "..."
}
Urgency values: low | normal | high | urgent
"""


def _build_user_message(
    farmer_input: FarmerInput,
    research: ResearchResult,
    weather: WeatherData,
) -> str:
    """Compose the LLM user message from structured inputs."""
    research_text = ""
    if research.entries:
        for e in research.entries:
            research_text += (
                f"\n- [{e.topic.title()}] ({e.source_title}): {e.content[:400]}"
            )
    else:
        research_text = "\nNo matching entries found in the local knowledge base."

    weather_text = ""
    if weather.error:
        weather_text = f"Weather data unavailable: {weather.error}"
    elif weather.is_demo:
        weather_text = f"[DEMO WEATHER] Location: {weather.location}, Temp: {weather.temperature_c}°C, Humidity: {weather.humidity_pct}%"
    else:
        weather_text = (
            f"Location: {weather.location}, Temp: {weather.temperature_c}°C, "
            f"Humidity: {weather.humidity_pct}%, "
            f"Conditions: {weather.description}, "
            f"Wind: {weather.wind_speed_ms} m/s, "
            f"Rainfall (last hour): {weather.rainfall_mm} mm"
        )

    return f"""FARMER REPORT:
Crop: {farmer_input.crop_name}
Location: {farmer_input.location}
Symptoms: {farmer_input.symptoms}
Duration: {farmer_input.symptom_duration or "Not specified"}
Additional Notes: {farmer_input.additional_notes or "None"}

WEATHER DATA:
{weather_text}

RESEARCH EVIDENCE FROM KNOWLEDGE BASE:
{research_text}

Based on the above, produce a structured farming action plan in JSON."""


def _template_plan(farmer_input: FarmerInput, research: ResearchResult) -> ActionPlan:
    """
    Template-based fallback plan used when no LLM API key is configured.
    Clearly labelled as a demo plan. Uses only knowledge base content.
    """
    steps: list[ActionStep] = [
        ActionStep(
            step_number=1,
            action="Document and photograph the affected plants",
            rationale="Visual records help track disease progression and support diagnosis by an expert.",
            urgency="normal",
        ),
        ActionStep(
            step_number=2,
            action="Isolate severely affected plants if possible",
            rationale="Prevents potential spread of infectious diseases to healthy plants.",
            urgency="high",
        ),
        ActionStep(
            step_number=3,
            action="Check soil moisture and recent irrigation history",
            rationale="Moisture stress can cause or exacerbate many symptoms including wilting and leaf scorch.",
            urgency="normal",
        ),
        ActionStep(
            step_number=4,
            action="Contact your local agricultural extension office or agronomist",
            rationale="A qualified expert can inspect the field directly and provide region-specific advice.",
            urgency="high",
        ),
    ]

    likely_issues: list[str] = []
    if research.entries:
        for e in research.entries[:2]:
            likely_issues.append(f"{e.topic.title()} — see: {e.source_title}")

    if not likely_issues:
        likely_issues = ["Insufficient evidence for a specific diagnosis — field inspection recommended."]

    return ActionPlan(
        summary=(
            f"[DEMO PLAN — LLM not configured] "
            f"Based on the reported symptoms on {farmer_input.crop_name} in {farmer_input.location}, "
            "the following general steps are recommended. Configure your OpenAI API key for an AI-generated plan."
        ),
        likely_issues=likely_issues,
        steps=steps,
        observations_needed=[
            "Count and map affected plants to estimate spread.",
            "Check if symptoms are worse in specific field areas (low-lying, edges, etc.).",
            "Look for insects, fungal growth, or unusual odours on affected plants.",
        ],
        expert_consultation_recommended=True,
        uncertainty_notes=(
            "This is a template-based demo plan. No LLM analysis was performed. "
            "The likely issues listed are based on the local knowledge base only. "
            "Always consult a qualified agronomist before taking action."
        ),
    )


def _classify_openai_error(exc: Exception) -> str:
    """
    Return a user-friendly, diagnostic message for an OpenAI API error.
    Never includes the API key itself.
    """
    exc_type = type(exc).__name__
    exc_str = str(exc)

    # openai >= 1.x uses typed exception classes
    if "AuthenticationError" in exc_type or "401" in exc_str or "Incorrect API key" in exc_str:
        return (
            "OpenAI API key error (AuthenticationError): The key was rejected by OpenAI. "
            "Check that OPENAI_API_KEY in your .env file is correct, active, and has not expired. "
            "Obtain a new key at https://platform.openai.com/api-keys if needed."
        )
    if "RateLimitError" in exc_type or "429" in exc_str:
        return (
            "OpenAI rate limit reached (RateLimitError): Too many requests or quota exceeded. "
            "Wait a moment, check your usage at https://platform.openai.com/usage, or upgrade your plan."
        )
    if "NotFoundError" in exc_type or "404" in exc_str:
        return (
            "OpenAI model not found (NotFoundError): The model 'gpt-4o-mini' is not available "
            "on this API key or account. Confirm your account has access to this model."
        )
    if "APIConnectionError" in exc_type or "ConnectionError" in exc_type:
        return (
            "Network error (APIConnectionError): Could not reach the OpenAI API. "
            "Check your internet connection."
        )
    if "Timeout" in exc_type:
        return "OpenAI request timed out. Try again in a moment."
    # Generic fallback — include type but not the full message (may contain key fragments)
    return f"OpenAI API error ({exc_type}): {exc_str[:200]}"


def run_planning(
    farmer_input: FarmerInput,
    research: ResearchResult,
    weather: WeatherData,
) -> ActionPlan:
    """
    Produce a structured action plan by combining all available evidence.

    Reads OPENAI_API_KEY fresh from os.environ on every call so that
    load_dotenv() in app.py is guaranteed to have run first regardless
    of module import order.

    Uses the OpenAI API when OPENAI_API_KEY is set; falls back to a
    clearly-labelled template-based demo plan otherwise.

    Args:
        farmer_input: Validated farmer input.
        research:     Results from the research agent.
        weather:      Weather data from the weather agent.

    Returns:
        ActionPlan instance.
    """
    # Read key at call time, not module-import time
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()

    if not api_key:
        return _template_plan(farmer_input, research)

    try:
        from openai import OpenAI  # imported lazily to avoid hard dependency crash

        client = OpenAI(api_key=api_key)
        user_message = _build_user_message(farmer_input, research, weather)

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT.strip()},
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,
            max_tokens=1200,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content or "{}"
        data = json.loads(raw)

        steps = [
            ActionStep(
                step_number=s.get("step_number", i + 1),
                action=s.get("action", ""),
                rationale=s.get("rationale", ""),
                urgency=s.get("urgency", "normal"),
            )
            for i, s in enumerate(data.get("steps", []))
        ]

        return ActionPlan(
            summary=data.get("summary", ""),
            likely_issues=data.get("likely_issues", []),
            steps=steps,
            observations_needed=data.get("observations_needed", []),
            expert_consultation_recommended=data.get("expert_consultation_recommended", True),
            uncertainty_notes=data.get("uncertainty_notes"),
        )

    except json.JSONDecodeError:
        fallback = _template_plan(farmer_input, research)
        fallback.uncertainty_notes = (
            "[DEMO PLAN] The OpenAI response could not be parsed as valid JSON. "
            "Try again; if the problem persists check your model access. "
            + (fallback.uncertainty_notes or "")
        )
        return fallback
    except Exception as exc:  # noqa: BLE001
        diagnostic = _classify_openai_error(exc)
        fallback = _template_plan(farmer_input, research)
        fallback.uncertainty_notes = (
            f"[DEMO PLAN — LLM unavailable] {diagnostic} "
            + (fallback.uncertainty_notes or "")
        )
        return fallback
