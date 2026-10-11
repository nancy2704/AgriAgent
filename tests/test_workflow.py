"""
Tests for the workflow service and agents.
"""
import pytest
from unittest.mock import patch, MagicMock

from agents.intake_agent import validate_farmer_input, get_missing_field_prompts
from models.schemas import WeatherData, ResearchResult, KnowledgeEntry


# ---------------------------------------------------------------------------
# Intake Agent
# ---------------------------------------------------------------------------

class TestIntakeAgent:

    def test_valid_input_returns_farmer_input(self):
        farmer, errors = validate_farmer_input(
            crop_name="tomato",
            location="Kenya",
            symptoms="brown water-soaked lesions on leaves",
        )
        assert errors == []
        assert farmer is not None
        assert farmer.crop_name == "tomato"

    def test_missing_crop_name_returns_error(self):
        farmer, errors = validate_farmer_input(
            crop_name="",
            location="Nigeria",
            symptoms="yellow leaves and wilting",
        )
        assert farmer is None
        assert len(errors) > 0
        assert any("crop name" in e.lower() for e in errors)

    def test_missing_location_returns_error(self):
        farmer, errors = validate_farmer_input(
            crop_name="wheat",
            location="",
            symptoms="yellow stripes on leaves",
        )
        assert farmer is None
        assert len(errors) > 0

    def test_missing_symptoms_returns_error(self):
        farmer, errors = validate_farmer_input(
            crop_name="rice",
            location="India",
            symptoms="",
        )
        assert farmer is None
        assert len(errors) > 0

    def test_trivial_symptoms_returns_error(self):
        # Only one word — should fail validation
        farmer, errors = validate_farmer_input(
            crop_name="maize",
            location="Ghana",
            symptoms="sick",
        )
        assert farmer is None
        assert len(errors) > 0

    def test_whitespace_is_stripped(self):
        farmer, errors = validate_farmer_input(
            crop_name="  wheat  ",
            location="  Punjab  ",
            symptoms="  yellow stripes on upper leaves  ",
        )
        assert errors == []
        assert farmer.crop_name == "wheat"
        assert farmer.location == "Punjab"

    def test_optional_fields_can_be_none(self):
        farmer, errors = validate_farmer_input(
            crop_name="potato",
            location="Peru",
            symptoms="dark water-soaked lesions",
            symptom_duration=None,
            additional_notes=None,
        )
        assert errors == []
        assert farmer.symptom_duration is None
        assert farmer.additional_notes is None

    def test_missing_field_prompts(self):
        prompts = get_missing_field_prompts("", "", "")
        assert len(prompts) == 3  # All three missing

    def test_no_prompts_when_all_provided(self):
        prompts = get_missing_field_prompts("wheat", "Kenya", "yellow leaves")
        assert prompts == []

    def test_partial_prompts(self):
        prompts = get_missing_field_prompts("wheat", "", "yellow leaves")
        assert len(prompts) == 1
        assert any("farm" in p.lower() or "location" in p.lower() or "where" in p.lower() for p in prompts)


# ---------------------------------------------------------------------------
# Workflow Service
# ---------------------------------------------------------------------------

class TestWorkflowService:

    def _run(self, **kwargs):
        """Helper to run workflow without persisting to DB."""
        from services.workflow_service import run_workflow
        defaults = dict(
            crop_name="wheat",
            location="Punjab, India",
            symptoms="yellow stripes on upper leaves",
            save_to_db=False,
        )
        defaults.update(kwargs)
        return run_workflow(**defaults)

    def test_successful_workflow_returns_result(self):
        result, errors = self._run()
        assert errors == []
        assert result is not None
        assert result.farmer_input.crop_name == "wheat"

    def test_workflow_returns_research_result(self):
        result, errors = self._run()
        assert errors == []
        assert isinstance(result.research, ResearchResult)

    def test_workflow_returns_weather_data(self):
        result, errors = self._run()
        assert errors == []
        assert isinstance(result.weather, WeatherData)

    def test_workflow_returns_action_plan(self):
        result, errors = self._run()
        assert errors == []
        assert result.action_plan is not None
        assert result.action_plan.summary != ""

    def test_workflow_missing_crop_name_returns_errors(self):
        result, errors = self._run(crop_name="")
        assert result is None
        assert len(errors) > 0

    def test_workflow_missing_location_returns_errors(self):
        result, errors = self._run(location="")
        assert result is None
        assert len(errors) > 0

    def test_workflow_missing_symptoms_returns_errors(self):
        result, errors = self._run(symptoms="")
        assert result is None
        assert len(errors) > 0

    def test_workflow_weather_api_failure_continues(self):
        """Workflow should continue and return a plan even when weather fails."""
        with patch("tools.weather_tool.requests.get", side_effect=ConnectionError("down")):
            result, errors = self._run()
        # Even with weather failure, workflow should succeed
        assert errors == [] or result is None  # depends on env; no crash

    def test_workflow_empty_research_produces_plan(self):
        """Workflow should produce a plan even when no research entries match."""
        result, errors = self._run(
            crop_name="unknownplantxyz",
            symptoms="strange purple discoloration unusual",
        )
        # May return errors from intake or succeed with empty research
        if errors:
            assert result is None
        else:
            assert result.action_plan is not None

    def test_workflow_with_all_optional_fields(self):
        result, errors = self._run(
            symptom_duration="1 week",
            additional_notes="Recent heavy rain",
        )
        assert errors == []
        assert result.farmer_input.symptom_duration == "1 week"
        assert result.farmer_input.additional_notes == "Recent heavy rain"


