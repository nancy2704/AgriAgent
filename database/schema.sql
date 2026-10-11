-- AgriAgent SQLite Schema
-- Version 1.0

CREATE TABLE IF NOT EXISTS farmer_queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    crop_name TEXT NOT NULL,
    location TEXT NOT NULL,
    symptoms TEXT NOT NULL,
    symptom_duration TEXT,
    additional_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS analysis_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_id INTEGER NOT NULL REFERENCES farmer_queries(id),
    research_summary TEXT,
    weather_summary TEXT,
    action_plan TEXT NOT NULL,
    uncertainty_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS source_references (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL REFERENCES analysis_reports(id),
    source_title TEXT NOT NULL,
    source_url TEXT,
    relevance_note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS followup_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL REFERENCES analysis_reports(id),
    task_description TEXT NOT NULL,
    due_date DATE,
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'completed', 'skipped')),
    observation_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_queries_created ON farmer_queries(created_at);
CREATE INDEX IF NOT EXISTS idx_reports_query ON analysis_reports(query_id);
CREATE INDEX IF NOT EXISTS idx_followup_report ON followup_tasks(report_id);
CREATE INDEX IF NOT EXISTS idx_followup_status ON followup_tasks(status);
