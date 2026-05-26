"""SQL Server cluster AG 自动同步前端契约测试."""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


def test_cluster_ag_tab_exposes_sync_action() -> None:
    content = _read_text("app/templates/cluster/list.html")

    required_fragments = (
        'data-action="sync-ag"',
        "同步 AG 信息",
        "使用已绑定实例凭据读取 AG/listener 信息。",
        "clusterDomainNameInput",
        "群集域名",
        "连接地址",
        "数据库同步状态",
        "异常数",
        'data-action="sync-sqlserver-status"',
    )
    for fragment in required_fragments:
        assert fragment in content

    forbidden_fragments = (
        "clusterAgNameInput",
        "clusterAgListenerNameInput",
        "clusterAgHostInput",
        "clusterAgPortInput",
        "clusterAgDatabaseInput",
        "clusterAgContainedInput",
        "clusterAgEnabledInput",
        "clusterAgCredentialInput",
        'data-action="save-ag-draft"',
        "保存 AG",
    )
    for fragment in forbidden_fragments:
        assert fragment not in content


def test_cluster_frontend_calls_sync_ag_endpoint_from_ag_tab() -> None:
    service_content = _read_text("app/static/js/modules/services/sqlserver_clusters_service.js")
    store_content = _read_text("app/static/js/modules/stores/sqlserver_clusters_store.js")
    view_content = _read_text("app/static/js/modules/views/cluster/list.js")

    assert "syncAvailabilityGroups(clusterId, payload)" in service_content
    assert "`${BASE_PATH}/${clusterId}/availability-groups/actions/sync`" in service_content

    assert '"syncAvailabilityGroups",' in store_content
    assert "syncAvailabilityGroups(clusterId, payload)" in store_content

    required_view_fragments = (
        '[data-action="sync-ag"]',
        "syncAvailabilityGroups(clusterId, {})",
        "AG 信息同步完成",
        "store.actions.load(clusterId)",
        'data-action="update-ag-account-credential"',
        'data-action="toggle-ag-collection"',
        "account_credential_id",
        "非 contained AG 不允许启用采集",
        "domain_name",
        "clusterDomainNameInput",
        "connection_endpoint",
    )
    for fragment in required_view_fragments:
        assert fragment in view_content

    forbidden_view_fragments = (
        "saveAgDraft",
        "buildAgPayload",
        "populateAgForm",
        "disableAg",
        "findAg",
        "pendingAgDrafts",
        "clusterAgContainedInput",
        "clusterAgDatabaseInput",
        "connection_database:",
        "请选择 AG 凭据后同步",
        "edit-ag",
        "disable-ag",
    )
    for fragment in forbidden_view_fragments:
        assert fragment not in view_content


def test_cluster_list_exposes_ag_account_sync_and_account_ledger_actions() -> None:
    template_content = _read_text("app/templates/cluster/list.html")
    service_content = _read_text("app/static/js/modules/services/sqlserver_clusters_service.js")
    store_content = _read_text("app/static/js/modules/stores/sqlserver_clusters_store.js")
    view_content = _read_text("app/static/js/modules/views/cluster/list.js")
    accounts_view_content = _read_text("app/static/js/modules/views/accounts/ledgers.js")

    assert "syncAgAccounts(clusterId)" in service_content
    assert "syncStatus(clusterId)" in service_content
    assert "`${BASE_PATH}/${clusterId}/actions/sync-status`" in service_content
    assert "`${BASE_PATH}/${clusterId}/availability-groups/actions/sync-accounts`" in service_content
    assert '"syncAgAccounts",' in store_content
    assert "syncAgAccounts(clusterId)" in store_content

    required_view_fragments = (
        'data-action="open-ag-accounts-dashboard"',
        'title="AG账户"',
        'aria-label="AG账户"',
        "btn btn-outline-secondary btn-sm btn-icon",
        'data-action="sync-ag-accounts-dashboard"',
        "syncAgAccounts(clusterId)",
        "loadAgAccountsLedger",
        'owner_type: "sqlserver_ag"',
        "owner_id: agId",
    )
    for fragment in required_view_fragments:
        assert fragment in view_content

    assert "owner_type" in accounts_view_content
    assert "同步AG账户</button>" not in view_content
    assert "账户列表</button>" not in view_content
    assert 'data-action="sync-ag-accounts"' not in template_content
    assert 'data-action="open-ag-accounts-ledger-dashboard"' not in template_content


