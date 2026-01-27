import pytest

import app.services.scheduler.scheduler_job_write_service as module


@pytest.mark.unit
def test_scheduler_job_write_service_type_checking_guard_sets_job_types_to_object() -> None:
    assert module.Job is object
    assert module.BaseScheduler is object

