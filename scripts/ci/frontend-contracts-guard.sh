#!/usr/bin/env bash
# Frontend contracts 门禁：modules 分层/注入/迁移约束（避免页面脚本回退为直连 service 或 legacy token）
#
# 参考：
# - docs/Obsidian/standards/ui/design/javascript-module.md
# - docs/Obsidian/standards/ui/gate/grid.md
# - docs/plans/2026-01-24-frontend-strict-layering-refactor.md

set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  cat <<'EOF'
Usage:
  ./scripts/ci/frontend-contracts-guard.sh

Notes:
  - 该脚本是“迁移完成后的防回归门禁”，不属于 pytest 单元测试。
  - 若页面/模块结构发生重构，请同步更新该脚本与对应 SSOT 文档的“门禁/检查方式”。
EOF
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

PY_BIN="${PY_BIN:-python3}"
if ! command -v "${PY_BIN}" >/dev/null 2>&1; then
  echo "未检测到 python3，无法执行 frontend contracts 门禁检查。" >&2
  exit 1
fi

"${PY_BIN}" - <<'PY'
from __future__ import annotations

import re
import sys
from pathlib import Path


def _read_text(rel_path: str) -> str:
    path = Path(rel_path)
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except FileNotFoundError:
        raise AssertionError(f"文件缺失: {rel_path}") from None


def _assert_contains(text: str, token: str, *, ctx: str) -> None:
    if token not in text:
        raise AssertionError(f"{ctx}: 缺少必要标记: {token}")


def _assert_not_contains(text: str, token: str, *, ctx: str) -> None:
    if token in text:
        raise AssertionError(f"{ctx}: 发现禁止 token: {token}")


def _assert_index_before(text: str, a: str, b: str, *, ctx: str) -> None:
    if a not in text:
        raise AssertionError(f"{ctx}: 未找到: {a}")
    if b not in text:
        raise AssertionError(f"{ctx}: 未找到: {b}")
    if text.index(a) >= text.index(b):
        raise AssertionError(f"{ctx}: 加载顺序错误: `{a}` 必须在 `{b}` 之前")


def _assert_regex(text: str, pattern: re.Pattern[str], *, ctx: str) -> None:
    if not pattern.search(text):
        raise AssertionError(f"{ctx}: 未命中必要 pattern: {pattern.pattern}")


def _scan_lines(paths: list[Path], *, line_predicate) -> list[str]:
    hits: list[str] = []
    for path in paths:
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for lineno, line in enumerate(content.splitlines(), start=1):
            if line_predicate(line):
                hits.append(f"{path}:{lineno}: {line.strip()}")
    return hits


def _iter_files(root: Path, *, suffix_allow: set[str]) -> list[Path]:
    out: list[Path] = []
    for path in root.rglob("*"):
        if path.is_dir():
            continue
        if path.suffix not in suffix_allow:
            continue
        out.append(path)
    return out


def _check_template_load_order() -> None:
    cases = [
        (
            "app/templates/history/account_change_logs/account-change-logs.html",
            "js/modules/stores/account_change_logs_store.js",
            "js/modules/views/history/account-change-logs/account-change-logs.js",
        ),
        (
            "app/templates/accounts/statistics.html",
            "js/modules/stores/accounts_statistics_store.js",
            "js/modules/views/accounts/statistics.js",
        ),
        (
            "app/templates/dashboard/overview.html",
            "js/modules/stores/dashboard_store.js",
            "js/modules/views/dashboard/overview.js",
        ),
        (
            "app/templates/history/logs/logs.html",
            "js/modules/stores/logs_store.js",
            "js/modules/views/history/logs/logs.js",
        ),
        (
            "app/templates/history/sessions/sync-sessions.html",
            "js/modules/stores/task_runs_store.js",
            "js/modules/views/history/sessions/sync-sessions.js",
        ),
    ]

    for template_path, store_js, entry_js in cases:
        content = _read_text(template_path)
        _assert_contains(content, store_js, ctx=template_path)
        _assert_index_before(content, store_js, entry_js, ctx=template_path)

    # Auth list：store 必须在 modals/page 之前
    auth_tpl = "app/templates/auth/list.html"
    content = _read_text(auth_tpl)
    _assert_contains(content, "js/modules/stores/users_store.js", ctx=auth_tpl)
    _assert_index_before(
        content,
        "js/modules/stores/users_store.js",
        "js/modules/views/auth/modals/user-modals.js",
        ctx=auth_tpl,
    )
    _assert_index_before(content, "js/modules/stores/users_store.js", "js/modules/views/auth/list.js", ctx=auth_tpl)

    # Tags index：store 必须在 modals/page 之前
    tags_tpl = "app/templates/tags/index.html"
    content = _read_text(tags_tpl)
    _assert_contains(content, "js/modules/stores/tag_list_store.js", ctx=tags_tpl)
    _assert_index_before(
        content,
        "js/modules/stores/tag_list_store.js",
        "js/modules/views/tags/modals/tag-modals.js",
        ctx=tags_tpl,
    )
    _assert_index_before(content, "js/modules/stores/tag_list_store.js", "js/modules/views/tags/index.js", ctx=tags_tpl)


