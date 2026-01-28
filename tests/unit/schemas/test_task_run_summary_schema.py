import pytest

from app.schemas.task_run_summary import TaskRunSummaryFactory, TaskRunSummaryV1


@pytest.mark.unit
def test_summary_base_has_fixed_top_level_keys() -> None:
    payload = TaskRunSummaryFactory.base(task_key="sync_accounts")
    assert set(payload.keys()) == {"version", "common", "ext"}
    assert payload["version"] == 1
    assert payload["ext"]["type"] == "sync_accounts"


@pytest.mark.unit
def test_summary_validate_task_key_rejects_wrong_ext_type() -> None:
    payload = TaskRunSummaryFactory.base(task_key="sync_accounts")
    payload["ext"]["type"] = "wrong"
    model = TaskRunSummaryV1.model_validate(payload)

    with pytest.raises(ValueError):
        model.validate_task_key("sync_accounts")
