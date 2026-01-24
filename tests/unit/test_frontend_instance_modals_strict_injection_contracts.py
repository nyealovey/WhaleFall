from __future__ import annotations

import re
from pathlib import Path

import pytest


@pytest.mark.unit
def test_instance_modals_must_not_construct_service() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "app/static/js/modules/views/instances/modals/instance-modals.js"
    content = path.read_text(encoding="utf-8", errors="ignore")

    assert "new InstanceService" not in content, (
        "instance-modals 不得自行 new InstanceService（必须由 Page Entry 注入 store/actions）"
    )


@pytest.mark.unit
def test_instance_modals_must_not_reload_page_directly() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "app/static/js/modules/views/instances/modals/instance-modals.js"
    content = path.read_text(encoding="utf-8", errors="ignore")

    assert "window.location.reload" not in content, (
        "instance-modals 不应直接 window.location.reload（由 Page Entry 通过 onSaved 决定刷新策略）"
    )


@pytest.mark.unit
def test_instances_list_page_must_inject_store_to_instance_modals() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "app/static/js/modules/views/instances/list.js"
    content = path.read_text(encoding="utf-8", errors="ignore")

    pattern = re.compile(
        r"InstanceModals\.createController\(\{[\s\S]*?\bstore\s*:",
        re.MULTILINE,
    )
    assert pattern.search(content), "InstancesListPage 必须向 instance-modals 注入 store"


@pytest.mark.unit
def test_instances_detail_page_must_inject_store_to_instance_modals() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "app/static/js/modules/views/instances/detail.js"
    content = path.read_text(encoding="utf-8", errors="ignore")

    pattern = re.compile(
        r"InstanceModals\.createController\(\{[\s\S]*?\bstore\s*:",
        re.MULTILINE,
    )
    assert pattern.search(content), "InstanceDetailPage 必须向 instance-modals 注入 store"

