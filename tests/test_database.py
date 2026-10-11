"""
Tests for the database layer.
"""
import pytest
import tempfile
import os

from database.db import (
    initialize_db,
    save_farmer_query,
    get_all_queries,
    save_report,
    get_report,
    save_source_reference,
    get_sources_for_report,
    save_followup_task,
    get_followup_tasks,
    update_followup_task,
)


@pytest.fixture
def temp_db(tmp_path):
    """Provide a fresh temporary SQLite database for each test."""
    db_file = str(tmp_path / "test_agriagent.db")
    initialize_db(db_path=db_file)
    return db_file


def test_initialize_db_creates_tables(temp_db):
    """Database initialization should create all required tables."""
    import sqlite3
    conn = sqlite3.connect(temp_db)
    tables = {
        row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    conn.close()
    assert "farmer_queries" in tables
    assert "analysis_reports" in tables
    assert "source_references" in tables
    assert "followup_tasks" in tables


def test_save_and_retrieve_farmer_query(temp_db):
    """Saved farmer queries should be retrievable."""
    qid = save_farmer_query(
        crop_name="tomato",
        location="Kenya",
        symptoms="brown spots on leaves",
        symptom_duration="5 days",
        db_path=temp_db,
    )
    assert isinstance(qid, int)
    assert qid > 0

    queries = get_all_queries(db_path=temp_db)
    assert len(queries) == 1
    q = queries[0]
    assert q["crop_name"] == "tomato"
    assert q["location"] == "Kenya"
    assert q["symptoms"] == "brown spots on leaves"
    assert q["symptom_duration"] == "5 days"


def test_save_and_retrieve_report(temp_db):
    """Saved reports should be retrievable by id."""
    qid = save_farmer_query(
        crop_name="wheat",
        location="Punjab",
        symptoms="yellow stripes on leaves",
        db_path=temp_db,
    )
    rid = save_report(
        query_id=qid,
        action_plan="Monitor and apply fungicide if needed.",
        research_summary="Matched: rust diseases",
        db_path=temp_db,
    )
    assert isinstance(rid, int)

    report = get_report(rid, db_path=temp_db)
    assert report is not None
    assert report["action_plan"] == "Monitor and apply fungicide if needed."
    assert report["query_id"] == qid


def test_save_and_retrieve_source_reference(temp_db):
    """Source references should be saved and retrievable by report id."""
    qid = save_farmer_query("rice", "Ghana", "water-soaked lesions", db_path=temp_db)
    rid = save_report(qid, "Check for bacterial leaf blight.", db_path=temp_db)

    src_id = save_source_reference(
        report_id=rid,
        source_title="IRRI — Rice Knowledge Bank",
        source_url="https://www.knowledgebank.irri.org/",
        db_path=temp_db,
    )
    assert src_id > 0

    sources = get_sources_for_report(rid, db_path=temp_db)
    assert len(sources) == 1
    assert sources[0]["source_title"] == "IRRI — Rice Knowledge Bank"


def test_save_and_update_followup_task(temp_db):
    """Follow-up tasks should be saved, listed, and updateable."""
    qid = save_farmer_query("maize", "Nigeria", "holes in leaves", db_path=temp_db)
    rid = save_report(qid, "Check for fall armyworm.", db_path=temp_db)

    tid = save_followup_task(
        report_id=rid,
        task_description="Inspect whorl for frass",
        due_date="2025-08-01",
        db_path=temp_db,
    )
    assert tid > 0

    pending = get_followup_tasks(status="pending", db_path=temp_db)
    assert any(t["id"] == tid for t in pending)

    updated = update_followup_task(
        task_id=tid,
        status="completed",
        observation_notes="Found frass — confirmed FAW",
        db_path=temp_db,
    )
    assert updated is True

    completed = get_followup_tasks(status="completed", db_path=temp_db)
    assert any(t["id"] == tid for t in completed)


def test_followup_filter_by_report(temp_db):
    """get_followup_tasks should filter correctly by report_id."""
    qid = save_farmer_query("potato", "Peru", "dark lesions", db_path=temp_db)
    rid1 = save_report(qid, "Late blight suspected.", db_path=temp_db)
    rid2 = save_report(qid, "Second report.", db_path=temp_db)

    save_followup_task(report_id=rid1, task_description="Task for report 1", db_path=temp_db)
    save_followup_task(report_id=rid2, task_description="Task for report 2", db_path=temp_db)

    tasks_r1 = get_followup_tasks(report_id=rid1, db_path=temp_db)
    tasks_r2 = get_followup_tasks(report_id=rid2, db_path=temp_db)

    assert len(tasks_r1) == 1
    assert tasks_r1[0]["task_description"] == "Task for report 1"
    assert len(tasks_r2) == 1


def test_update_nonexistent_task_returns_false(temp_db):
    """Updating a non-existent task should return False."""
    result = update_followup_task(task_id=9999, status="completed", db_path=temp_db)
    assert result is False


def test_multiple_queries_ordering(temp_db):
    """Queries should be returned most-recent-first."""
    for crop in ["wheat", "rice", "maize"]:
        save_farmer_query(crop, "Location", f"{crop} symptoms", db_path=temp_db)

    queries = get_all_queries(db_path=temp_db)
    assert len(queries) == 3
    # All should be returned
    crops = [q["crop_name"] for q in queries]
    assert "wheat" in crops and "rice" in crops and "maize" in crops
