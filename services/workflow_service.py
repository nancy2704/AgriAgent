"""
Workflow Service
Orchestrates the full AgriAgent agentic workflow:
intake → research → weather → planning → persist → follow-up
"""
from __future__ import annotations

from typing import Optional

from models.schemas import (
    ActionPlan,
    FarmerInput,
    ResearchResult,
    WeatherData,
    WorkflowResult,
)
from agents import intake_agent, research_agent, weather_agent, planning_agent, followup_agent
from database import db


def run_workflow(
    crop_name: str,
    location: str,
    symptoms: str,
    symptom_duration: Optional[str] = None,
    additional_notes: Optional[str] = None,
    save_to_db: bool = True,
) -> tuple[Optional[WorkflowResult], list[str]]:
    """
    Execute the complete AgriAgent agentic workflow.

    Workflow steps:
    1. Validate farmer input (Intake Agent).
    2. Check which information is available.
    3. Retrieve agricultural knowledge (Research Agent).
    4. Retrieve weather data (Weather Agent).
    5. Combine evidence and produce action plan (Planning Agent).
    6. Persist query, report, and sources to the database.
    7. Generate default follow-up tasks.

    Args:
        crop_name, location, symptoms, symptom_duration, additional_notes:
            Raw farmer inputs.
        save_to_db:
            If False, skips persistence (useful for tests/demo mode).

    Returns:
        (WorkflowResult, []) on success.
        (None, [error messages]) on validation failure.
    """
    # Step 1 — Intake validation
    farmer_input, errors = intake_agent.validate_farmer_input(
        crop_name=crop_name,
        location=location,
        symptoms=symptoms,
        symptom_duration=symptom_duration,
        additional_notes=additional_notes,
    )
    if errors:
        return None, errors

    # Step 2 — Research
    research: ResearchResult = research_agent.run_research(farmer_input)

    # Step 3 — Weather
    weather: WeatherData = weather_agent.run_weather(farmer_input)

    # Step 4 — Planning
    action_plan: ActionPlan = planning_agent.run_planning(farmer_input, research, weather)

    query_id: Optional[int] = None
    report_id: Optional[int] = None

    # Step 5 — Persist
    if save_to_db:
        db.initialize_db()

        query_id = db.save_farmer_query(
            crop_name=farmer_input.crop_name,
            location=farmer_input.location,
            symptoms=farmer_input.symptoms,
            symptom_duration=farmer_input.symptom_duration,
            additional_notes=farmer_input.additional_notes,
        )

        weather_summary = None
        if not weather.error and weather.temperature_c is not None:
            weather_summary = (
                f"Temp: {weather.temperature_c}°C, Humidity: {weather.humidity_pct}%, "
                f"Conditions: {weather.description}"
            )
        elif weather.error:
            weather_summary = f"Weather unavailable: {weather.error}"

        research_summary = None
        if research.entries:
            topics = ", ".join(e.topic for e in research.entries)
            research_summary = f"Matched topics: {topics}"

        report_id = db.save_report(
            query_id=query_id,
            action_plan=action_plan.summary,
            research_summary=research_summary,
            weather_summary=weather_summary,
            uncertainty_notes=action_plan.uncertainty_notes,
        )

        for entry in research.entries:
            db.save_source_reference(
                report_id=report_id,
                source_title=entry.source_title,
                source_url=entry.source_url,
                relevance_note=f"Relevance score: {entry.relevance_score:.2f}",
            )

        # Step 6 — Generate default follow-up tasks
        followup_agent.generate_default_followup_tasks(
            report_id=report_id,
            crop_name=farmer_input.crop_name,
            observations_needed=action_plan.observations_needed,
        )

    is_demo = research.is_demo or weather.is_demo or (not bool(
        __import__("os").environ.get("OPENAI_API_KEY", "")
    ))

    result = WorkflowResult(
        query_id=query_id,
        report_id=report_id,
        farmer_input=farmer_input,
        research=research,
        weather=weather,
        action_plan=action_plan,
        sources=research.entries,
        is_demo=is_demo,
    )
    return result, []