def _check_entry_scripts_no_direct_service_calls() -> None:
    # History: account change logs
    p = "app/static/js/modules/views/history/account-change-logs/account-change-logs.js"
    content = _read_text(p)
    _assert_contains(content, "createAccountChangeLogsStore", ctx=p)
    for token in ("fetchStats(", "fetchDetail(", "getGridUrl("):
        _assert_not_contains(content, token, ctx=p)

    # Accounts statistics
    p = "app/static/js/modules/views/accounts/statistics.js"
    content = _read_text(p)
    _assert_contains(content, "createAccountsStatisticsStore", ctx=p)
    _assert_not_contains(content, "fetchStatistics(", ctx=p)

    # Auth list page
    p = "app/static/js/modules/views/auth/list.js"
    content = _read_text(p)
    _assert_contains(content, "createUsersStore", ctx=p)
    _assert_not_contains(content, "getGridUrl(", ctx=p)

    # Auth user modals
    p = "app/static/js/modules/views/auth/modals/user-modals.js"
    content = _read_text(p)
    for token in ("createUsersStore", "new UserService", "userService."):
        _assert_not_contains(content, token, ctx=p)

    # Dashboard overview
    p = "app/static/js/modules/views/dashboard/overview.js"
    content = _read_text(p)
    _assert_contains(content, "createDashboardStore", ctx=p)
    _assert_not_contains(content, "fetchCharts(", ctx=p)

    # History logs page
    p = "app/static/js/modules/views/history/logs/logs.js"
    content = _read_text(p)
    _assert_contains(content, "createLogsStore", ctx=p)
    for token in ("fetchStats(", "fetchLogDetail(", "getGridUrl("):
        _assert_not_contains(content, token, ctx=p)

    # Sync sessions page
    p = "app/static/js/modules/views/history/sessions/sync-sessions.js"
    content = _read_text(p)
    _assert_contains(content, "createTaskRunsStore", ctx=p)
    for token in ("getGridUrl(", ".detail(", ".cancel("):
        _assert_not_contains(content, token, ctx=p)

    # Tags index page + tag modals
    p = "app/static/js/modules/views/tags/index.js"
    content = _read_text(p)
    _assert_contains(content, "createTagListStore", ctx=p)
    for token in ("getGridUrl(", "deleteTag("):
        _assert_not_contains(content, token, ctx=p)

    p = "app/static/js/modules/views/tags/modals/tag-modals.js"
    content = _read_text(p)
    for token in ("createTagListStore", "new TagManagementService", "tagService."):
        _assert_not_contains(content, token, ctx=p)


def _check_credentials_strict_layering() -> None:
    p = "app/static/js/modules/views/credentials/modals/credential-modals.js"
    content = _read_text(p)
    _assert_not_contains(content, "new CredentialsService", ctx=p)

    p = "app/static/js/modules/views/credentials/list.js"
    content = _read_text(p)
    _assert_not_contains(content, "初始化 CredentialsService/CredentialsStore 失败", ctx=p)

    pattern = re.compile(r"CredentialModals\.createController\(\{[\s\S]*?\bstore\s*:", re.MULTILINE)
    _assert_regex(content, pattern, ctx=p)


