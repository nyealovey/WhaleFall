from __future__ import annotations

import re
from pathlib import Path

import pytest


@pytest.mark.unit
def test_scheduler_modals_must_be_store_driven() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "app/static/js/modules/views/admin/scheduler/modals/scheduler-modals.js"
    content = path.read_text(encoding="utf-8", errors="ignore")

    assert "ensureStore" not in content, "SchedulerModals 不应依赖 ensureStore（必须直接注入 store）"
    assert "getStore" not in content, "SchedulerModals 不应依赖 getStore（必须直接注入 store）"
    assert "store.actions.updateJob" in content, "SchedulerModals 必须通过 store.actions.updateJob 更新任务"


@pytest.mark.unit
def test_scheduler_page_must_inject_store_to_modals_and_remove_migration_fallback() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "app/static/js/modules/views/admin/scheduler/index.js"
    content = path.read_text(encoding="utf-8", errors="ignore")

    assert "初始化 SchedulerService/SchedulerStore 失败" not in content, (
        "SchedulerPage 不应保留迁移期 try/catch 兜底（应 fail fast）"
    )

    pattern = re.compile(
        r"SchedulerModals\.createController\(\{[\s\S]*?\bstore\s*:",
        re.MULTILINE,
    )
    assert pattern.search(content), "SchedulerPage 必须向 SchedulerModals 注入 store"

    assert "getStore" not in content, "SchedulerPage 不应向 SchedulerModals 传 getStore"
    assert "ensureStore" not in content, "SchedulerPage 不应向 SchedulerModals 传 ensureStore"

