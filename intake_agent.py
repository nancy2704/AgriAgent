"""
Farmer Intake Agent
Validates and normalises the farmer's problem submission.
"""
from __future__ import annotations

from typing import Optional
from pydantic import ValidationError

from models.schemas import FarmerInput


REQUIRED_FIELDS = {
    "crop_name": "crop name",
    "location": "farm location",
    "symptoms": "observed symptoms",
}


def validate_farmer_input(
    crop_name: str,
    location: str,
    symptoms: str,
    symptom_duration: Optional[str] = None,
    additional_notes: Optional[str] = None,
) -> tuple[Optional[FarmerInput], list[str]]:
    """
    Validate and normalise the farmer's input.

    Returns:
        (FarmerInput, []) on success.
        (None, [error messages]) on failure.
    """
    errors: list[str] = []

    # Check required fields are non-empty before Pydantic validation
    raw = {
        "crop_name": (crop_name or "").strip(),
        "location": (location or "").strip(),
        "symptoms": (symptoms or "").strip(),
        "symptom_duration": (symptom_duration or "").strip() or None,
        "additional_notes": (additional_notes or "").strip() or None,
    }

    for field, label in REQUIRED_FIELDS.items():
        if not raw[field]:
            errors.append(f"Missing required field: {label}.")

    if errors:
        return None, errors

    try:
        farmer_input = FarmerInput(**raw)
        return farmer_input, []
    except ValidationError as exc:
        for err in exc.errors():
            field = err.get("loc", ("field",))[-1]
            msg = err.get("msg", "Invalid value")
            errors.append(f"Validation error in '{field}': {msg}")
        return None, errors


def get_missing_field_prompts(
    crop_name: str,
    location: str,
    symptoms: str,
) -> list[str]:
    """
    Return a list of follow-up prompts for any missing required fields.
    Used by the UI to guide the farmer.
    """
    prompts = []
    if not (crop_name or "").strip():
        prompts.append("Which crop is affected? (e.g., wheat, rice, tomato)")
    if not (location or "").strip():
        prompts.append("Where is your farm located? (city, region, or country)")
    if not (symptoms or "").strip():
        prompts.append(
            "What symptoms are you observing? (e.g., yellow leaves, spots, wilting)"
        )
    return prompts
