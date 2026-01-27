from collections.abc import Callable

import pytest

from app.services.account_classification import auto_classify_actions_service as module


@pytest.mark.unit
def test_launch_background_auto_classify_logs_when_task_raises(monkeypatch) -> None:
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

    thread = module._launch_background_auto_classify(
        created_by=1,
        run_id="run-1",
        instance_id=2,
        task=_bad_task,
    )

    assert thread.name == "auto_classify_accounts_manual"
    assert calls

    level, message, kwargs = calls[0]
    assert level == "error"
    assert message == "后台自动分类失败"
    assert kwargs["module"] == "account_classification"
    assert kwargs["action"] == "auto_classify_accounts_background"
    assert kwargs["include_actor"] is False
    assert kwargs["context"] == {"created_by": 1, "run_id": "run-1", "instance_id": 2}
    assert kwargs["extra"] == {"error_type": "RuntimeError", "error_message": "boom"}