def _check_instances_strict_layering() -> None:
    # instance-modals
    p = "app/static/js/modules/views/instances/modals/instance-modals.js"
    content = _read_text(p)
    _assert_not_contains(content, "new InstanceService", ctx=p)
    _assert_not_contains(content, "window.location.reload", ctx=p)

    # list/detail inject store to InstanceModals
    pattern = re.compile(r"InstanceModals\.createController\(\{[\s\S]*?\bstore\s*:", re.MULTILINE)
    for p in ("app/static/js/modules/views/instances/list.js", "app/static/js/modules/views/instances/detail.js"):
        content = _read_text(p)
        _assert_regex(content, pattern, ctx=p)

    # list page selection state
    p = "app/static/js/modules/views/instances/list.js"
    content = _read_text(p)
    _assert_not_contains(content, "selectedInstanceIds", ctx=p)
    if "restoreInstance(" in content:
        _assert_contains(content, "instanceStore.actions.restoreInstance", ctx=p)
    _assert_not_contains(content, "managementService.restoreInstance", ctx=p)

    # batch-create modal
    p = "app/static/js/modules/views/instances/modals/batch-create-modal.js"
    content = _read_text(p)
    _assert_not_contains(content, "location.reload", ctx=p)
    _assert_not_contains(content, "service.batchCreateInstances", ctx=p)
    _assert_not_contains(content, "getInstanceStore", ctx=p)

    # database-table-sizes modal
    p = "app/static/js/modules/views/instances/modals/database-table-sizes-modal.js"
    content = _read_text(p)
    _assert_not_contains(content, "new Service", ctx=p)
    _assert_not_contains(content, "payload 解析失败", ctx=p)
    _assert_contains(content, "store.actions.fetchDatabaseTableSizes", ctx=p)
    _assert_contains(content, "store.actions.refreshDatabaseTableSizes", ctx=p)

    # instance detail: forbid direct service methods; require store.actions calls
    p = "app/static/js/modules/views/instances/detail.js"
    content = _read_text(p)
    forbidden = [
        "instanceService.syncInstanceAccounts",
        "instanceService.syncInstanceCapacity",
        "instanceService.fetchDatabaseSizes",
        "instanceService.fetchAccountChangeHistory",
    ]
    for token in forbidden:
        _assert_not_contains(content, token, ctx=p)
    required = [
        "instanceStore.actions.syncInstanceAccounts",
        "instanceStore.actions.syncInstanceCapacity",
        "instanceStore.actions.fetchAccountChangeHistory",
    ]
    for token in required:
        _assert_contains(content, token, ctx=p)


def _check_scheduler_strict_layering() -> None:
    p = "app/static/js/modules/views/admin/scheduler/modals/scheduler-modals.js"
    content = _read_text(p)
    for token in ("ensureStore", "getStore"):
        _assert_not_contains(content, token, ctx=p)
    _assert_contains(content, "store.actions.updateJob", ctx=p)

    p = "app/static/js/modules/views/admin/scheduler/index.js"
    content = _read_text(p)
    _assert_not_contains(content, "初始化 SchedulerService/SchedulerStore 失败", ctx=p)
    pattern = re.compile(r"SchedulerModals\.createController\(\{[\s\S]*?\bstore\s*:", re.MULTILINE)
    _assert_regex(content, pattern, ctx=p)
    for token in ("getStore", "ensureStore"):
        _assert_not_contains(content, token, ctx=p)


def _check_permissions_viewer_injection_contract() -> None:
    p = "app/static/js/modules/views/components/permissions/permission-viewer.js"
    content = _read_text(p)
    _assert_not_contains(content, "new PermissionService", ctx=p)

    p = "app/static/js/modules/views/accounts/ledgers.js"
    content = _read_text(p)
    _assert_contains(content, "configurePermissionViewer", ctx=p)
    _assert_not_contains(content, "global.viewAccountPermissions", ctx=p)

    p = "app/static/js/modules/views/instances/detail.js"
    content = _read_text(p)
    _assert_contains(content, "configurePermissionViewer", ctx=p)
    _assert_not_contains(content, "window.viewAccountPermissions", ctx=p)


