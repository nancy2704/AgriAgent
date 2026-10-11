"""
Report Service
Helper functions for retrieving and formatting stored reports and follow-up tasks.
"""
from __future__ import annotations

from typing import Optional
from database import db


def get_all_reports_summary() -> list[dict]:
    """Return all reports joined with their farmer query data."""
    return db.get_all_reports()


def get_report_detail(report_id: int) -> Optional[dict]:
    """Return a report with its sources."""
    report = db.get_report(report_id)
    if report is None:
        return None
    sources = db.get_sources_for_report(report_id)
    report["sources"] = sources
    return report


def get_followup_dashboard() -> dict:
    """
    Return a summary dict for the follow-up dashboard.

    Returns:
        {
            "pending": [...],
            "completed": [...],
            "skipped": [...],
            "total": int,
        }
    """
    pending = db.get_followup_tasks(status="pending")
    completed = db.get_followup_tasks(status="completed")
    skipped = db.get_followup_tasks(status="skipped")
    return {
        "pending": pending,
        "completed": completed,
        "skipped": skipped,
        "total": len(pending) + len(completed) + len(skipped),
    }
