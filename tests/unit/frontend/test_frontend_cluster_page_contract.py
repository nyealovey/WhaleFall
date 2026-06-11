"""cluster 页面前端契约测试."""

import re
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[3]


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


@pytest.mark.unit
def test_base_navigation_contains_cluster_entry() -> None:
    content = _read_text("app/templates/base.html")

    assert "url_for('cluster.index')" in content
    assert ">群集管理<" in content


@pytest.mark.unit
def test_cluster_template_contains_management_surface() -> None:
    content = _read_text("app/templates/cluster/list.html")

    required_fragments = (
        "{% block title %}群集管理 - 鲸落{% endblock %}",
        "群集管理",
        "cluster-page-root",
        "cluster-filter-form",
        "cluster-db-type-switcher",
        "data-db-type-btn",
        'data-cluster-db-type="sqlserver"',
        'data-cluster-db-type="mysql"',
        "segmented-control cluster-db-type-switcher",
        "btn btn-segment active",
        "btn btn-segment",
        "sqlserver-clusters-grid",
        "mysql-clusters-grid",
        "clusterManagementModal",
        "mysqlClusterManagementModal",
        "agAccountsDashboardModal",
        "mysqlTopologyDashboardModal",
        "cluster-basic-tab",
        "cluster-instances-tab",
        "cluster-ag-tab",
        "clusterInstanceSelect",
        "clusterAgTableBody",
        "agAccountsDashboardTableBody",
        "mysqlTopologyDashboardInstances",
        "sqlserver_clusters_service.js",
        "sqlserver_clusters_store.js",
        "views/cluster/list.js",
    )
    for fragment in required_fragments:
        assert fragment in content


@pytest.mark.unit
def test_cluster_instance_options_show_bound_cluster_without_disabling_selection() -> None:
    content = _read_text("app/templates/cluster/list.html")
    css = _read_text("app/static/css/pages/cluster/list.css")

    assert "bound_cluster_name" in content
    assert "已绑定：" in content
    assert "cluster-instance-option--bound" in content
    assert "data-bound-cluster-name" in content
    assert "cluster-instance-option--bound" in css
    option_match = re.search(
        r"<option value=\"\{\{ instance.id \}\}\"(?P<body>.*?)</option>",
        content,
        re.S,
    )
    assert option_match is not None
    assert "disabled" not in option_match.group("body")


@pytest.mark.unit
def test_cluster_js_service_uses_sqlserver_cluster_api_path() -> None:
    content = _read_text("app/static/js/modules/services/sqlserver_clusters_service.js")

    assert 'const BASE_PATH = "/api/v1/sqlserver-clusters";' in content
    assert "replaceInstances" in content
    assert "createAvailabilityGroup" in content
    assert "updateAvailabilityGroup" in content


@pytest.mark.unit
def test_cluster_js_service_uses_mysql_cluster_api_path() -> None:
    content = _read_text("app/static/js/modules/services/mysql_clusters_service.js")

    assert 'const BASE_PATH = "/api/v1/mysql-clusters";' in content
    assert "replaceInstances" in content
    assert "syncTopology" in content


@pytest.mark.unit
def test_cluster_grid_status_formatter_returns_grid_html() -> None:
    content = _read_text("app/static/js/modules/views/cluster/list.js")

    assert "formatter: (value) => gridHtml(renderStatus(value))" in content


@pytest.mark.unit
def test_sqlserver_cluster_row_actions_keep_only_editor_and_dashboards() -> None:
    content = _read_text("app/static/js/modules/views/cluster/list.js")

    function_body = re.search(
        r"function buildColumns\(\) \{(?P<body>.*?)\n  function buildMySQLColumns",
        content,
        re.S,
    )

    assert function_body is not None
    body = function_body.group("body")
    assert 'data-action="edit-cluster"' in body
    assert 'data-action="open-ag-accounts-dashboard"' in body
    assert 'data-action="open-ag-dashboard"' in body
    assert 'data-action="sync-ag-accounts"' not in body
    assert 'data-action="open-ag-accounts"' not in body
    assert 'data-action="sync-sqlserver-status-row"' not in body


