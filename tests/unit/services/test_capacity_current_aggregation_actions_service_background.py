from collections.abc import Callable

import pytest

from app.services.capacity import capacity_current_aggregation_actions_service as module


@pytest.mark.unit
def test_launch_background_aggregation_logs_when_task_raises(monkeypatch) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []

    def _fake_log_with_context(level: str, message: str, **kwargs: object) -> None:
        calls.append((level, message, dict(kwargs)))

    class _DummyThread:
        def __init__(
            self,
            *,
            target: Callable[..., None],
            args: tuple[object, ...],
            name: str,
            daemon: bool,
        ) -> None:
            self._target = target
            self._args = args
            self.name = name
            self.daemon = daemon

        def start(self) -> None:
            self._target(*self._args)

    def _bad_task(**_kwargs: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(module, "log_with_context", _fake_log_with_context)
    monkeypatch.setattr(module.threading, "Thread", _DummyThread)

    thread = module._launch_background_aggregation(
        created_by=1,
        run_id="run-1",
        scope="all",
        task=_bad_task,
    )

    assert thread.name == "capacity_aggregate_current_manual"
    assert calls

    level, message, kwargs = calls[0]
    assert level == "error"
    assert message == "后台统计当前周期失败"
    assert kwargs["module"] == "capacity_aggregations"
    assert kwargs["action"] == "capacity_aggregate_current_background"
    assert kwargs["include_actor"] is False
    assert kwargs["context"] == {"created_by": 1, "run_id": "run-1", "scope": "all"}
    assert kwargs["extra"] == {"error_type": "RuntimeError", "error_message": "boom"}

