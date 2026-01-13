"""scheduler_tasks.yaml 配置读取入口的 schema 门禁测试."""

from __future__ import annotations

import pytest

import app.scheduler as scheduler


@pytest.mark.unit
def test_read_default_task_configs_validates_and_canonicalizes(tmp_path, monkeypatch) -> None:
    """读取入口应完成一次性校验/规范化，输出 typed config."""
    config_path = tmp_path / "scheduler_tasks.yaml"
    config_path.write_text(
        "\n".join(
            [
                "default_tasks:",
                "  - id: '  sync_accounts  '",
                "    name: '  账户同步  '",
                "    function: ' sync_accounts '",
                "    trigger_type: ' cron '",
                "    trigger_params: {}",
                "    enabled: true",
            ],
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(scheduler, "TASK_CONFIG_PATH", config_path)

    tasks = scheduler._read_default_task_configs()

    assert len(tasks) == 1
    assert tasks[0].id == "sync_accounts"
    assert tasks[0].name == "账户同步"
    assert tasks[0].function == "sync_accounts"
    assert tasks[0].trigger_type == "cron"
    assert tasks[0].trigger_params == {}
    assert tasks[0].enabled is True


@pytest.mark.unit
def test_read_default_task_configs_raises_value_error_when_schema_invalid(tmp_path, monkeypatch) -> None:
    """当缺少必填字段时应抛出 ValueError，避免 silent fallback."""
    config_path = tmp_path / "scheduler_tasks.yaml"
    config_path.write_text(
        "\n".join(
            [
                "default_tasks:",
                "  - id: sync_accounts",
                "    name: 账户同步",
            ],
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(scheduler, "TASK_CONFIG_PATH", config_path)

    with pytest.raises(ValueError):
        scheduler._read_default_task_configs()

