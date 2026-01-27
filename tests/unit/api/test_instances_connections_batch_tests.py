from typing import Any, cast

import pytest

from app.api.v1.namespaces import instances_connections as instances_connections_module


@pytest.mark.unit
def test_execute_batch_tests_marks_instance_failed_when_test_raises(monkeypatch) -> None:
    class DummyInstance:
        def __init__(self, name: str) -> None:
            self.name = name

    class DummyDetailService:
        def get_instance_by_id(self, instance_id: int):
            return DummyInstance(name=f"instance-{instance_id}")

    class DummyConnTestService:
        def test_connection(self, _instance):
            raise RuntimeError("boom")

    log_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def _fake_log_with_context(*args: object, **kwargs: object) -> None:
        log_calls.append((args, dict(kwargs)))

    monkeypatch.setattr(instances_connections_module, "InstanceDetailReadService", lambda: DummyDetailService())
    monkeypatch.setattr(instances_connections_module, "log_with_context", _fake_log_with_context)

    results, success_count, fail_count = instances_connections_module._execute_batch_tests(
        cast(Any, DummyConnTestService()),
        [1],
    )

    assert success_count == 0
    assert fail_count == 1
    assert len(results) == 1
    assert results[0]["instance_id"] == 1
    assert results[0]["success"] is False
    assert results[0]["error_code"] == "BATCH_TEST_FAILED"
    assert log_calls