def _check_capacity_data_source_injection_contract() -> None:
    p = "app/static/js/modules/views/components/charts/data-source.js"
    content = _read_text(p)
    _assert_not_contains(content, "new CapacityStatsService", ctx=p)

    p = "app/static/js/modules/views/components/charts/manager.js"
    content = _read_text(p)
    _assert_not_contains(content, "CapacityStatsDataSource", ctx=p)

    pattern = re.compile(r"new\s+window\.CapacityStats\.Manager\(\{[\s\S]*?\bdataSource\s*:", re.MULTILINE)
    for p in ("app/static/js/modules/views/capacity/databases.js", "app/static/js/modules/views/capacity/instances.js"):
        content = _read_text(p)
        _assert_regex(content, pattern, ctx=p)


def _check_tag_selector_injection_contract() -> None:
    p = "app/static/js/modules/views/components/tags/tag-selector-controller.js"
    content = _read_text(p)
    for token in ("new TagManagementService", "createTagManagementStore"):
        _assert_not_contains(content, token, ctx=p)

    pattern = re.compile(r"TagSelectorHelper\.setupForForm\(\{[\s\S]*?\bstore\s*:", re.MULTILINE)
    for p in (
        "app/static/js/modules/views/accounts/ledgers.js",
        "app/static/js/modules/views/databases/ledgers.js",
        "app/static/js/modules/views/instances/list.js",
    ):
        content = _read_text(p)
        _assert_regex(content, pattern, ctx=p)


def _check_partitions_injection_contract() -> None:
    p = "app/static/js/modules/views/admin/partitions/partition-list.js"
    content = _read_text(p)
    for token in ("new PartitionService", "PartitionService"):
        _assert_not_contains(content, token, ctx=p)
    _assert_contains(content, "gridUrl", ctx=p)

    p = "app/static/js/modules/views/admin/partitions/index.js"
    content = _read_text(p)
    _assert_contains(content, "PartitionsListGrid.mount", ctx=p)
    _assert_contains(content, "gridUrl:", ctx=p)

    p = "app/static/js/modules/views/admin/partitions/charts/partitions-chart.js"
    content = _read_text(p)
    for token in ("createPartitionStore", "PartitionService", "fetchCoreMetrics"):
        _assert_not_contains(content, token, ctx=p)


def _check_metric_card_component_contract() -> None:
    template_path = Path("app/templates/components/ui/metric_card.html")
    css_path = Path("app/static/css/components/metric-card.css")
    macros_path = Path("app/templates/components/ui/macros.html")
    base_path = Path("app/templates/base.html")

    if not template_path.exists():
        raise AssertionError("MetricCard 模板缺失: app/templates/components/ui/metric_card.html")
    if not css_path.exists():
        raise AssertionError("MetricCard CSS 缺失: app/static/css/components/metric-card.css")

    base_content = base_path.read_text(encoding="utf-8", errors="ignore")
    _assert_contains(base_content, "css/components/metric-card.css", ctx="app/templates/base.html")

    macros_content = macros_path.read_text(encoding="utf-8", errors="ignore")
    _assert_contains(macros_content, "metric_card", ctx="app/templates/components/ui/macros.html")

    template_content = template_path.read_text(encoding="utf-8", errors="ignore")
    css_content = css_path.read_text(encoding="utf-8", errors="ignore")
    _assert_contains(template_content, "wf-metric-card", ctx=str(template_path))
    _assert_contains(css_content, ".wf-metric-card", ctx=str(css_path))