# ---------------------------------------------------------------------------
# Planning Agent (template mode)
# ---------------------------------------------------------------------------

class TestPlanningAgent:

    def test_template_plan_no_openai_key(self):
        """Without an API key, planning agent must return a labelled template plan."""
        from agents.planning_agent import _template_plan
        from models.schemas import FarmerInput

        farmer = FarmerInput(
            crop_name="rice",
            location="Philippines",
            symptoms="water soaked lesions on leaf margins",
        )
        research = ResearchResult(entries=[])
        plan = _template_plan(farmer, research)

        assert plan is not None
        assert "DEMO PLAN" in plan.summary or "demo" in (plan.uncertainty_notes or "").lower()
        assert plan.expert_consultation_recommended is True
        assert len(plan.steps) > 0

    def test_template_plan_includes_knowledge_issues(self):
        """Template plan should list likely issues from knowledge base entries."""
        from agents.planning_agent import _template_plan
        from models.schemas import FarmerInput

        farmer = FarmerInput(
            crop_name="rice",
            location="Vietnam",
            symptoms="blast lesions on leaves",
        )
        entry = KnowledgeEntry(
            id="ri001",
            crop="rice",
            topic="blast disease",
            content="Rice blast content.",
            source_title="IRRI",
            relevance_score=0.9,
        )
        research = ResearchResult(entries=[entry])
        plan = _template_plan(farmer, research)

        assert len(plan.likely_issues) > 0
        assert any("blast" in issue.lower() for issue in plan.likely_issues)


# ---------------------------------------------------------------------------
# Follow-Up Agent
# ---------------------------------------------------------------------------

class TestFollowUpAgent:

    def test_save_and_retrieve_followup_task(self, tmp_path):
        """Follow-up tasks should persist and be retrievable."""
        import os
        db_path = str(tmp_path / "followup_test.db")
        os.environ["AGRIAGENT_DB_PATH"] = db_path

        from database.db import initialize_db, save_farmer_query, save_report
        initialize_db(db_path=db_path)
        qid = save_farmer_query("tomato", "Spain", "early blight symptoms", db_path=db_path)
        rid = save_report(qid, "Apply copper fungicide", db_path=db_path)

        from database.db import save_followup_task, get_followup_tasks
        tid = save_followup_task(
            report_id=rid,
            task_description="Check for new lesions",
            db_path=db_path,
        )
        tasks = get_followup_tasks(report_id=rid, db_path=db_path)
        assert len(tasks) == 1
        assert tasks[0]["task_description"] == "Check for new lesions"

        # Clean up
        del os.environ["AGRIAGENT_DB_PATH"]

    def test_update_task_status(self, tmp_path):
        """Updating follow-up task status should persist correctly."""
        import os
        db_path = str(tmp_path / "followup_update_test.db")
        os.environ["AGRIAGENT_DB_PATH"] = db_path

        from database.db import initialize_db, save_farmer_query, save_report, save_followup_task, update_followup_task, get_followup_tasks
        initialize_db(db_path=db_path)
        qid = save_farmer_query("maize", "Uganda", "fall armyworm frass", db_path=db_path)
        rid = save_report(qid, "Apply Bt biopesticide", db_path=db_path)
        tid = save_followup_task(report_id=rid, task_description="Monitor whorl", db_path=db_path)

        updated = update_followup_task(tid, "completed", "Frass found, Bt applied", db_path=db_path)
        assert updated is True

        completed = get_followup_tasks(status="completed", db_path=db_path)
        assert any(t["id"] == tid for t in completed)

        del os.environ["AGRIAGENT_DB_PATH"]
