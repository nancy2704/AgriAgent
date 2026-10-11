"""
Follow-Up Agent
Manages saving action plans, scheduling follow-up tasks, and tracking progress.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from models.schemas import FollowUpTask, FollowUpTaskUpdate
from database import db


def save_followup_task(task: FollowUpTask) -> int:
    """
    Persist a follow-up task to the database.

    Args:
        task: Validated FollowUpTask.

    Returns:
        The new task id.
    """
    due_date_str: Optional[str] = None
    if task.due_date:
        due_date_str = task.due_date.isoformat()

    if task.report_id is None:
        raise ValueError("report_id is required when saving a follow-up task.")

    task_id = db.save_followup_task(
        report_id=task.report_id,
        task_description=task.task_description,
        due_date=due_date_str,
    )
    return task_id


def update_task_status(update: FollowUpTaskUpdate) -> bool:
    """
    Update the status and optional observation notes of a follow-up task.

    Args:
        update: FollowUpTaskUpdate with task_id, status, and optional notes.

    Returns:
        True if the update was applied, False if the task was not found.
    """
    return db.update_followup_task(
        task_id=update.task_id,
        status=update.status,
        observation_notes=update.observation_notes,
    )


def get_pending_tasks(report_id: Optional[int] = None) -> list[dict]:
    """Return all pending follow-up tasks, optionally filtered by report."""
    return db.get_followup_tasks(report_id=report_id, status="pending")


def get_all_tasks(report_id: Optional[int] = None) -> list[dict]:
    """Return all follow-up tasks, optionally filtered by report."""
    return db.get_followup_tasks(report_id=report_id)


def generate_default_followup_tasks(
    report_id: int,
    crop_name: str,
    observations_needed: list[str],
) -> list[int]:
    """
    Generate and save default follow-up tasks derived from the action plan.

    Args:
        report_id:           The report to attach tasks to.
        crop_name:           Crop name for context.
        observations_needed: List of observations recommended in the action plan.

    Returns:
        List of saved task ids.
    """
    today = date.today()
    task_ids: list[int] = []

    # Standard follow-up check
    base_task = FollowUpTask(
        task_description=f"Check {crop_name} field for symptom changes",
        due_date=date.fromordinal(today.toordinal() + 3),
        report_id=report_id,
    )
    task_ids.append(save_followup_task(base_task))

    # Observation-based tasks
    for i, obs in enumerate(observations_needed[:3]):  # limit to 3
        task = FollowUpTask(
            task_description=f"Observe: {obs}",
            due_date=date.fromordinal(today.toordinal() + (i + 1) * 2),
            report_id=report_id,
        )
        task_ids.append(save_followup_task(task))

    return task_ids
