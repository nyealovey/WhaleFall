import pytest


@pytest.mark.unit
def test_prepare_background_auto_classify_uses_summary_envelope(monkeypatch) -> None:
    from app.schemas.task_run_summary import TaskRunSummaryV1
    from app.services.account_classification.auto_classify_actions_service import AutoClassifyActionsService
    from app.services.task_runs.task_runs_write_service import TaskRunsWriteService

    captured: dict[str, object] = {}

    def _fake_start_run(
        self: TaskRunsWriteService,
        *,
        task_key: str,
        task_name: str,
        task_category: str,
        trigger_source: str,
        created_by: int | None = None,
        summary_json: dict[str, object] | None = None,
        result_url: str | None = None,
    ) -> str:
        captured["task_key"] = task_key
        captured["summary_json"] = summary_json
        return "run-1"

    monkeypatch.setattr(TaskRunsWriteService, "start_run", _fake_start_run, raising=True)

    service = AutoClassifyActionsService(task=lambda **_: None)
    prepared = service.prepare_background_auto_classify(created_by=1, instance_id=123)
    assert prepared.run_id == "run-1"

    model = TaskRunSummaryV1.model_validate(captured["summary_json"])
    model.validate_task_key("auto_classify_accounts")
    assert model.common.inputs["instance_id"] == 123


@pytest.mark.unit
def test_prepare_background_capacity_aggregate_current_uses_summary_envelope(monkeypatch) -> None:
    from app.schemas.task_run_summary import TaskRunSummaryV1
    from app.services.capacity.capacity_current_aggregation_actions_service import (
        CapacityCurrentAggregationActionsService,
    )
    from app.services.task_runs.task_runs_write_service import TaskRunsWriteService

    captured: dict[str, object] = {}

    def _fake_start_run(
        self: TaskRunsWriteService,
        *,
        task_key: str,
        task_name: str,
        task_category: str,
        trigger_source: str,
        created_by: int | None = None,
        summary_json: dict[str, object] | None = None,
        result_url: str | None = None,
    ) -> str:
        captured["task_key"] = task_key
        captured["summary_json"] = summary_json
        return "run-2"

    monkeypatch.setattr(TaskRunsWriteService, "start_run", _fake_start_run, raising=True)

    service = CapacityCurrentAggregationActionsService(task=lambda **_: None)
    prepared = service.prepare_background_aggregation(created_by=1, scope="All", result_url="/capacity")
    assert prepared.run_id == "run-2"

    model = TaskRunSummaryV1.model_validate(captured["summary_json"])
    model.validate_task_key("capacity_aggregate_current")
    assert model.common.inputs["scope"] == "all"