def _check_metric_card_migration_contract() -> None:
    must_use_metric_card_templates = [
        "app/templates/dashboard/overview.html",
        "app/templates/capacity/databases.html",
        "app/templates/capacity/instances.html",
        "app/templates/tags/index.html",
        "app/templates/history/logs/logs.html",
        "app/templates/accounts/statistics.html",
        "app/templates/instances/statistics.html",
        "app/templates/admin/partitions/index.html",
        "app/templates/history/account_change_logs/account-change-logs.html",
    ]

    forbidden_tokens_by_template: dict[str, list[str]] = {
        "app/templates/dashboard/overview.html": ["dashboard-stat-card"],
        "app/templates/tags/index.html": ["tags-stat-card"],
        "app/templates/history/logs/logs.html": ["log-stats-card"],
        "app/templates/accounts/statistics.html": ["account-stat-card"],
        "app/templates/instances/statistics.html": ["instance-stat-card"],
        "app/templates/admin/partitions/index.html": ["partition-stat-card"],
        "app/templates/history/account_change_logs/account-change-logs.html": ["change-log-stats-card"],
    }

    for rel_path in must_use_metric_card_templates:
        content = _read_text(rel_path)
        _assert_contains(content, "metric_card(", ctx=rel_path)
        _assert_not_contains(content, "stats_card", ctx=rel_path)
        for token in forbidden_tokens_by_template.get(rel_path, []):
            _assert_not_contains(content, token, ctx=rel_path)

    must_not_use_metric_card_templates: dict[str, dict[str, list[str]]] = {
        "app/templates/history/sessions/sync-sessions.html": {
            "required": ['id="taskRunsTotalCount"'],
            "forbidden": ["session-stats-card"],
        },
        "app/templates/admin/scheduler/index.html": {
            "required": ['id="activeJobsCount"', 'id="pausedJobsCount"'],
            "forbidden": ["scheduler-stat-card"],
        },
    }

    for rel_path, rules in must_not_use_metric_card_templates.items():
        content = _read_text(rel_path)
        _assert_not_contains(content, "metric_card(", ctx=rel_path)
        for marker in rules["required"]:
            _assert_contains(content, marker, ctx=rel_path)
        for token in rules["forbidden"]:
            _assert_not_contains(content, token, ctx=rel_path)

    forbidden_css_tokens = [
        "account-stat-card",
        "instance-stat-card",
        "partition-stat-card",
        "change-log-stats-card",
    ]
    css_targets = [
        "app/static/css/pages/accounts/statistics.css",
        "app/static/css/pages/instances/statistics.css",
        "app/static/css/pages/admin/partitions.css",
        "app/static/css/pages/history/account-change-logs.css",
    ]
    for rel_path in css_targets:
        content = _read_text(rel_path)
        for token in forbidden_css_tokens:
            _assert_not_contains(content, token, ctx=rel_path)

    js_inventory_targets = [
        "app/static/js/modules/views/accounts/statistics.js",
        "app/static/js/modules/views/instances/statistics.js",
        "app/static/js/modules/views/admin/partitions/index.js",
    ]
    for rel_path in js_inventory_targets:
        content = _read_text(rel_path)
        for selector in ("data-stat-value", '[data-stat="'):
            _assert_not_contains(content, selector, ctx=rel_path)
        _assert_contains(content, "data-stat-key", ctx=rel_path)

    tags_js = "app/static/js/modules/views/tags/index.js"
    content = _read_text(tags_js)
    _assert_not_contains(content, ".tags-stat-card__value", ctx=tags_js)
    _assert_contains(content, "metric-value", ctx=tags_js)