def test_sqlserver_cluster_list_renders_database_status_semantics() -> None:
    view_content = _read_text("app/static/js/modules/views/cluster/list.js")
    template_content = _read_text("app/templates/cluster/list.html")

    required_view_fragments = (
        "renderSQLServerDatabaseStatusSummary(meta)",
        "last_status_sync_status",
        "last_status_sync_error",
        "未检测",
        "检测失败",
        "异常 ${abnormal}",
        "正常",
        'data-action="open-ag-dashboard"',
    )
    for fragment in required_view_fragments:
        assert fragment in view_content

    assert "异常数 ${abnormal} / 副本 ${replicas}" not in view_content
    assert 'href="/cluster/sqlserver-status"' not in template_content
    assert "/cluster/sqlserver-status" not in view_content


def test_sqlserver_cluster_ag_status_dashboard_modal_contract() -> None:
    template_content = _read_text("app/templates/cluster/list.html")
    view_content = _read_text("app/static/js/modules/views/cluster/list.js")

    required_template_fragments = (
        "agStatusDashboardModal",
        "agStatusDashboardTitle",
        "agStatusDashboardTabs",
        "agStatusReplicaTableBody",
        "agStatusDatabaseGroups",
        'data-action="sync-ag-dashboard"',
        'data-action="switch-ag-dashboard"',
        "可用性副本",
        "数据库状态",
        "AG 状态",
        "群集状态",
        "群集类型",
    )
    for fragment in required_template_fragments:
        assert fragment in template_content

    required_view_fragments = (
        "open-ag-dashboard",
        "loadAgDashboard",
        "renderAgDashboard",
        "renderAgDashboardTabs",
        "renderAgReplicaRows",
        "renderAgDatabaseGroups",
        "getAvailabilityGroupDashboard",
        "switch-ag-dashboard",
        "sync-ag-dashboard",
    )
    for fragment in required_view_fragments:
        assert fragment in view_content


def test_sqlserver_ag_views_show_missing_listener_label() -> None:
    view_content = _read_text("app/static/js/modules/views/cluster/list.js")

    assert "未配置侦听器" in view_content
    assert "renderAgListenerSummary(item)" in view_content
    assert "renderAgListenerSummary(ag)" in view_content
    assert "renderAgListenerSummary(summary)" in view_content
    assert '[item.listener_name, item.listener_host].filter(Boolean).join(" / ") || "-"' not in view_content
    assert "[summary.listener_host, summary.listener_port].filter(Boolean).join" not in view_content


def test_cluster_instance_options_show_bound_cluster_without_disabling_selection() -> None:
    template_content = _read_text("app/templates/cluster/list.html")
    css_content = _read_text("app/static/css/pages/cluster/list.css")

    assert "bound_cluster_name" in template_content
    assert "已绑定：" in template_content
    assert "cluster-instance-option--bound" in template_content
    assert "data-bound-cluster-name" in template_content
    assert "cluster-instance-option--bound" in css_content
    assert "disabled" not in template_content.split("cluster-instance-option--bound", 1)[0].rsplit("<option", 1)[-1]


def test_mysql_cluster_topology_modal_displays_failure_reason() -> None:
    template_content = _read_text("app/templates/cluster/list.html")
    view_content = _read_text("app/static/js/modules/views/cluster/list.js")
    css_content = _read_text("app/static/css/pages/cluster/list.css")

    assert "mysqlTopologyDashboardInstances" in template_content
    assert "mysql-topology-instance-card" in view_content
    assert "Last_IO_Error / Last_SQL_Error" in view_content
    assert "item.last_error" in view_content
    assert "mysql-topology-field-row" in view_content
    assert "mysql-topology-field-row" in css_content


def test_run_center_session_detail_labels_ag_cluster_items() -> None:
    content = _read_text("app/static/js/modules/views/history/sessions/session-detail.js")

    assert "sqlserver_ag_cluster" in content
    assert "AG群集" in content


def test_email_alert_settings_frontend_exposes_cluster_status_rule() -> None:
    template_content = _read_text("app/templates/admin/system-settings/_email-alert-settings-section.html")
    view_content = _read_text("app/static/js/modules/views/admin/alerts/email-settings.js")

    assert 'data-rule-card="clusterStatus"' in template_content
    assert 'id="clusterStatusEnabled"' in template_content
    assert "群集状态" in template_content
    assert "clusterStatusEnabled" in view_content
    assert "cluster_status_enabled" in view_content
    assert "群集检测失败或同步状态异常将进入汇总" in view_content