@pytest.mark.unit
def test_mysql_cluster_grid_contains_topology_status_without_lag_column() -> None:
    content = _read_text("app/static/js/modules/views/cluster/list.js")

    assert 'name: "主从状态"' in content
    assert 'name: "最大延迟"' not in content
    assert "renderMySQLTopologySummary(meta)" in content
    assert "item.max_replica_lag_seconds" in content
    assert 'data-action="open-mysql-topology-dashboard"' in content
    assert 'data-action="sync-mysql-topology-row"' not in content


@pytest.mark.unit
def test_mysql_cluster_topology_summary_uses_semantic_status_text() -> None:
    content = _read_text("app/static/js/modules/views/cluster/list.js")
    function_body = re.search(
        r"function renderMySQLTopologySummary\(cluster\) \{(?P<body>.*?)\n  function renderMySQLLagSummary",
        content,
        re.S,
    )

    assert "function renderMySQLTopologySummary(cluster)" in content
    assert function_body is not None
    body = function_body.group("body")
    assert ">正常<" in content
    assert "异常 ${abnormal}" in content
    assert "检测失败" in content
    assert "未检测" in content
    assert "异常数" not in body


@pytest.mark.unit
def test_mysql_topology_dashboard_renders_vertical_instance_status_cards() -> None:
    template = _read_text("app/templates/cluster/list.html")
    view = _read_text("app/static/js/modules/views/cluster/list.js")
    css = _read_text("app/static/css/pages/cluster/list.css")

    assert "mysqlTopologyDashboardInstances" in template
    assert "mysql-topology-instance-list" in template
    assert "mysql-topology-instance-card" in view
    assert "mysql-topology-field-row" in view
    assert "renderMySQLTopologyDashboardCards" in view
    assert "renderMySQLTopologyDashboardTable" not in view
    assert "mysqlTopologyDashboardTableBody" not in template
    assert "mysql-topology-dashboard-table" not in template
    assert "mysql-topology-dashboard-table" not in css


@pytest.mark.unit
def test_ag_accounts_dashboard_embeds_current_ag_account_list_without_ledger_jump() -> None:
    template = _read_text("app/templates/cluster/list.html")
    view = _read_text("app/static/js/modules/views/cluster/list.js")

    assert 'data-action="open-ag-accounts-ledger-dashboard"' not in template
    assert "openAgAccountsLedgerForCurrentDashboard" not in view
    assert "账户列表" in template
    assert "采集配置" not in template
    assert "agAccountsDashboardTableBody" in template
    assert "renderAgAccountsLedgerRows" in view
    assert "loadAgAccountsLedger" in view
    assert "owner_id" in view
    assert "renderAccountCredentialSelect(item, currentAgAccountsContext" not in view
    assert "renderCollectionToggle(item, currentAgAccountsContext" not in view


@pytest.mark.unit
def test_sqlserver_ag_views_show_missing_listener_instead_of_empty_ag() -> None:
    view = _read_text("app/static/js/modules/views/cluster/list.js")

    assert "未配置侦听器" in view
    assert "renderAgListenerSummary(item)" in view
    assert "renderAgListenerSummary(ag)" in view
    assert "renderAgListenerSummary(summary)" in view
    assert '[item.listener_name, item.listener_host].filter(Boolean).join(" / ") || "-"' not in view
    assert "[summary.listener_host, summary.listener_port].filter(Boolean).join" not in view


@pytest.mark.unit
def test_cluster_button_loading_does_not_replace_content_with_syncing_text() -> None:
    view = _read_text("app/static/js/modules/views/cluster/list.js")
    function_body = re.search(
        r"function setButtonLoading\(button, loading\) \{(?P<body>.*?)\n  function parseJsonDataset",
        view,
        re.S,
    )

    assert function_body is not None
    body = function_body.group("body")
    assert "aria-busy" in body
    assert "is-loading" in body
    assert "innerHTML" not in body
    assert "同步中" not in body