def _check_no_legacy_stat_card_classes() -> None:
    forbidden_patterns = [
        re.compile(r"(?<![\\w-])dashboard-stat-card(?![\\w-])"),
        re.compile(r"(?<![\\w-])tags-stat-card(?![\\w-])"),
        re.compile(r"(?<![\\w-])log-stats-card(?![\\w-])"),
        re.compile(r"(?<![\\w-])session-stats-card(?![\\w-])"),
        re.compile(r"(?<![\\w-])scheduler-stat-card(?![\\w-])"),
    ]

    matches: list[str] = []
    for root in (Path("app/templates"), Path("app/static/css/pages")):
        for path in _iter_files(root, suffix_allow={".html", ".css"}):
            content = path.read_text(encoding="utf-8", errors="ignore")
            for pattern in forbidden_patterns:
                if pattern.search(content):
                    matches.append(f"{path}: matches {pattern.pattern}")

    if matches:
        raise AssertionError("发现指标卡私有体系残留:\n" + "\n".join(matches[:80]))

    base_html = Path("app/templates/base.html").read_text(encoding="utf-8", errors="ignore")
    _assert_not_contains(base_html, "css/components/stats-card.css", ctx="app/templates/base.html")

    if Path("app/templates/components/ui/stats_card.html").exists():
        raise AssertionError("stats_card.html 应被移除: app/templates/components/ui/stats_card.html")
    if Path("app/static/css/components/stats-card.css").exists():
        raise AssertionError("stats-card.css 应被移除: app/static/css/components/stats-card.css")

    macros = Path("app/templates/components/ui/macros.html").read_text(encoding="utf-8", errors="ignore")
    _assert_not_contains(macros, "macro stats_card", ctx="app/templates/components/ui/macros.html")


def _check_no_legacy_api_paths() -> None:
    legacy_api = re.compile(r"/api(?!/v1)(?:/|$)")
    targets = [
        Path("app/static/js"),
        Path("app/templates"),
    ]

    offenders: list[str] = []
    for root in targets:
        for path in _iter_files(root, suffix_allow={".js", ".html"}):
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for lineno, line in enumerate(content.splitlines(), start=1):
                if legacy_api.search(line):
                    offenders.append(f"{path}:{lineno}: {line.strip()}")

    if offenders:
        raise AssertionError("发现旧版 API 路径引用(将导致 410):\n" + "\n".join(offenders[:80]))


def _check_views_no_window_httpu() -> None:
    views_root = Path("app/static/js/modules/views")
    if not views_root.exists():
        return

    pattern = re.compile(r"\bwindow\.httpU\b|\bhttpU\.")
    offenders: list[str] = []
    for path in sorted(views_root.rglob("*.js")):
        content = path.read_text(encoding="utf-8", errors="ignore")
        for lineno, line in enumerate(content.splitlines(), start=1):
            if pattern.search(line):
                offenders.append(f"{path}:{lineno}: {line.strip()}")

    if offenders:
        raise AssertionError("views 层禁止直接访问 httpU:\n" + "\n".join(offenders[:80]))


def _check_views_no_silent_catch() -> None:
    views_root = Path("app/static/js/modules/views")
    if not views_root.exists():
        return

    silent_catch = re.compile(r"\.catch\(\s*\(\)\s*=>\s*\{\s*\}\s*\)")
    offenders: list[str] = []
    for path in sorted(views_root.rglob("*.js")):
        content = path.read_text(encoding="utf-8", errors="ignore")
        if silent_catch.search(content):
            offenders.append(str(path))

    if offenders:
        raise AssertionError("views 禁止使用 `.catch(() => {})` 静默吞异常:\n" + "\n".join(offenders[:80]))


def _run_all_checks() -> list[str]:
    checks = [
        _check_template_load_order,
        _check_entry_scripts_no_direct_service_calls,
        _check_credentials_strict_layering,
        _check_instances_strict_layering,
        _check_scheduler_strict_layering,
        _check_permissions_viewer_injection_contract,
        _check_capacity_data_source_injection_contract,
        _check_tag_selector_injection_contract,
        _check_partitions_injection_contract,
        _check_metric_card_component_contract,
        _check_metric_card_migration_contract,
        _check_no_legacy_stat_card_classes,
        _check_no_legacy_api_paths,
        _check_views_no_window_httpu,
        _check_views_no_silent_catch,
    ]

    failures: list[str] = []
    for check in checks:
        try:
            check()
        except AssertionError as exc:
            failures.append(f"[{check.__name__}] {exc}")
    return failures


def main() -> int:
    failures = _run_all_checks()

    if failures:
        sys.stderr.write("Frontend contracts 门禁失败：\n\n")
        sys.stderr.write("\n\n".join(failures) + "\n")
        return 1

    sys.stdout.write("✅ frontend contracts 门禁通过。\n")
    return 0


raise SystemExit(main())
PY
