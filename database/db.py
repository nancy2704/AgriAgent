"""
AgriAgent Database Layer
Handles SQLite connection, initialization, and CRUD operations.
"""
import sqlite3
import os
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

DB_PATH = os.environ.get("AGRIAGENT_DB_PATH", "agriagent.db")
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Return a SQLite connection with row factory set."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db_session(db_path: str = DB_PATH):
    """Context manager for a database session with auto-commit/rollback."""
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def initialize_db(db_path: str = DB_PATH) -> None:
    """Create tables from schema.sql if they do not already exist."""
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with db_session(db_path) as conn:
        conn.executescript(schema_sql)


# ---------------------------------------------------------------------------
# Farmer Queries
# ---------------------------------------------------------------------------

def save_farmer_query(
    crop_name: str,
    location: str,
    symptoms: str,
    symptom_duration: Optional[str] = None,
    additional_notes: Optional[str] = None,
    db_path: str = DB_PATH,
) -> int:
    """Insert a farmer query and return its new id."""
    sql = """
        INSERT INTO farmer_queries
            (crop_name, location, symptoms, symptom_duration, additional_notes)
        VALUES (?, ?, ?, ?, ?)
    """
    with db_session(db_path) as conn:
        cur = conn.execute(sql, (crop_name, location, symptoms, symptom_duration, additional_notes))
        return cur.lastrowid


def get_all_queries(db_path: str = DB_PATH) -> list[dict]:
    """Return all farmer queries ordered by most recent first."""
    sql = "SELECT * FROM farmer_queries ORDER BY created_at DESC"
    with db_session(db_path) as conn:
        rows = conn.execute(sql).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Analysis Reports
# ---------------------------------------------------------------------------

def save_report(
    query_id: int,
    action_plan: str,
    research_summary: Optional[str] = None,
    weather_summary: Optional[str] = None,
    uncertainty_notes: Optional[str] = None,
    db_path: str = DB_PATH,
) -> int:
    """Insert an analysis report and return its new id."""
    sql = """
        INSERT INTO analysis_reports
            (query_id, action_plan, research_summary, weather_summary, uncertainty_notes)
        VALUES (?, ?, ?, ?, ?)
    """
    with db_session(db_path) as conn:
        cur = conn.execute(sql, (query_id, action_plan, research_summary, weather_summary, uncertainty_notes))
        return cur.lastrowid


def get_report(report_id: int, db_path: str = DB_PATH) -> Optional[dict]:
    """Return a single report by id."""
    sql = "SELECT * FROM analysis_reports WHERE id = ?"
    with db_session(db_path) as conn:
        row = conn.execute(sql, (report_id,)).fetchone()
        return dict(row) if row else None


def get_reports_for_query(query_id: int, db_path: str = DB_PATH) -> list[dict]:
    """Return all reports associated with a query."""
    sql = "SELECT * FROM analysis_reports WHERE query_id = ? ORDER BY created_at DESC"
    with db_session(db_path) as conn:
        rows = conn.execute(sql, (query_id,)).fetchall()
        return [dict(r) for r in rows]


def get_all_reports(db_path: str = DB_PATH) -> list[dict]:
    """Return all reports joined with their farmer query data."""
    sql = """
        SELECT r.*, q.crop_name, q.location, q.symptoms, q.created_at AS query_created_at
        FROM analysis_reports r
        JOIN farmer_queries q ON r.query_id = q.id
        ORDER BY r.created_at DESC
    """
    with db_session(db_path) as conn:
        rows = conn.execute(sql).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Source References
# ---------------------------------------------------------------------------

def save_source_reference(
    report_id: int,
    source_title: str,
    source_url: Optional[str] = None,
    relevance_note: Optional[str] = None,
    db_path: str = DB_PATH,
) -> int:
    """Insert a source reference and return its new id."""
    sql = """
        INSERT INTO source_references (report_id, source_title, source_url, relevance_note)
        VALUES (?, ?, ?, ?)
    """
    with db_session(db_path) as conn:
        cur = conn.execute(sql, (report_id, source_title, source_url, relevance_note))
        return cur.lastrowid


def get_sources_for_report(report_id: int, db_path: str = DB_PATH) -> list[dict]:
    """Return all source references for a report."""
    sql = "SELECT * FROM source_references WHERE report_id = ?"
    with db_session(db_path) as conn:
        rows = conn.execute(sql, (report_id,)).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Follow-up Tasks
# ---------------------------------------------------------------------------

def save_followup_task(
    report_id: int,
    task_description: str,
    due_date: Optional[str] = None,
    db_path: str = DB_PATH,
) -> int:
    """Insert a follow-up task and return its new id."""
    sql = """
        INSERT INTO followup_tasks (report_id, task_description, due_date)
        VALUES (?, ?, ?)
    """
    with db_session(db_path) as conn:
        cur = conn.execute(sql, (report_id, task_description, due_date))
        return cur.lastrowid


def get_followup_tasks(
    report_id: Optional[int] = None,
    status: Optional[str] = None,
    db_path: str = DB_PATH,
) -> list[dict]:
    """Return follow-up tasks optionally filtered by report_id and/or status."""
    conditions = []
    params = []
    if report_id is not None:
        conditions.append("report_id = ?")
        params.append(report_id)
    if status is not None:
        conditions.append("status = ?")
        params.append(status)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    sql = f"SELECT * FROM followup_tasks {where} ORDER BY due_date ASC, created_at ASC"
    with db_session(db_path) as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def update_followup_task(
    task_id: int,
    status: str,
    observation_notes: Optional[str] = None,
    db_path: str = DB_PATH,
) -> bool:
    """Update the status and optional notes of a follow-up task. Returns True if updated."""
    sql = """
        UPDATE followup_tasks
        SET status = ?, observation_notes = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """
    with db_session(db_path) as conn:
        cur = conn.execute(sql, (status, observation_notes, task_id))
        return cur.rowcount > 0
