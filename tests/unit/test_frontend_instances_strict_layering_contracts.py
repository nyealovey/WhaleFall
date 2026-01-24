from __future__ import annotations

import re
from pathlib import Path

import pytest


@pytest.mark.unit
def test_instances_list_page_must_not_maintain_selected_state() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "app/static/js/modules/views/instances/list.js"
    content = path.read_text(encoding="utf-8", errors="ignore")

    assert "selectedInstanceIds" not in content, (
        "InstancesListPage 不应自维护 selectedInstanceIds（选择状态必须下沉 store）"
    )


@pytest.mark.unit
def test_instances_list_page_restore_must_use_store_action() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "app/static/js/modules/views/instances/list.js"
    content = path.read_text(encoding="utf-8", errors="ignore")

    assert "restoreInstance(" not in content or "instanceStore.actions.restoreInstance" in content, (
        "InstancesListPage 恢复实例必须走 store.actions.restoreInstance（禁止直连 service.restoreInstance）"
    )
    assert "managementService.restoreInstance" not in content, (
        "InstancesListPage 禁止直连 managementService.restoreInstance（必须走 store/actions）"
    )


@pytest.mark.unit
def test_batch_create_instance_modal_must_not_reload_page() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "app/static/js/modules/views/instances/modals/batch-create-modal.js"
    content = path.read_text(encoding="utf-8", errors="ignore")

    assert "location.reload" not in content, (
        "BatchCreateInstanceModal 不应自行 location.reload（由 Page Entry 通过 onSaved 决定刷新策略）"
    )


@pytest.mark.unit
def test_batch_create_instance_modal_must_not_fallback_to_service() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "app/static/js/modules/views/instances/modals/batch-create-modal.js"
    content = path.read_text(encoding="utf-8", errors="ignore")

    assert "service.batchCreateInstances" not in content, (
        "BatchCreateInstanceModal 禁止 fallback 到 service.batchCreateInstances（必须依赖 store/actions）"
    )
    assert "getInstanceStore" not in content, (
        "BatchCreateInstanceModal 不应依赖 getInstanceStore（直接注入 store 即可）"
    )


@pytest.mark.unit
def test_database_table_sizes_modal_must_be_store_driven_and_di_only() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    path = (
        repo_root
        / "app/static/js/modules/views/instances/modals/database-table-sizes-modal.js"
    )
    content = path.read_text(encoding="utf-8", errors="ignore")

    assert "new Service" not in content, (
        "DatabaseTableSizesModal 不得自行 new Service（必须由 Page Entry 注入 store/actions）"
    )
    assert "payload 解析失败" not in content, (
        "DatabaseTableSizesModal 不应吞 JSON.parse 异常并返回空对象（禁止静默 fallback）"
    )
    assert "store.actions.fetchDatabaseTableSizes" in content, (
        "DatabaseTableSizesModal 必须通过 store.actions.fetchDatabaseTableSizes 加载数据"
    )
    assert "store.actions.refreshDatabaseTableSizes" in content, (
        "DatabaseTableSizesModal 必须通过 store.actions.refreshDatabaseTableSizes 刷新数据"
    )


@pytest.mark.unit
def test_instance_detail_page_must_not_call_management_service_directly() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "app/static/js/modules/views/instances/detail.js"
    content = path.read_text(encoding="utf-8", errors="ignore")

    forbidden = [
        "instanceService.syncInstanceAccounts",
        "instanceService.syncInstanceCapacity",
        "instanceService.fetchDatabaseSizes",
        "instanceService.fetchAccountChangeHistory",
    ]
    for token in forbidden:
        assert token not in content, f"InstanceDetailPage 禁止直连 InstanceManagementService: {token}"

    required = [
        "instanceStore.actions.syncInstanceAccounts",
        "instanceStore.actions.syncInstanceCapacity",
        "instanceStore.actions.fetchAccountChangeHistory",
    ]
    for token in required:
        assert token in content, f"InstanceDetailPage 必须通过 store/actions 调用: {token}"


@pytest.mark.unit
def test_instance_statistics_page_must_not_silently_swallow_load_errors() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "app/static/js/modules/views/instances/statistics.js"
    content = path.read_text(encoding="utf-8", errors="ignore")

    silent_catch = re.compile(r"\.catch\(\s*\(\)\s*=>\s*\{\s*\}\s*\)")
    assert not silent_catch.search(content), (
        "InstanceStatisticsPage 禁止 .catch(() => {}) 静默吞异常（必须显式提示/上报）"
    )

